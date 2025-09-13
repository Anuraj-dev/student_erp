from flask import Blueprint, request, jsonify, current_app, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, extract, func
from io import BytesIO
import uuid
import qrcode
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import os
import csv

from app import db
from app.models.fee import Fee, FeeStatus, PaymentMethod, FeeType
from app.models.student import Student
from app.models.course import Course
from app.models.staff import Staff
from app.utils.decorators import admin_required, staff_required
from app.utils.email_utils import send_notification_email
from app.utils.validators import validate_fee_payment

# Import dashboard broadcasting functions
try:
    from app.routes.dashboard import broadcast_fee_payment_update
except ImportError:
    def broadcast_fee_payment_update(*args, **kwargs):
        pass  # Fallback if dashboard module is not available

# Fee management routes blueprint
fee_bp = Blueprint('fee', __name__)

@fee_bp.route('/generate-demand', methods=['POST'])
@jwt_required()
@admin_required
def generate_fee_demand():
    """Generate fee demand for semester (Admin only)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['semester', 'academic_year', 'course_ids']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'error': True,
                    'message': f'Missing required field: {field}',
                    'code': 'MISSING_FIELD'
                }), 400
        
        semester = data['semester']
        academic_year = data['academic_year']
        course_ids = data['course_ids']  # List of course IDs
        fee_types = data.get('fee_types', ['tuition'])  # Default to tuition
        due_days = data.get('due_days', 30)  # Default 30 days from now
        
        # Validate semester and academic year
        if not (1 <= semester <= 8):
            return jsonify({
                'error': True,
                'message': 'Semester must be between 1 and 8',
                'code': 'INVALID_SEMESTER'
            }), 400
        
        # Get active students from specified courses
        students = Student.query.filter(
            and_(
                Student.course_id.in_(course_ids),
                Student.is_active == True,
                Student.current_semester == semester
            )
        ).all()
        
        if not students:
            return jsonify({
                'error': True,
                'message': 'No active students found for the specified courses and semester',
                'code': 'NO_STUDENTS_FOUND'
            }), 404
        
        # Calculate due date
        due_date = datetime.utcnow() + timedelta(days=due_days)
        
        created_fees = []
        failed_students = []
        
        for student in students:
            try:
                # Check if fees already exist for this semester
                existing_fees = Fee.query.filter(
                    and_(
                        Fee.student_id == student.roll_no,
                        Fee.semester == semester,
                        Fee.academic_year == academic_year
                    )
                ).first()
                
                if existing_fees:
                    failed_students.append({
                        'student_id': student.roll_no,
                        'reason': 'Fees already generated'
                    })
                    continue
                
                # Create fee records for each fee type
                for fee_type in fee_types:
                    # Calculate fee amount based on course and type
                    amount = calculate_fee_amount(student, fee_type)
                    
                    fee = Fee(
                        student_id=student.roll_no,
                        fee_type=FeeType(fee_type),
                        amount=amount,
                        semester=semester,
                        academic_year=academic_year,
                        due_date=due_date,
                        description=f'{fee_type.title()} fee for {academic_year} - Semester {semester}'
                    )
                    
                    db.session.add(fee)
                    created_fees.append({
                        'student_id': student.roll_no,
                                                'student_name': student.name,  # Student model uses 'name' not 'full_name'  # Use student.name instead of full_name
                        'fee_type': fee_type,
                        'amount': amount
                    })
                
                # Send fee notification email
                try:
                    total_amount = sum(calculate_fee_amount(student, ft) for ft in fee_types)
                    send_fee_notification_email(student, semester, academic_year, total_amount, due_date)
                except Exception as e:
                    current_app.logger.warning(f"Failed to send fee notification to {student.email}: {e}")
                    
            except Exception as e:
                current_app.logger.error(f"Error generating fees for student {student.roll_no}: {e}")
                failed_students.append({
                    'student_id': student.roll_no,
                    'reason': str(e)
                })
        
        db.session.commit()
        
        current_app.logger.info(f"Fee demand generated for {len(created_fees)} fee records")
        
        return jsonify({
            'error': False,
            'message': 'Fee demand generated successfully',
            'data': {
                'semester': semester,
                'academic_year': academic_year,
                'total_students': len(students),
                'fees_created': len(created_fees),
                'failed_students': len(failed_students),
                'due_date': due_date.isoformat(),
                'created_fees': created_fees[:10],  # Show first 10 for preview
                'failed_students': failed_students
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error generating fee demand: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@fee_bp.route('/pay', methods=['POST'])
@jwt_required()
def pay_fee():
    """Process fee payment for a student"""
    try:
        data = request.get_json()
        
        # Validate payment data
        validation_result = validate_fee_payment(data)
        if not validation_result['valid']:
            return jsonify({
                'error': True,
                'message': validation_result['message'],
                'code': 'VALIDATION_ERROR'
            }), 400
        
        student_id = data['student_id']
        amount = float(data['amount'])
        payment_method = data['payment_method']
        transaction_id = data.get('transaction_id')
        reference_number = data.get('reference_number')
        remarks = data.get('remarks', '')
        
        # Get current user (staff who is processing payment)
        current_user_id = get_jwt_identity()
        staff_member = Staff.query.get(current_user_id)
        
        # Verify student exists
        student = Student.query.filter_by(roll_no=student_id).first()
        if not student:
            return jsonify({
                'error': True,
                'message': 'Student not found',
                'code': 'STUDENT_NOT_FOUND'
            }), 404
        
        # Get pending fees for the student
        pending_fees = Fee.query.filter(
            and_(
                Fee.student_id == student_id,
                Fee.status.in_([FeeStatus.PENDING, FeeStatus.OVERDUE])
            )
        ).order_by(Fee.due_date.asc()).all()
        
        if not pending_fees:
            return jsonify({
                'error': True,
                'message': 'No pending fees found for this student',
                'code': 'NO_PENDING_FEES'
            }), 404
        
        # Calculate total pending amount
        total_pending = sum(fee.total_amount for fee in pending_fees)
        
        if amount > total_pending:
            return jsonify({
                'error': True,
                'message': f'Payment amount (₹{amount}) exceeds total pending amount (₹{total_pending})',
                'code': 'AMOUNT_EXCEEDS_PENDING'
            }), 400
        
        # Process payment - allocate amount to fees
        paid_fees = []
        remaining_amount = amount
        
        for fee in pending_fees:
            if remaining_amount <= 0:
                break
                
            fee_amount = fee.total_amount
            
            if remaining_amount >= fee_amount:
                # Pay this fee completely
                fee.status = FeeStatus.PAID
                fee.payment_date = datetime.utcnow()
                fee.payment_method = PaymentMethod(payment_method)
                fee.transaction_id = transaction_id or f"TXN{uuid.uuid4().hex[:8].upper()}"
                fee.reference_number = reference_number
                fee.processed_by = current_user_id
                fee.remarks = remarks
                fee.receipt_number = generate_receipt_number(fee)
                
                paid_fees.append({
                    'fee_id': fee.id,
                    'fee_type': fee.fee_type.value,
                    'amount_paid': fee_amount,
                    'receipt_number': fee.receipt_number
                })
                
                remaining_amount -= fee_amount
            else:
                # Partial payment - create a new fee record for remaining amount
                fee.amount = int(remaining_amount)
                fee.late_fee = 0  # Reset late fee for paid portion
                fee.status = FeeStatus.PAID
                fee.payment_date = datetime.utcnow()
                fee.payment_method = PaymentMethod(payment_method)
                fee.transaction_id = transaction_id or f"TXN{uuid.uuid4().hex[:8].upper()}"
                fee.reference_number = reference_number
                fee.processed_by = current_user_id
                fee.remarks = remarks
                fee.receipt_number = generate_receipt_number(fee)
                
                # Create new fee record for remaining amount
                remaining_fee = Fee(
                    student_id=fee.student_id,
                    fee_type=fee.fee_type,
                    amount=fee_amount - int(remaining_amount),
                    late_fee=fee.late_fee,
                    discount=0,
                    semester=fee.semester,
                    academic_year=fee.academic_year,
                    due_date=fee.due_date,
                    description=fee.description + " (Partial payment remaining)",
                    status=FeeStatus.PENDING if not fee.is_overdue else FeeStatus.OVERDUE
                )
                db.session.add(remaining_fee)
                
                paid_fees.append({
                    'fee_id': fee.id,
                    'fee_type': fee.fee_type.value,
                    'amount_paid': remaining_amount,
                    'receipt_number': fee.receipt_number
                })
                
                remaining_amount = 0
        
        db.session.commit()
        
        # Broadcast real-time payment update to dashboard
        try:
            broadcast_fee_payment_update(
                student_id=student_id,
                amount=amount,
                payment_method=payment_method
            )
        except Exception as e:
            current_app.logger.warning(f"Failed to broadcast fee payment update: {e}")
        
        # Generate consolidated receipt
        receipt_data = {
            'student': student,
            'paid_fees': paid_fees,
            'total_amount': amount,
            'payment_method': payment_method,
            'payment_date': datetime.utcnow(),
            'transaction_id': transaction_id,
            'processed_by': staff_member.full_name if staff_member else 'System'
        }
        
        # Generate PDF receipt
        receipt_pdf_path = generate_pdf_receipt(receipt_data)
        
        current_app.logger.info(f"Fee payment processed: ₹{amount} for student {student_id}")
        
        return jsonify({
            'error': False,
            'message': 'Payment processed successfully',
            'data': {
                'student_id': student_id,
                'student_name': student.name,  # Student model uses 'name' not 'full_name'
                'amount_paid': amount,
                'payment_method': payment_method,
                'payment_date': datetime.utcnow().isoformat(),
                'transaction_id': transaction_id,
                'paid_fees': paid_fees,
                'receipt_download_url': f'/api/fee/receipt-download/{paid_fees[0]["receipt_number"]}',
                'remaining_balance': total_pending - amount
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error processing fee payment: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@fee_bp.route('/pending/<student_id>', methods=['GET'])
@jwt_required()
def get_pending_fees(student_id):
    """Get all pending fees for a student"""
    try:
        # Verify student exists
        student = Student.query.filter_by(roll_no=student_id).first()
        if not student:
            return jsonify({
                'error': True,
                'message': 'Student not found',
                'code': 'STUDENT_NOT_FOUND'
            }), 404
        
        # Get pending fees
        pending_fees = Fee.query.filter(
            and_(
                Fee.student_id == student_id,
                Fee.status.in_([FeeStatus.PENDING, FeeStatus.OVERDUE])
            )
        ).order_by(Fee.due_date.asc()).all()
        
        # Calculate late fees for overdue payments
        for fee in pending_fees:
            if fee.is_overdue:
                fee.calculate_late_fee()
                fee.status = FeeStatus.OVERDUE
        
        db.session.commit()
        
        # Format response
        fees_data = []
        total_amount = 0
        total_late_fee = 0
        
        for fee in pending_fees:
            fee_data = {
                'id': fee.id,
                'fee_type': fee.fee_type.value,
                'semester': fee.semester,
                'academic_year': fee.academic_year,
                'amount': fee.amount,
                'late_fee': fee.late_fee,
                'discount': fee.discount,
                'total_amount': fee.total_amount,
                'due_date': fee.due_date.isoformat(),
                'days_overdue': fee.days_overdue,
                'status': fee.status.value,
                'description': fee.description
            }
            fees_data.append(fee_data)
            total_amount += fee.amount
            total_late_fee += fee.late_fee
        
        return jsonify({
            'error': False,
            'data': {
                'student_id': student_id,
                'student_name': student.name,  # Student model uses 'name' not 'full_name'
                'course': student.course.course_name if student.course else 'N/A',  # Use course_name
                'pending_fees': fees_data,
                'summary': {
                    'total_fees_amount': total_amount,
                    'total_late_fee': total_late_fee,
                    'total_amount_due': total_amount + total_late_fee,
                    'total_count': len(pending_fees),
                    'overdue_count': len([f for f in pending_fees if f.is_overdue])
                }
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting pending fees: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@fee_bp.route('/receipt/<transaction_id>', methods=['GET'])
@jwt_required()
def get_receipt(transaction_id):
    """Generate and return PDF receipt"""
    try:
        # Find fees by transaction ID
        fees = Fee.query.filter_by(transaction_id=transaction_id).all()
        
        if not fees:
            return jsonify({
                'error': True,
                'message': 'Receipt not found',
                'code': 'RECEIPT_NOT_FOUND'
            }), 404
        
        # Get student info
        student = fees[0].student
        
        # Prepare receipt data
        receipt_data = {
            'student': student,
            'paid_fees': [{'fee_id': f.id, 'fee_type': f.fee_type.value, 'amount_paid': f.total_amount, 'receipt_number': f.receipt_number} for f in fees],
            'total_amount': sum(f.total_amount for f in fees),
            'payment_method': fees[0].payment_method.value if fees[0].payment_method else 'N/A',
            'payment_date': fees[0].payment_date,
            'transaction_id': transaction_id,
            'processed_by': fees[0].processed_by_staff.full_name if fees[0].processed_by_staff else 'System'
        }
        
        # Generate PDF receipt
        pdf_buffer = generate_pdf_receipt_buffer(receipt_data)
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'fee_receipt_{transaction_id}.pdf'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error generating receipt: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@fee_bp.route('/receipt-download/<receipt_number>', methods=['GET'])
def download_receipt(receipt_number):
    """Download receipt by receipt number (public endpoint)"""
    try:
        # Find fee by receipt number
        fee = Fee.query.filter_by(receipt_number=receipt_number).first()
        
        if not fee or fee.status != FeeStatus.PAID:
            return jsonify({
                'error': True,
                'message': 'Receipt not found',
                'code': 'RECEIPT_NOT_FOUND'
            }), 404
        
        # Prepare receipt data
        receipt_data = {
            'student': fee.student,
            'paid_fees': [{'fee_id': fee.id, 'fee_type': fee.fee_type.value, 'amount_paid': fee.total_amount, 'receipt_number': fee.receipt_number}],
            'total_amount': fee.total_amount,
            'payment_method': fee.payment_method.value if fee.payment_method else 'N/A',
            'payment_date': fee.payment_date,
            'transaction_id': fee.transaction_id,
            'processed_by': fee.processed_by_staff.full_name if fee.processed_by_staff else 'System'
        }
        
        # Generate PDF receipt
        pdf_buffer = generate_pdf_receipt_buffer(receipt_data)
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'fee_receipt_{receipt_number}.pdf'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error downloading receipt: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@fee_bp.route('/report', methods=['GET'])
@jwt_required()
@admin_required
def get_fee_report():
    """Get fee collection report (Admin only)"""
    try:
        # Get query parameters
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        course_id = request.args.get('course_id', type=int)
        payment_status = request.args.get('status')
        export_format = request.args.get('format', 'json')  # json, csv, excel
        
        # Build query
        query = Fee.query
        
        # Apply filters
        if date_from:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Fee.created_on >= date_from_obj)
        
        if date_to:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            query = query.filter(Fee.created_on <= date_to_obj)
        
        if course_id:
            query = query.join(Student).filter(Student.course_id == course_id)
        
        if payment_status:
            query = query.filter(Fee.status == FeeStatus(payment_status))
        
        fees = query.all()
        
        # Prepare report data
        report_data = []
        total_amount = 0
        total_paid = 0
        total_pending = 0
        
        for fee in fees:
            fee_info = {
                'fee_id': fee.id,
                'student_id': fee.student_id,
                'student_name': fee.student.name,  # Student model uses 'name' not 'full_name'
                'course': fee.student.course.course_name if fee.student.course else 'N/A',  # Use course_name
                'fee_type': fee.fee_type.value,
                'semester': fee.semester,
                'academic_year': fee.academic_year,
                'amount': fee.amount,
                'late_fee': fee.late_fee,
                'discount': fee.discount,
                'total_amount': fee.total_amount,
                'status': fee.status.value,
                'payment_date': fee.payment_date.isoformat() if fee.payment_date else None,
                'payment_method': fee.payment_method.value if fee.payment_method else None,
                'transaction_id': fee.transaction_id,
                'due_date': fee.due_date.isoformat(),
                'days_overdue': fee.days_overdue
            }
            report_data.append(fee_info)
            
            total_amount += fee.total_amount
            if fee.status == FeeStatus.PAID:
                total_paid += fee.total_amount
            else:
                total_pending += fee.total_amount
        
        # Summary statistics
        summary = {
            'total_fees': len(fees),
            'total_amount': total_amount,
            'total_paid': total_paid,
            'total_pending': total_pending,
            'collection_rate': (total_paid / total_amount * 100) if total_amount > 0 else 0,
            'filters': {
                'date_from': date_from,
                'date_to': date_to,
                'course_id': course_id,
                'status': payment_status
            }
        }
        
        if export_format == 'csv':
            return export_report_csv(report_data, summary)
        elif export_format == 'excel':
            return export_report_excel(report_data, summary)
        else:
            return jsonify({
                'error': False,
                'data': {
                    'fees': report_data[:100],  # Limit to first 100 for JSON response
                    'summary': summary,
                    'pagination': {
                        'total_count': len(report_data),
                        'showing': min(100, len(report_data))
                    }
                }
            }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error generating fee report: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@fee_bp.route('/statistics', methods=['GET'])
@jwt_required()
@admin_required
def get_fee_statistics():
    """Get fee collection statistics (Admin only)"""
    try:
        # Get comprehensive statistics
        stats = Fee.get_fee_statistics()
        
        # Additional analytics
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        # Monthly collection trend (last 6 months)
        monthly_collections = []
        for i in range(6):
            month_date = datetime.now() - timedelta(days=30 * i)
            month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_month = month_start + timedelta(days=32)
            next_month_start = next_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            month_fees = Fee.query.filter(
                and_(
                    Fee.status == FeeStatus.PAID,
                    Fee.payment_date >= month_start,
                    Fee.payment_date < next_month_start
                )
            ).all()
            
            monthly_collections.append({
                'month': month_start.strftime('%Y-%m'),
                'month_name': month_start.strftime('%B %Y'),
                'total_amount': sum(fee.total_amount for fee in month_fees),
                'total_count': len(month_fees)
            })
        
        # Fee type breakdown
        fee_type_stats = {}
        for fee_type in FeeType:
            type_fees = Fee.query.filter_by(fee_type=fee_type).all()
            paid_fees = [f for f in type_fees if f.status == FeeStatus.PAID]
            
            fee_type_stats[fee_type.value] = {
                'total_count': len(type_fees),
                'paid_count': len(paid_fees),
                'total_amount': sum(f.total_amount for f in type_fees),
                'paid_amount': sum(f.total_amount for f in paid_fees)
            }
        
        # Course-wise collection
        course_stats = {}
        courses = Course.query.all()
        for course in courses:
            course_students = Student.query.filter_by(course_id=course.id).all()
            course_fees = Fee.query.filter(
                Fee.student_id.in_([s.roll_no for s in course_students])
            ).all()
            
            paid_fees = [f for f in course_fees if f.status == FeeStatus.PAID]
            
            course_stats[course.course_name] = {  # Use course_name instead of name
                'total_students': len(course_students),
                'total_fees': len(course_fees),
                'paid_fees': len(paid_fees),
                'total_amount': sum(f.total_amount for f in course_fees),
                'collected_amount': sum(f.total_amount for f in paid_fees),
                'collection_rate': (len(paid_fees) / len(course_fees) * 100) if course_fees else 0
            }
        
        return jsonify({
            'error': False,
            'data': {
                'overview': stats,
                'monthly_trend': monthly_collections,
                'by_fee_type': fee_type_stats,
                'by_course': course_stats,
                'generated_at': datetime.utcnow().isoformat()
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting fee statistics: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

# Helper functions

def calculate_fee_amount(student, fee_type):
    """Calculate fee amount based on student course and fee type"""
    base_amounts = {
        'tuition': student.course.fees_per_semester if student.course else 50000,
        'hostel': 25000 if student.hostel_id else 0,
        'library': 2000,
        'laboratory': 5000,
        'exam': 3000,
        'miscellaneous': 1000
    }
    return base_amounts.get(fee_type, 1000)

def generate_receipt_number(fee):
    """Generate unique receipt number"""
    year = datetime.now().year
    month = datetime.now().month
    count = Fee.query.filter(
        and_(
            Fee.receipt_number.isnot(None),
            extract('year', Fee.payment_date) == year,
            extract('month', Fee.payment_date) == month
        )
    ).count()
    
    return f"RCP{year}{month:02d}{count+1:05d}"

def generate_pdf_receipt_buffer(receipt_data):
    """Generate PDF receipt and return as buffer"""
    buffer = BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Header
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=1,  # Center alignment
        textColor=colors.darkblue
    )
    
    story.append(Paragraph("Government Engineering College", header_style))
    story.append(Paragraph("State of Rajasthan", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Receipt title
    title_style = ParagraphStyle(
        'ReceiptTitle',
        parent=styles['Heading2'],
        fontSize=16,
        alignment=1,
        textColor=colors.red
    )
    story.append(Paragraph("FEE PAYMENT RECEIPT", title_style))
    story.append(Spacer(1, 20))
    
    # Student details
    student_data = [
        ['Student ID:', receipt_data['student'].roll_no],
        ['Student Name:', receipt_data['student'].name],  # Use name instead of full_name
        ['Course:', receipt_data['student'].course.course_name if receipt_data['student'].course else 'N/A'],  # Use course_name
        ['Payment Date:', receipt_data['payment_date'].strftime('%d/%m/%Y %H:%M:%S')],
        ['Transaction ID:', receipt_data['transaction_id']],
        ['Payment Method:', receipt_data['payment_method']],
        ['Processed By:', receipt_data['processed_by']]
    ]
    
    student_table = Table(student_data, colWidths=[2*inch, 4*inch])
    student_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey)
    ]))
    
    story.append(student_table)
    story.append(Spacer(1, 20))
    
    # Fee details
    fee_headers = ['Fee Type', 'Amount (₹)', 'Receipt No.']
    fee_data = [fee_headers]
    
    for paid_fee in receipt_data['paid_fees']:
        fee_data.append([
            paid_fee['fee_type'].title(),
            f"₹{paid_fee['amount_paid']:,.2f}",
            paid_fee['receipt_number']
        ])
    
    # Add total row
    fee_data.append(['TOTAL AMOUNT', f"₹{receipt_data['total_amount']:,.2f}", ''])
    
    fee_table = Table(fee_data, colWidths=[2*inch, 1.5*inch, 2*inch])
    fee_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')
    ]))
    
    story.append(fee_table)
    story.append(Spacer(1, 30))
    
    # QR Code for verification
    qr_data = f"Receipt:{receipt_data['paid_fees'][0]['receipt_number']};Amount:{receipt_data['total_amount']};Date:{receipt_data['payment_date'].strftime('%Y-%m-%d')}"
    qr = qrcode.QRCode(version=1, box_size=3, border=5)
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    
    qr_image = Image(qr_buffer, width=1*inch, height=1*inch)
    story.append(qr_image)
    
    # Footer
    story.append(Spacer(1, 20))
    footer_text = "This is a computer-generated receipt. No signature required."
    story.append(Paragraph(footer_text, styles['Normal']))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    
    return buffer

def generate_pdf_receipt(receipt_data):
    """Generate PDF receipt and save to file"""
    receipt_dir = os.path.join(current_app.root_path, 'static', 'receipts')
    os.makedirs(receipt_dir, exist_ok=True)
    
    filename = f"receipt_{receipt_data['paid_fees'][0]['receipt_number']}.pdf"
    filepath = os.path.join(receipt_dir, filename)
    
    buffer = generate_pdf_receipt_buffer(receipt_data)
    
    with open(filepath, 'wb') as f:
        f.write(buffer.read())
    
    return filepath

def send_fee_notification_email(student, semester, academic_year, total_amount, due_date):
    """Send fee notification email to student"""
    context = {
        'full_name': student.name,  # Student model uses 'name' not 'full_name'
        'semester': semester,
        'academic_year': academic_year,
        'amount': total_amount,
        'due_date': due_date.strftime('%d/%m/%Y')
    }
    
    return send_notification_email(
        'student',
        student.email,
        'fee_reminder',
        context
    )

def export_report_csv(report_data, summary):
    """Export fee report as CSV"""
    from io import StringIO
    
    output = StringIO()
    
    if not report_data:
        output.write("No data available\n")
    else:
        writer = csv.DictWriter(output, fieldnames=report_data[0].keys(), extrasaction='ignore')
        writer.writeheader()
        writer.writerows(report_data)
    
    output.seek(0)
    
    # Convert to bytes for send_file
    csv_data = output.getvalue()
    output_bytes = BytesIO()
    output_bytes.write(csv_data.encode('utf-8-sig'))  # UTF-8 with BOM
    output_bytes.seek(0)
    
    return send_file(
        output_bytes,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'fee_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

def export_report_excel(report_data, summary):
    """Export fee report as Excel (placeholder - would need openpyxl)"""
    # For now, return CSV format
    return export_report_csv(report_data, summary)
