from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from sqlalchemy import and_, or_
from app import db
from app.models.admission import AdmissionApplication
from app.models.student import Student
from app.models.course import Course
from app.models.staff import Staff
from app.utils.decorators import staff_required, admin_required
from app.utils.email_utils import send_email
from app.utils.validators import validate_admission_data
import uuid

# Import dashboard broadcasting functions
try:
    from app.routes.dashboard import broadcast_admission_update
except ImportError:
    def broadcast_admission_update(*args, **kwargs):
        pass  # Fallback if dashboard module is not available

# Admission routes blueprint
admission_bp = Blueprint('admission', __name__)

@admission_bp.route('/apply', methods=['POST'])
def apply_admission():
    """Submit a new admission application"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = [
            'full_name', 'email', 'phone', 'address', 
            'date_of_birth', 'course_id', 'previous_education',
            'documents'
        ]
        
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'error': True,
                    'message': f'Missing required field: {field}',
                    'code': 'MISSING_FIELD'
                }), 400
        
        # Validate admission data
        validation_result = validate_admission_data(data)
        if not validation_result['valid']:
            return jsonify({
                'error': True,
                'message': validation_result['message'],
                'code': 'VALIDATION_ERROR'
            }), 400
        
        # Check if course exists and is accepting applications
        course = Course.query.get(data['course_id'])
        if not course:
            return jsonify({
                'error': True,
                'message': 'Course not found',
                'code': 'COURSE_NOT_FOUND'
            }), 404
        
        if not course.is_accepting_applications():
            return jsonify({
                'error': True,
                'message': 'Course is not accepting applications currently',
                'code': 'APPLICATIONS_CLOSED'
            }), 400
        
        # Check for duplicate applications
        existing_application = AdmissionApplication.query.filter(
            and_(
                AdmissionApplication.email == data['email'],
                AdmissionApplication.course_id == data['course_id'],
                AdmissionApplication.status.in_(['submitted', 'under_review', 'approved'])
            )
        ).first()
        
        if existing_application:
            return jsonify({
                'error': True,
                'message': 'Application already exists for this course',
                'code': 'DUPLICATE_APPLICATION',
                'application_id': existing_application.application_id
            }), 409
        
        # Generate unique application ID
        application_id = f"APP{datetime.now().year}{str(uuid.uuid4())[:8].upper()}"
        
        # Create new admission application
        application = AdmissionApplication(
            application_id=application_id,
            full_name=data['full_name'],
            email=data['email'],
            phone=data['phone'],
            address=data['address'],
            date_of_birth=datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date(),
            course_id=data['course_id'],
            previous_education=data['previous_education'],
            documents=data['documents'],
            guardian_name=data.get('guardian_name'),
            guardian_phone=data.get('guardian_phone'),
            emergency_contact=data.get('emergency_contact'),
            medical_conditions=data.get('medical_conditions'),
            status='submitted'
        )
        
        db.session.add(application)
        db.session.commit()
        
        # Send confirmation email
        try:
            send_confirmation_email(application)
        except Exception as e:
            current_app.logger.warning(f"Failed to send confirmation email: {e}")
        
        current_app.logger.info(f"New admission application submitted: {application_id}")
        
        return jsonify({
            'error': False,
            'message': 'Application submitted successfully',
            'data': {
                'application_id': application_id,
                'status': 'submitted',
                'next_steps': [
                    'You will receive a confirmation email shortly',
                    'Applications will be processed within 7-10 working days',
                    'You can check your application status using the application ID',
                    'Ensure all documents are clearly readable'
                ]
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in admission application: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@admission_bp.route('/applications', methods=['GET'])
@jwt_required()
@staff_required
def get_applications():
    """Get all admission applications with filters (Staff only)"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)  # Max 100 per page
        
        status_filter = request.args.get('status')
        course_filter = request.args.get('course_id', type=int)
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        sort_by = request.args.get('sort_by', 'application_date')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Build query
        query = AdmissionApplication.query
        
        # Apply filters
        if status_filter:
            query = query.filter(AdmissionApplication.status == status_filter)
        
        if course_filter:
            query = query.filter(AdmissionApplication.course_id == course_filter)
        
        if date_from:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(AdmissionApplication.application_date >= date_from_obj)
        
        if date_to:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            query = query.filter(AdmissionApplication.application_date <= date_to_obj)
        
        # Apply sorting
        if sort_by == 'name':
            sort_column = AdmissionApplication.full_name
        elif sort_by == 'status':
            sort_column = AdmissionApplication.status
        else:
            sort_column = AdmissionApplication.application_date
        
        if sort_order.lower() == 'desc':
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Execute paginated query
        applications = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        # Format response
        return jsonify({
            'error': False,
            'data': {
                'applications': [app.to_dict() for app in applications.items],
                'pagination': {
                    'page': page,
                    'pages': applications.pages,
                    'per_page': per_page,
                    'total': applications.total,
                    'has_next': applications.has_next,
                    'has_prev': applications.has_prev
                }
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching applications: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@admission_bp.route('/process/<application_id>', methods=['PUT'])
@jwt_required()
@staff_required
def process_application(application_id):
    """Process admission application - update status (Staff only)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('status') or not data.get('remarks'):
            return jsonify({
                'error': True,
                'message': 'Status and remarks are required',
                'code': 'MISSING_FIELDS'
            }), 400
        
        # Validate status
        valid_statuses = ['under_review', 'approved', 'declined', 'waitlisted']
        if data['status'] not in valid_statuses:
            return jsonify({
                'error': True,
                'message': f'Invalid status. Must be one of: {", ".join(valid_statuses)}',
                'code': 'INVALID_STATUS'
            }), 400
        
        # Get application
        application = AdmissionApplication.query.filter_by(application_id=application_id).first()
        if not application:
            return jsonify({
                'error': True,
                'message': 'Application not found',
                'code': 'APPLICATION_NOT_FOUND'
            }), 404
        
        # Get staff member
        current_user_id = get_jwt_identity()
        staff_member = Staff.query.get(current_user_id)
        if not staff_member:
            return jsonify({
                'error': True,
                'message': 'Staff member not found',
                'code': 'STAFF_NOT_FOUND'
            }), 404
        
        # Store previous status for logging
        previous_status = application.status
        
        # Update application
        application.update_status(
            new_status=data['status'],
            remarks=data['remarks'],
            processed_by=staff_member.id
        )
        
        # If approved, create student record
        if data['status'] == 'approved':
            try:
                # Generate roll number
                roll_number = Student.generate_roll_number(application.course_id)
                
                # Create student record
                student = Student(
                    roll_number=roll_number,
                    full_name=application.full_name,
                    email=application.email,
                    phone=application.phone,
                    address=application.address,
                    date_of_birth=application.date_of_birth,
                    course_id=application.course_id,
                    admission_date=datetime.now().date(),
                    guardian_name=application.guardian_name,
                    guardian_phone=application.guardian_phone,
                    emergency_contact=application.emergency_contact,
                    medical_conditions=application.medical_conditions,
                    password='temporary123'  # Temporary password
                )
                
                db.session.add(student)
                application.student_id = student.id
                
                # Send approval email with roll number
                try:
                    send_approval_email(application, student)
                except Exception as e:
                    current_app.logger.warning(f"Failed to send approval email: {e}")
                
            except Exception as e:
                current_app.logger.error(f"Error creating student record: {str(e)}")
                return jsonify({
                    'error': True,
                    'message': 'Failed to create student record',
                    'code': 'STUDENT_CREATION_ERROR'
                }), 500
        
        # If declined, send rejection email
        elif data['status'] == 'declined':
            try:
                send_rejection_email(application, data['remarks'])
            except Exception as e:
                current_app.logger.warning(f"Failed to send rejection email: {e}")
        
        db.session.commit()
        
        # Broadcast real-time update to dashboard
        try:
            broadcast_admission_update(
                application_id=application_id,
                status=data['status'],
                user_type='admin'
            )
        except Exception as e:
            current_app.logger.warning(f"Failed to broadcast admission update: {e}")
        
        current_app.logger.info(
            f"Application {application_id} status changed from {previous_status} to {data['status']} by staff {staff_member.full_name}"
        )
        
        return jsonify({
            'error': False,
            'message': 'Application processed successfully',
            'data': {
                'application_id': application_id,
                'previous_status': previous_status,
                'current_status': data['status'],
                'processed_by': staff_member.full_name,
                'processed_at': datetime.now().isoformat(),
                'remarks': data['remarks']
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error processing application: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@admission_bp.route('/status/<application_id>', methods=['GET'])
def get_application_status(application_id):
    """Get application status (Public endpoint)"""
    try:
        application = AdmissionApplication.query.filter_by(application_id=application_id).first()
        if not application:
            return jsonify({
                'error': True,
                'message': 'Application not found',
                'code': 'APPLICATION_NOT_FOUND'
            }), 404
        
        return jsonify({
            'error': False,
            'data': {
                'application_id': application_id,
                'applicant_name': application.full_name,
                'course': application.course.name if application.course else 'N/A',
                'status': application.status,
                'application_date': application.application_date.strftime('%Y-%m-%d'),
                'last_updated': application.last_updated.strftime('%Y-%m-%d %H:%M:%S'),
                'remarks': application.remarks if application.status in ['declined', 'waitlisted'] else None,
                'roll_number': application.student.roll_number if application.student else None
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting application status: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@admission_bp.route('/statistics', methods=['GET'])
@jwt_required()
@admin_required
def get_admission_statistics():
    """Get admission statistics and analytics (Admin only)"""
    try:
        # Get date range
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        query = AdmissionApplication.query
        
        if date_from:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(AdmissionApplication.application_date >= date_from_obj)
        
        if date_to:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            query = query.filter(AdmissionApplication.application_date <= date_to_obj)
        
        applications = query.all()
        
        # Calculate statistics
        total_applications = len(applications)
        
        status_stats = {}
        course_stats = {}
        monthly_stats = {}
        
        for app in applications:
            # Status statistics
            status = app.status
            status_stats[status] = status_stats.get(status, 0) + 1
            
            # Course statistics
            course_name = app.course.name if app.course else 'Unknown'
            course_stats[course_name] = course_stats.get(course_name, 0) + 1
            
            # Monthly statistics
            month_key = app.application_date.strftime('%Y-%m')
            monthly_stats[month_key] = monthly_stats.get(month_key, 0) + 1
        
        # Calculate conversion rates
        approved_count = status_stats.get('approved', 0)
        conversion_rate = (approved_count / total_applications * 100) if total_applications > 0 else 0
        
        # Calculate average processing time
        processed_apps = [app for app in applications if app.status in ['approved', 'declined']]
        avg_processing_time = 0
        if processed_apps:
            total_days = sum([(app.last_updated.date() - app.application_date.date()).days for app in processed_apps])
            avg_processing_time = total_days / len(processed_apps)
        
        return jsonify({
            'error': False,
            'data': {
                'summary': {
                    'total_applications': total_applications,
                    'approved': status_stats.get('approved', 0),
                    'declined': status_stats.get('declined', 0),
                    'pending': status_stats.get('submitted', 0) + status_stats.get('under_review', 0),
                    'conversion_rate': round(conversion_rate, 2),
                    'average_processing_time_days': round(avg_processing_time, 1)
                },
                'by_status': status_stats,
                'by_course': course_stats,
                'by_month': monthly_stats,
                'date_range': {
                    'from': date_from,
                    'to': date_to
                }
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting admission statistics: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

# Helper functions
def send_confirmation_email(application):
    """Send confirmation email to applicant"""
    subject = f"Application Received - {application.application_id}"
    
    body = f"""
    Dear {application.full_name},
    
    Thank you for applying to our institution. Your application has been received successfully.
    
    Application Details:
    - Application ID: {application.application_id}
    - Course: {application.course.name if application.course else 'N/A'}
    - Submitted on: {application.application_date.strftime('%Y-%m-%d %H:%M:%S')}
    
    Next Steps:
    1. Your application will be reviewed within 7-10 working days
    2. You will receive updates via email
    3. You can check your application status anytime using your Application ID
    
    Please keep your Application ID safe for future reference.
    
    Best regards,
    Admissions Office
    """
    
    send_email(application.email, subject, body)

def send_approval_email(application, student):
    """Send approval email with roll number"""
    subject = f"Application Approved - Welcome to {application.course.name if application.course else 'Our Institution'}"
    
    body = f"""
    Dear {application.full_name},
    
    Congratulations! Your application has been approved.
    
    Your Details:
    - Application ID: {application.application_id}
    - Roll Number: {student.roll_number}
    - Course: {application.course.name if application.course else 'N/A'}
    - Admission Date: {student.admission_date.strftime('%Y-%m-%d')}
    
    Next Steps:
    1. Complete the enrollment process within 7 days
    2. Pay the required fees
    3. Submit original documents for verification
    4. Attend the orientation session
    
    Welcome to our institution!
    
    Best regards,
    Admissions Office
    """
    
    send_email(application.email, subject, body)

def send_rejection_email(application, reason):
    """Send rejection email with reason"""
    subject = f"Application Update - {application.application_id}"
    
    body = f"""
    Dear {application.full_name},
    
    Thank you for your interest in our institution. After careful review, we regret to inform you that your application could not be approved at this time.
    
    Reason: {reason}
    
    We encourage you to apply again in the future. Please feel free to contact our admissions office if you have any questions.
    
    Best regards,
    Admissions Office
    """
    
    send_email(application.email, subject, body)
