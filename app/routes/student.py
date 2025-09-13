"""
Student Management Routes
Complete implementation matching API documentation
"""

from flask import Blueprint, request, jsonify, current_app, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
import csv
import io
import os
from app import db
from app.models.student import Student
from app.models.course import Course
from app.models.hostel import Hostel
from app.models.fee import Fee
# from app.models.library import BookIssue  # Not implemented yet
from app.models.examination import Examination
from app.models.staff import Staff
from app.utils.decorators import admin_required, staff_required, role_required
from app.utils.validators import validate_email, validate_phone, validate_roll_no
from app.utils.email_service import send_email
from app.utils.logging_config import log_admin_action
from app.models.library import BookIssue

# Create Blueprint
student_bp = Blueprint('student', __name__)

def get_current_user_role():
    """Get current user role from JWT token"""
    try:
        claims = get_jwt()
        return claims.get('role', 'student')
    except:
        return 'student'

def get_current_user_info():
    """Get current user information from JWT token"""
    try:
        user_id = get_jwt_identity()
        claims = get_jwt()
        role = claims.get('role', 'student')
        
        if role == 'student':
            user = Student.query.filter_by(roll_no=user_id).first()
        else:
            # For staff, the user_id is employee_id (string)
            user = Staff.query.filter_by(employee_id=user_id).first()
            
        return user, role
    except:
        return None, None

@student_bp.route('', methods=['GET'])
@jwt_required()
def get_students():
    """
    Get Students List
    GET /api/student
    
    Query Parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 50, max: 100)
    - search: Search by name, roll_no, or email
    - course_id: Filter by course
    - hostel_id: Filter by hostel
    - is_active: Filter by status (true/false)
    - admission_year: Filter by admission year
    - sort_by: Sort field (name, roll_no, created_on)
    - sort_order: Sort direction (asc, desc)
    """
    try:
        current_user, role = get_current_user_info()
        
        # Access control
        if role == 'student':
            # Students can only view their own profile
            student = current_user
            if not student:
                return jsonify({
                    'error': True,
                    'message': 'Student not found',
                    'code': 'STUDENT_NOT_FOUND'
                }), 404
                
            return jsonify({
                'error': False,
                'data': [student.to_dict()],
                'pagination': {
                    'page': 1,
                    'per_page': 1,
                    'total': 1,
                    'pages': 1
                }
            }), 200
        
        # Admin/Staff can view all students
        if role not in ['admin', 'staff']:
            return jsonify({
                'error': True,
                'message': 'Insufficient permissions',
                'code': 'ACCESS_DENIED'
            }), 403
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        search = request.args.get('search', '').strip()
        course_id = request.args.get('course_id', type=int)
        hostel_id = request.args.get('hostel_id', type=int)
        is_active = request.args.get('is_active')
        admission_year = request.args.get('admission_year')
        sort_by = request.args.get('sort_by', 'name')
        sort_order = request.args.get('sort_order', 'asc')
        
        # Build query
        query = Student.query.options(
            joinedload(Student.course),
            joinedload(Student.hostel)
        )
        
        # Apply filters
        if search:
            search_filter = or_(
                Student.name.ilike(f'%{search}%'),
                Student.email.ilike(f'%{search}%'),
                Student.roll_no.ilike(f'%{search}%')
            )
            query = query.filter(search_filter)
        
        if course_id:
            query = query.filter(Student.course_id == course_id)
            
        if hostel_id:
            query = query.filter(Student.hostel_id == hostel_id)
            
        if is_active is not None:
            active = is_active.lower() == 'true'
            query = query.filter(Student.is_active == active)
            
        if admission_year:
            start_date = datetime.strptime(f"{admission_year}-01-01", "%Y-%m-%d")
            end_date = datetime.strptime(f"{admission_year}-12-31", "%Y-%m-%d")
            query = query.filter(and_(
                Student.registered_on >= start_date,
                Student.registered_on <= end_date
            ))
        
        # Apply sorting
        if sort_by == 'name':
            order_field = Student.name
        elif sort_by == 'roll_no':
            order_field = Student.roll_no
        elif sort_by == 'created_on':
            order_field = Student.registered_on
        else:
            order_field = Student.name
            
        if sort_order.lower() == 'desc':
            query = query.order_by(desc(order_field))
        else:
            query = query.order_by(asc(order_field))
        
        # Execute paginated query
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        students = []
        for student in pagination.items:
            student_data = student.to_dict()
            # Add additional info for admin/staff
            if role in ['admin', 'staff']:
                student_data['course_name'] = student.course.course_name if student.course else None
                student_data['hostel_name'] = student.hostel.name if student.hostel else None
            students.append(student_data)
        
        return jsonify({
            'error': False,
            'data': students,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting students: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@student_bp.route('', methods=['POST'])
@jwt_required()
@admin_required
def create_student():
    """
    Create New Student (Admin Only)
    POST /api/student
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': True,
                'message': 'Invalid request format',
                'code': 'INVALID_REQUEST'
            }), 400
        
        # Validate required fields
        required_fields = ['name', 'email', 'phone', 'course_id', 'date_of_birth', 'gender']
        missing_fields = []
        
        for field in required_fields:
            if not data.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            return jsonify({
                'error': True,
                'message': f'Missing required fields: {", ".join(missing_fields)}',
                'code': 'MISSING_FIELDS'
            }), 400
        
        # Validate email format
        email_valid, email_message = validate_email(data['email'])
        if not email_valid:
            return jsonify({
                'error': True,
                'message': f'Invalid email: {email_message}',
                'code': 'INVALID_EMAIL'
            }), 400
        
        # Validate phone format
        phone_valid, phone_message, formatted_phone = validate_phone(data['phone'])
        if not phone_valid:
            return jsonify({
                'error': True,
                'message': f'Invalid phone: {phone_message}',
                'code': 'INVALID_PHONE'
            }), 400
        
        # Check for duplicate email
        existing_student = Student.query.filter_by(email=data['email']).first()
        if existing_student:
            return jsonify({
                'error': True,
                'message': 'Email already exists',
                'code': 'DUPLICATE_EMAIL'
            }), 409
        
        # Check for duplicate phone
        existing_phone = Student.query.filter_by(phone=data['phone']).first()
        if existing_phone:
            return jsonify({
                'error': True,
                'message': 'Phone number already exists',
                'code': 'DUPLICATE_PHONE'
            }), 409
        
        # Validate course exists
        course = Course.query.get(data['course_id'])
        if not course:
            return jsonify({
                'error': True,
                'message': 'Course not found',
                'code': 'COURSE_NOT_FOUND'
            }), 404
        
        # Generate unique roll number
        current_year = datetime.now().year
        course_code = course.course_code if hasattr(course, 'course_code') else 'GEN'
        
        # Get next sequence number for the course and year
        last_student = Student.query.filter(
            Student.roll_no.like(f'{current_year}{course_code}%')
        ).order_by(desc(Student.roll_no)).first()
        
        if last_student:
            last_seq = int(last_student.roll_no[-3:])
            next_seq = last_seq + 1
        else:
            next_seq = 1
        
        roll_no = f'{current_year}{course_code}{next_seq:03d}'
        
        # Ensure roll number is unique
        while Student.query.filter_by(roll_no=roll_no).first():
            next_seq += 1
            roll_no = f'{current_year}{course_code}{next_seq:03d}'
        
        # Parse date of birth
        try:
            dob = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'error': True,
                'message': 'Invalid date format. Use YYYY-MM-DD',
                'code': 'INVALID_DATE'
            }), 400
        
        # Parse gender enum
        try:
            from app.models.student import Gender
            if isinstance(data['gender'], str):
                gender_value = Gender[data['gender'].upper()]
            else:
                gender_value = data['gender']
        except (KeyError, ValueError):
            return jsonify({
                'error': True,
                'message': 'Invalid gender. Must be Male, Female, or Other',
                'code': 'INVALID_GENDER'
            }), 400
        
        # Create student
        student = Student(
            roll_no=roll_no,
            name=data['name'].strip(),
            email=data['email'].lower().strip(),
            phone=data['phone'].strip(),
            course_id=data['course_id'],
            date_of_birth=dob,
            gender=gender_value,
            address=data.get('address', '').strip(),
            city=data.get('city', '').strip(),
            state=data.get('state', '').strip(),
            pincode=data.get('pincode', '').strip(),
            father_name=data.get('father_name', '').strip(),
            mother_name=data.get('mother_name', '').strip(),
            guardian_phone=data.get('guardian_phone', '').strip(),
            guardian_email=data.get('guardian_email', '').strip(),
            admission_year=data.get('admission_year', datetime.now().year),
            current_semester=data.get('current_semester', 1),
            is_active=True
        )
        
        # Set password from data or default to roll number
        password = data.get('password', roll_no)
        student.set_password(password)
        
        db.session.add(student)
        db.session.commit()
        
        # Log admin action
        current_user, _ = get_current_user_info()
        if current_user:
            admin_id = current_user.roll_no if hasattr(current_user, 'roll_no') else current_user.employee_id
            log_admin_action(
                admin_id=admin_id,
                action='CREATE_STUDENT',
                details=f'Created student {student.roll_no} - {student.name}'
            )
        
        # Send welcome email (async)
        try:
            send_email(
                to_email=student.email,
                subject='Welcome to ERP System',
                template='welcome_student',
                context={
                    'name': student.name,
                    'roll_no': student.roll_no,
                    'password': roll_no,
                    'course': course.course_name
                }
            )
        except Exception as e:
            current_app.logger.warning(f"Failed to send welcome email: {e}")
        
        return jsonify({
            'error': False,
            'message': 'Student created successfully',
            'roll_no': student.roll_no,
            'data': student.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating student: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@student_bp.route('/<string:roll_no>', methods=['GET'])
@jwt_required()
def get_student_details(roll_no):
    """
    Get Student Details
    GET /api/student/<roll_no>
    """
    try:
        current_user, role = get_current_user_info()
        
        # Find student
        student = Student.query.filter_by(roll_no=roll_no).options(
            joinedload(Student.course),
            joinedload(Student.hostel)
        ).first()
        
        if not student:
            return jsonify({
                'error': True,
                'message': 'Student not found',
                'code': 'STUDENT_NOT_FOUND'
            }), 404
        
        # Access control
        if role == 'student':
            # Students can only view their own profile
            if current_user.roll_no != roll_no:
                return jsonify({
                    'error': True,
                    'message': 'Access denied',
                    'code': 'ACCESS_DENIED'
                }), 403
        elif role not in ['admin', 'staff']:
            return jsonify({
                'error': True,
                'message': 'Insufficient permissions',
                'code': 'ACCESS_DENIED'
            }), 403
        
        # Get student data
        student_data = student.to_dict()
        
        # Add detailed information for admin/staff
        if role in ['admin', 'staff']:
            # Course details
            if student.course:
                student_data['course_details'] = {
                    'id': student.course.id,
                    'course_name': student.course.course_name,
                    'program_level': getattr(student.course, 'program_level', None),
                    'degree_name': getattr(student.course, 'degree_name', None)
                }
            
            # Hostel details
            if student.hostel:
                student_data['hostel_details'] = {
                    'hostel_name': student.hostel.name,
                    'room_no': student.room_number,
                    'allocated_on': None  # We don't have allocation date in this model
                }
            
            # Fee payment summary
            total_paid = db.session.query(func.sum(Fee.amount)).filter_by(
                student_id=student.roll_no, status='paid'
            ).scalar() or 0
            
            pending_fees = db.session.query(func.sum(Fee.amount)).filter_by(
                student_id=student.roll_no, status='pending'
            ).scalar() or 0
            
            student_data['fee_summary'] = {
                'total_paid': float(total_paid),
                'pending_amount': float(pending_fees),
                'last_payment': None
            }
            
            # Get last payment
            last_payment = Fee.query.filter_by(
                student_id=student.roll_no, status='paid'
            ).order_by(desc(Fee.payment_date)).first()
            
            if last_payment:
                student_data['fee_summary']['last_payment'] = {
                    'amount': float(last_payment.amount),
                    'date': last_payment.payment_date.isoformat(),
                    'method': last_payment.payment_method
                }
            
            # Library statistics (BookIssue model not implemented yet)
            student_data['library_stats'] = {
                'currently_issued': 0,
                'total_books_taken': 0,
                'note': 'Library system not yet implemented'
            }
        
        return jsonify({
            'error': False,
            'data': student_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting student details: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@student_bp.route('/<string:roll_no>', methods=['PUT'])
@jwt_required()
def update_student(roll_no):
    """
    Update Student Information
    PUT /api/student/<roll_no>
    """
    try:
        current_user, role = get_current_user_info()
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': True,
                'message': 'Invalid request format',
                'code': 'INVALID_REQUEST'
            }), 400
        
        # Find student
        student = Student.query.filter_by(roll_no=roll_no).first()
        if not student:
            return jsonify({
                'error': True,
                'message': 'Student not found',
                'code': 'STUDENT_NOT_FOUND'
            }), 404
        
        # Access control and determine allowed fields
        allowed_fields = []
        
        if role == 'admin':
            # Admin can update all fields
            allowed_fields = [
                'name', 'email', 'phone', 'course_id', 'address', 
                'guardian_name', 'guardian_phone', 'is_active', 'gender'
            ]
        elif role == 'staff':
            # Staff can update basic info only
            allowed_fields = ['phone', 'address', 'guardian_name', 'guardian_phone']
        elif role == 'student' and current_user.roll_no == roll_no:
            # Students can update their own contact info only
            allowed_fields = ['phone', 'address', 'guardian_phone']
        else:
            return jsonify({
                'error': True,
                'message': 'Insufficient permissions',
                'code': 'ACCESS_DENIED'
            }), 403
        
        # Track changes for logging
        changes = {}
        
        # Update allowed fields
        for field in allowed_fields:
            if field in data and data[field] is not None:
                old_value = getattr(student, field)
                new_value = data[field]
                
                # Validate specific fields
                if field == 'email':
                    email_valid, email_message = validate_email(new_value)
                    if not email_valid:
                        return jsonify({
                            'error': True,
                            'message': f'Invalid email: {email_message}',
                            'code': 'INVALID_EMAIL'
                        }), 400
                    
                    # Check for duplicate email
                    existing = Student.query.filter(
                        Student.email == new_value,
                        Student.roll_no != student.roll_no
                    ).first()
                    if existing:
                        return jsonify({
                            'error': True,
                            'message': 'Email already exists',
                            'code': 'DUPLICATE_EMAIL'
                        }), 409
                
                if field == 'phone':
                    phone_valid, phone_message, formatted_phone = validate_phone(new_value)
                    if not phone_valid:
                        return jsonify({
                            'error': True,
                            'message': f'Invalid phone: {phone_message}',
                            'code': 'INVALID_PHONE'
                        }), 400
                    
                    # Use formatted phone if available
                    if formatted_phone:
                        new_value = formatted_phone
                    
                    # Check for duplicate phone
                    existing = Student.query.filter(
                        Student.phone == new_value,
                        Student.roll_no != student.roll_no
                    ).first()
                    if existing:
                        return jsonify({
                            'error': True,
                            'message': 'Phone number already exists',
                            'code': 'DUPLICATE_PHONE'
                        }), 409
                
                if field == 'course_id':
                    course = Course.query.get(new_value)
                    if not course:
                        return jsonify({
                            'error': True,
                            'message': 'Course not found',
                            'code': 'COURSE_NOT_FOUND'
                        }), 404
                
                # Update field if changed
                if old_value != new_value:
                    setattr(student, field, new_value)
                    changes[field] = {'old': old_value, 'new': new_value}
        
        if not changes:
            return jsonify({
                'error': False,
                'message': 'No changes made',
                'data': student.to_dict()
            }), 200
        
        # Save changes
        student.updated_on = datetime.now()
        db.session.commit()
        
        # Log changes
        if role in ['admin', 'staff']:
            log_admin_action(
                admin_id=current_user.roll_no if hasattr(current_user, 'roll_no') else current_user.id,
                action='UPDATE_STUDENT',
                details=f'Updated student {student.roll_no}: {changes}'
            )
        
        return jsonify({
            'error': False,
            'message': 'Student updated successfully',
            'data': student.to_dict(),
            'changes': changes
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating student: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@student_bp.route('/<string:roll_no>', methods=['DELETE'])
@jwt_required()
@admin_required
def deactivate_student(roll_no):
    """
    Deactivate Student (Admin Only)
    DELETE /api/student/<roll_no>
    """
    try:
        student = Student.query.filter_by(roll_no=roll_no).first()
        if not student:
            return jsonify({
                'error': True,
                'message': 'Student not found',
                'code': 'STUDENT_NOT_FOUND'
            }), 404
        
        # Check for pending obligations
        pending_fees = Fee.query.filter_by(
            student_id=student.roll_no, status='pending'
        ).count()
        
        issued_books = BookIssue.query.filter_by(
            student_id=student.roll_no, status='issued'
        ).count()
        
        if pending_fees > 0:
            return jsonify({
                'error': True,
                'message': f'Student has {pending_fees} pending fee payments',
                'code': 'PENDING_FEES'
            }), 409
        
        if issued_books > 0:
            return jsonify({
                'error': True,
                'message': f'Student has {issued_books} books not returned',
                'code': 'PENDING_BOOKS'
            }), 409
        
        # Soft delete - mark as inactive
        student.is_active = False
        student.deactivated_on = datetime.now()
        
        # Release hostel allocation if any
        if student.hostel:
            student.hostel_id = None
            student.room_number = None
        
        db.session.commit()
        
        # Log admin action
        current_user, _ = get_current_user_info()
        log_admin_action(
            admin_id=current_user.roll_no if hasattr(current_user, 'roll_no') else current_user.id,
            action='DEACTIVATE_STUDENT',
            details=f'Deactivated student {student.roll_no} - {student.name}'
        )
        
        return jsonify({
            'error': False,
            'message': 'Student deactivated successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deactivating student: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@student_bp.route('/<string:roll_no>/academic-record', methods=['GET'])
@jwt_required()
def get_academic_record(roll_no):
    """
    Get Student Academic Record
    GET /api/student/<roll_no>/academic-record
    """
    try:
        current_user, role = get_current_user_info()
        
        # Find student
        student = Student.query.filter_by(roll_no=roll_no).first()
        if not student:
            return jsonify({
                'error': True,
                'message': 'Student not found',
                'code': 'STUDENT_NOT_FOUND'
            }), 404
        
        # Access control
        if role == 'student' and current_user.roll_no != roll_no:
            return jsonify({
                'error': True,
                'message': 'Access denied',
                'code': 'ACCESS_DENIED'
            }), 403
        elif role not in ['admin', 'staff', 'student']:
            return jsonify({
                'error': True,
                'message': 'Access denied',
                'code': 'ACCESS_DENIED'
            }), 403
        
        # Get academic records
        examinations = Examination.query.filter_by(
            student_id=student.roll_no
        ).order_by(Examination.semester, Examination.exam_date).all()
        
        # Organize by semester
        semester_records = {}
        total_credits = 0
        total_grade_points = 0
        
        for exam in examinations:
            sem = exam.semester
            if sem not in semester_records:
                semester_records[sem] = {
                    'semester': sem,
                    'subjects': [],
                    'semester_gpa': 0,
                    'total_credits': 0
                }
            
            subject_record = {
                'subject_code': getattr(exam, 'subject_code', 'N/A'),
                'subject_name': getattr(exam, 'subject_name', 'N/A'),
                'marks': exam.marks,
                'grade': exam.grade,
                'credits': getattr(exam, 'credits', 3),  # Default 3 credits
                'exam_date': exam.exam_date.isoformat() if exam.exam_date else None
            }
            
            semester_records[sem]['subjects'].append(subject_record)
            
            # Calculate GPA (assuming grade points: A=10, B=8, C=6, D=4, F=0)
            grade_points = {
                'A+': 10, 'A': 9, 'B+': 8, 'B': 7, 'C+': 6, 
                'C': 5, 'D': 4, 'F': 0
            }.get(exam.grade, 0)
            
            credits = subject_record['credits']
            semester_records[sem]['total_credits'] += credits
            total_credits += credits
            total_grade_points += grade_points * credits
        
        # Calculate semester GPAs
        for sem_data in semester_records.values():
            if sem_data['total_credits'] > 0:
                sem_grade_points = sum(
                    {
                        'A+': 10, 'A': 9, 'B+': 8, 'B': 7, 'C+': 6, 
                        'C': 5, 'D': 4, 'F': 0
                    }.get(subject['grade'], 0) * subject['credits']
                    for subject in sem_data['subjects']
                )
                sem_data['semester_gpa'] = round(sem_grade_points / sem_data['total_credits'], 2)
        
        # Calculate overall CGPA
        cgpa = round(total_grade_points / total_credits, 2) if total_credits > 0 else 0
        
        academic_record = {
            'student_info': {
                'roll_no': student.roll_no,
                'name': student.name,
                'course': student.course.course_name if student.course else None
            },
            'academic_summary': {
                'total_semesters': len(semester_records),
                'total_credits': total_credits,
                'cgpa': cgpa
            },
            'semester_records': list(semester_records.values()),
            'generated_on': datetime.now().isoformat()
        }
        
        # Check for PDF format request
        format_type = request.args.get('format', 'json')
        if format_type.lower() == 'pdf':
            # TODO: Generate PDF transcript
            return jsonify({
                'error': True,
                'message': 'PDF generation not implemented yet',
                'code': 'FEATURE_NOT_IMPLEMENTED'
            }), 501
        
        return jsonify({
            'error': False,
            'data': academic_record
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting academic record: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@student_bp.route('/<string:roll_no>/fee-history', methods=['GET'])
@jwt_required()
def get_fee_history(roll_no):
    """
    Get Student Fee History
    GET /api/student/<roll_no>/fee-history
    """
    try:
        current_user, role = get_current_user_info()
        
        # Find student
        student = Student.query.filter_by(roll_no=roll_no).first()
        if not student:
            return jsonify({
                'error': True,
                'message': 'Student not found',
                'code': 'STUDENT_NOT_FOUND'
            }), 404
        
        # Access control
        if role == 'student' and current_user.roll_no != roll_no:
            return jsonify({
                'error': True,
                'message': 'Access denied',
                'code': 'ACCESS_DENIED'
            }), 403
        elif role not in ['admin', 'staff', 'student']:
            return jsonify({
                'error': True,
                'message': 'Access denied',
                'code': 'ACCESS_DENIED'
            }), 403
        
        # Get query parameters
        year = request.args.get('year', type=int)
        semester = request.args.get('semester')
        status = request.args.get('status')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        
        # Build query
        query = Fee.query.filter_by(student_id=student.roll_no)
        
        if year:
            start_date = datetime(year, 1, 1)
            end_date = datetime(year, 12, 31)
            query = query.filter(and_(
                Fee.created_on >= start_date,
                Fee.created_on <= end_date
            ))
        
        if semester:
            query = query.filter_by(semester=semester)
        
        if status:
            query = query.filter_by(status=status)
        
        if from_date:
            try:
                from_dt = datetime.strptime(from_date, '%Y-%m-%d')
                query = query.filter(Fee.created_on >= from_dt)
            except ValueError:
                return jsonify({
                    'error': True,
                    'message': 'Invalid from_date format. Use YYYY-MM-DD',
                    'code': 'INVALID_DATE'
                }), 400
        
        if to_date:
            try:
                to_dt = datetime.strptime(to_date, '%Y-%m-%d')
                query = query.filter(Fee.created_on <= to_dt)
            except ValueError:
                return jsonify({
                    'error': True,
                    'message': 'Invalid to_date format. Use YYYY-MM-DD',
                    'code': 'INVALID_DATE'
                }), 400
        
        fees = query.order_by(desc(Fee.created_on)).all()
        
        # Calculate summary
        total_paid = sum(fee.amount for fee in fees if fee.status == 'paid')
        total_pending = sum(fee.amount for fee in fees if fee.status == 'pending')
        total_overdue = sum(fee.amount for fee in fees if fee.status == 'overdue')
        
        # Group by semester
        semester_wise = {}
        for fee in fees:
            sem = fee.semester or 'General'
            if sem not in semester_wise:
                semester_wise[sem] = {
                    'semester': sem,
                    'fees': [],
                    'total_amount': 0,
                    'paid_amount': 0,
                    'pending_amount': 0
                }
            
            fee_data = fee.to_dict()
            semester_wise[sem]['fees'].append(fee_data)
            semester_wise[sem]['total_amount'] += fee.amount
            
            if fee.status == 'paid':
                semester_wise[sem]['paid_amount'] += fee.amount
            else:
                semester_wise[sem]['pending_amount'] += fee.amount
        
        fee_history = {
            'student_info': {
                'roll_no': student.roll_no,
                'name': student.name
            },
            'summary': {
                'total_fees': len(fees),
                'total_amount': float(total_paid + total_pending + total_overdue),
                'paid_amount': float(total_paid),
                'pending_amount': float(total_pending),
                'overdue_amount': float(total_overdue)
            },
            'semester_wise': list(semester_wise.values()),
            'all_fees': [fee.to_dict() for fee in fees]
        }
        
        return jsonify({
            'error': False,
            'data': fee_history
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting fee history: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@student_bp.route('/<string:roll_no>/library-history', methods=['GET'])
@jwt_required()
def get_library_history(roll_no):
    """
    Get Student Library History
    GET /api/student/<roll_no>/library-history
    """
    try:
        current_user, role = get_current_user_info()
        
        # Find student
        student = Student.query.filter_by(roll_no=roll_no).first()
        if not student:
            return jsonify({
                'error': True,
                'message': 'Student not found',
                'code': 'STUDENT_NOT_FOUND'
            }), 404
        
        # Access control
        if role == 'student' and current_user.roll_no != roll_no:
            return jsonify({
                'error': True,
                'message': 'Access denied',
                'code': 'ACCESS_DENIED'
            }), 403
        elif role not in ['admin', 'staff', 'student', 'library']:
            return jsonify({
                'error': True,
                'message': 'Access denied',
                'code': 'ACCESS_DENIED'
            }), 403
        
        # Get query parameters
        status = request.args.get('status')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        category = request.args.get('category')
        
        # Build query
        query = BookIssue.query.filter_by(student_id=student.roll_no).options(
            joinedload(BookIssue.book)
        )
        
        if status:
            query = query.filter_by(status=status)
        
        if from_date:
            try:
                from_dt = datetime.strptime(from_date, '%Y-%m-%d')
                query = query.filter(BookIssue.issue_date >= from_dt)
            except ValueError:
                return jsonify({
                    'error': True,
                    'message': 'Invalid from_date format. Use YYYY-MM-DD',
                    'code': 'INVALID_DATE'
                }), 400
        
        if to_date:
            try:
                to_dt = datetime.strptime(to_date, '%Y-%m-%d')
                query = query.filter(BookIssue.issue_date <= to_dt)
            except ValueError:
                return jsonify({
                    'error': True,
                    'message': 'Invalid to_date format. Use YYYY-MM-DD',
                    'code': 'INVALID_DATE'
                }), 400
        
        if category:
            # Assuming books have category field
            query = query.join(BookIssue.book).filter(
                getattr(BookIssue.book, 'category', None) == category
            )
        
        book_issues = query.order_by(desc(BookIssue.issue_date)).all()
        
        # Calculate statistics
        currently_issued = [issue for issue in book_issues if issue.status == 'issued']
        returned_books = [issue for issue in book_issues if issue.status == 'returned']
        overdue_books = [issue for issue in book_issues if issue.status == 'overdue']
        
        total_fines = sum(getattr(issue, 'fine_amount', 0) for issue in book_issues)
        paid_fines = sum(
            getattr(issue, 'fine_amount', 0) for issue in book_issues 
            if getattr(issue, 'fine_paid', False)
        )
        
        library_history = {
            'student_info': {
                'roll_no': student.roll_no,
                'name': student.name
            },
            'statistics': {
                'currently_issued': len(currently_issued),
                'total_books_taken': len(book_issues),
                'books_returned': len(returned_books),
                'overdue_books': len(overdue_books),
                'total_fines': float(total_fines),
                'pending_fines': float(total_fines - paid_fines)
            },
            'currently_issued_books': [
                {
                    'issue_id': issue.id,
                    'book_title': issue.book.title if issue.book else 'Unknown',
                    'book_isbn': getattr(issue.book, 'isbn', None) if issue.book else None,
                    'issue_date': issue.issue_date.isoformat(),
                    'due_date': issue.due_date.isoformat() if issue.due_date else None,
                    'days_overdue': max(0, (datetime.now().date() - issue.due_date).days) if issue.due_date else 0
                }
                for issue in currently_issued
            ],
            'all_issues': [
                {
                    'issue_id': issue.id,
                    'book_title': issue.book.title if issue.book else 'Unknown',
                    'book_isbn': getattr(issue.book, 'isbn', None) if issue.book else None,
                    'issue_date': issue.issue_date.isoformat(),
                    'due_date': issue.due_date.isoformat() if issue.due_date else None,
                    'return_date': issue.return_date.isoformat() if issue.return_date else None,
                    'status': issue.status,
                    'fine_amount': float(getattr(issue, 'fine_amount', 0))
                }
                for issue in book_issues
            ]
        }
        
        return jsonify({
            'error': False,
            'data': library_history
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting library history: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@student_bp.route('/statistics', methods=['GET'])
@jwt_required()
@staff_required
def get_students_statistics():
    """
    Get Students Statistics (Admin/Staff Only)
    GET /api/student/statistics
    """
    try:
        # Get query parameters
        year = request.args.get('year', type=int)
        course_id = request.args.get('course_id', type=int)
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        
        # Base query
        base_query = Student.query
        
        if not include_inactive:
            base_query = base_query.filter_by(is_active=True)
        
        if year:
            start_date = datetime(year, 1, 1)
            end_date = datetime(year, 12, 31)
            base_query = base_query.filter(and_(
                Student.registered_on >= start_date,
                Student.registered_on <= end_date
            ))
        
        if course_id:
            base_query = base_query.filter_by(course_id=course_id)
        
        # Total counts
        total_students = base_query.count()
        active_students = base_query.filter_by(is_active=True).count()
        inactive_students = total_students - active_students
        
        # Gender distribution
        gender_stats = db.session.query(
            Student.gender, func.count(Student.roll_no)
        ).filter(Student.roll_no.in_(
            base_query.with_entities(Student.roll_no)
        )).group_by(Student.gender).all()
        
        gender_distribution = {gender.value if hasattr(gender, 'value') else str(gender): count for gender, count in gender_stats}
        
        # Course-wise distribution
        course_stats = db.session.query(
            Course.course_name, func.count(Student.roll_no)
        ).join(Student).filter(Student.roll_no.in_(
            base_query.with_entities(Student.roll_no)
        )).group_by(Course.id, Course.course_name).all()
        
        course_distribution = {course: count for course, count in course_stats}
        
        # Admission year statistics
        admission_stats = db.session.query(
            Student.admission_year,
            func.count(Student.roll_no)
        ).filter(Student.roll_no.in_(
            base_query.with_entities(Student.roll_no)
        )).group_by(Student.admission_year).all()
        
        admission_year_stats = {int(year): count for year, count in admission_stats}
        
        # Hostel statistics
        hostel_allocated = db.session.query(func.count(Student.roll_no)).filter(
            Student.roll_no.in_(base_query.with_entities(Student.roll_no)),
            Student.hostel_id.isnot(None)
        ).scalar() or 0
        
        # Fee payment statistics
        total_fees_generated = db.session.query(func.count(Fee.id)).join(
            Student, Fee.student_id == Student.roll_no
        ).filter(Student.roll_no.in_(base_query.with_entities(Student.roll_no))).scalar() or 0
        
        paid_fees = db.session.query(func.count(Fee.id)).join(
            Student, Fee.student_id == Student.roll_no
        ).filter(
            Student.roll_no.in_(base_query.with_entities(Student.roll_no)),
            Fee.status == 'paid'
        ).scalar() or 0
        
        pending_fees = total_fees_generated - paid_fees
        
        statistics = {
            'overview': {
                'total_students': total_students,
                'active_students': active_students,
                'inactive_students': inactive_students,
                'hostel_allocated': hostel_allocated,
                'hostel_occupancy_rate': round((hostel_allocated / total_students * 100), 2) if total_students > 0 else 0
            },
            'gender_distribution': gender_distribution,
            'course_distribution': course_distribution,
            'admission_year_distribution': admission_year_stats,
            'fee_statistics': {
                'total_fees_generated': total_fees_generated,
                'paid_fees': paid_fees,
                'pending_fees': pending_fees,
                'payment_rate': round((paid_fees / total_fees_generated * 100), 2) if total_fees_generated > 0 else 0
            },
            'generated_on': datetime.now().isoformat(),
            'filters_applied': {
                'year': year,
                'course_id': course_id,
                'include_inactive': include_inactive
            }
        }
        
        return jsonify({
            'error': False,
            'data': statistics
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting student statistics: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@student_bp.route('/bulk-operations', methods=['POST'])
@jwt_required()
@admin_required
def bulk_student_operations():
    """
    Bulk Student Operations (Admin Only)
    POST /api/student/bulk-operations
    """
    try:
        data = request.get_json()
        
        if not data or 'operation' not in data:
            return jsonify({
                'error': True,
                'message': 'Operation type required',
                'code': 'MISSING_OPERATION'
            }), 400
        
        operation = data['operation']
        
        if operation == 'export':
            # Export students to CSV
            format_type = data.get('format', 'csv')
            filters = data.get('filters', {})
            
            # Build query with filters
            query = Student.query.options(joinedload(Student.course))
            
            if filters.get('course_id'):
                query = query.filter_by(course_id=filters['course_id'])
            if filters.get('is_active') is not None:
                query = query.filter_by(is_active=filters['is_active'])
            
            students = query.all()
            
            if format_type.lower() == 'csv':
                # Generate CSV
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Write header
                writer.writerow([
                    'Roll No', 'Name', 'Email', 'Phone', 'Course', 
                    'Gender', 'Date of Birth', 'Status', 'Registered On'
                ])
                
                # Write data
                for student in students:
                    writer.writerow([
                        student.roll_no,
                        student.name,
                        student.email,
                        student.phone,
                        student.course.course_name if student.course else '',
                        student.gender,
                        student.date_of_birth.strftime('%Y-%m-%d') if student.date_of_birth else '',
                        'Active' if student.is_active else 'Inactive',
                        student.registered_on.strftime('%Y-%m-%d %H:%M:%S') if student.registered_on else ''
                    ])
                
                output.seek(0)
                
                return jsonify({
                    'error': False,
                    'message': 'Export completed successfully',
                    'data': {
                        'csv_content': output.getvalue(),
                        'total_records': len(students)
                    }
                }), 200
        
        elif operation == 'import':
            # Import students from CSV data
            csv_data = data.get('csv_data')
            if not csv_data:
                return jsonify({
                    'error': True,
                    'message': 'CSV data required for import',
                    'code': 'MISSING_CSV_DATA'
                }), 400
            
            # Parse CSV
            csv_file = io.StringIO(csv_data)
            reader = csv.DictReader(csv_file)
            
            imported_count = 0
            errors = []
            
            for row_num, row in enumerate(reader, 1):
                try:
                    # Validate required fields
                    if not all([row.get('name'), row.get('email'), row.get('course_code')]):
                        errors.append(f"Row {row_num}: Missing required fields")
                        continue
                    
                    # Find course
                    course = Course.query.filter_by(course_code=row['course_code']).first()
                    if not course:
                        errors.append(f"Row {row_num}: Course '{row['course_code']}' not found")
                        continue
                    
                    # Check for existing email
                    if Student.query.filter_by(email=row['email']).first():
                        errors.append(f"Row {row_num}: Email '{row['email']}' already exists")
                        continue
                    
                    # Generate roll number (same logic as create_student)
                    current_year = datetime.now().year
                    course_code = course.course_code
                    
                    last_student = Student.query.filter(
                        Student.roll_no.like(f'{current_year}{course_code}%')
                    ).order_by(desc(Student.roll_no)).first()
                    
                    if last_student:
                        last_seq = int(last_student.roll_no[-3:])
                        next_seq = last_seq + 1
                    else:
                        next_seq = 1
                    
                    roll_no = f'{current_year}{course_code}{next_seq:03d}'
                    
                    # Create student
                    student = Student(
                        roll_no=roll_no,
                        name=row['name'].strip(),
                        email=row['email'].lower().strip(),
                        phone=row.get('phone', '').strip(),
                        course_id=course.id,
                        gender=row.get('gender', 'other'),
                        address=row.get('address', '').strip(),
                        guardian_name=row.get('guardian_name', '').strip(),
                        guardian_phone=row.get('guardian_phone', '').strip(),
                        is_active=True,
                        registered_on=datetime.now()
                    )
                    
                    if row.get('date_of_birth'):
                        try:
                            student.date_of_birth = datetime.strptime(
                                row['date_of_birth'], '%Y-%m-%d'
                            ).date()
                        except ValueError:
                            pass
                    
                    # Set default password
                    student.set_password(roll_no)
                    
                    db.session.add(student)
                    imported_count += 1
                    
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
            
            if imported_count > 0:
                db.session.commit()
                
                # Log admin action
                current_user, _ = get_current_user_info()
                log_admin_action(
                    admin_id=current_user.roll_no if hasattr(current_user, 'roll_no') else current_user.id,
                    action='BULK_IMPORT_STUDENTS',
                    details=f'Imported {imported_count} students'
                )
            
            return jsonify({
                'error': False,
                'message': f'Bulk import completed. {imported_count} students imported.',
                'data': {
                    'imported_count': imported_count,
                    'error_count': len(errors),
                    'errors': errors[:10]  # Limit errors shown
                }
            }), 200
        
        else:
            return jsonify({
                'error': True,
                'message': f'Unsupported operation: {operation}',
                'code': 'UNSUPPORTED_OPERATION'
            }), 400
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in bulk operations: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@student_bp.route('/search', methods=['GET'])
@jwt_required()
@staff_required
def search_students():
    """
    Advanced Student Search
    GET /api/student/search
    """
    try:
        # Get query parameters
        q = request.args.get('q', '').strip()
        if not q:
            return jsonify({
                'error': True,
                'message': 'Search query required',
                'code': 'MISSING_QUERY'
            }), 400
        
        fields = request.args.get('fields', 'name,email,roll_no').split(',')
        fuzzy = request.args.get('fuzzy', 'false').lower() == 'true'
        limit = min(request.args.get('limit', 20, type=int), 100)
        
        # Build search query
        search_conditions = []
        
        if 'name' in fields:
            search_conditions.append(Student.name.ilike(f'%{q}%'))
        if 'email' in fields:
            search_conditions.append(Student.email.ilike(f'%{q}%'))
        if 'roll_no' in fields:
            search_conditions.append(Student.roll_no.ilike(f'%{q}%'))
        if 'phone' in fields:
            search_conditions.append(Student.phone.ilike(f'%{q}%'))
        
        if not search_conditions:
            return jsonify({
                'error': True,
                'message': 'No valid search fields specified',
                'code': 'INVALID_FIELDS'
            }), 400
        
        # Execute search
        students = Student.query.options(
            joinedload(Student.course)
        ).filter(
            or_(*search_conditions)
        ).limit(limit).all()
        
        # Format results with highlighting
        results = []
        for student in students:
            student_data = student.to_dict()
            student_data['course_name'] = student.course.course_name if student.course else None
            
            # Add highlighting (simple implementation)
            highlights = {}
            if q.lower() in student.name.lower():
                highlights['name'] = student.name.replace(
                    q, f'<mark>{q}</mark>'
                ) if not fuzzy else student.name
            
            if q.lower() in student.email.lower():
                highlights['email'] = student.email.replace(
                    q, f'<mark>{q}</mark>'
                ) if not fuzzy else student.email
                
            student_data['highlights'] = highlights
            results.append(student_data)
        
        # Calculate relevance scores (simple implementation)
        for result in results:
            score = 0
            if q.lower() in result['name'].lower():
                score += 3
            if q.lower() in result['roll_no'].lower():
                score += 5  # Exact roll no match is more relevant
            if q.lower() in result['email'].lower():
                score += 2
            result['relevance_score'] = score
        
        # Sort by relevance
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return jsonify({
            'error': False,
            'data': {
                'query': q,
                'total_results': len(results),
                'results': results,
                'search_suggestions': [] if results else [
                    'Check spelling',
                    'Try different keywords',
                    'Use student roll number for exact match'
                ]
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in student search: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500
