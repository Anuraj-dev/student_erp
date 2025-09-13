"""
Hostel Management Routes
Handles hostel allocation, vacation, and occupancy reporting
"""

from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError
from app.models.hostel import Hostel
from app.models.student import Student
from app.models.staff import Staff
from app.utils.decorators import admin_required, staff_required
from app import db
import logging

# Create hostel blueprint
hostel_bp = Blueprint('hostel', __name__, url_prefix='/api/hostel')

# Set up logging
logger = logging.getLogger(__name__)


@hostel_bp.route('/available', methods=['GET'])
@jwt_required()
def get_available_hostels():
    """
    GET /api/hostel/available
    Get list of hostels with available beds
    Include capacity, occupied, and available counts
    """
    try:
        # Get optional gender filter
        gender = request.args.get('gender', None)
        
        # Get available hostels
        available_hostels = Hostel.get_available_hostels(gender=gender)
        
        # Convert to dict format
        hostels_data = []
        for hostel in available_hostels:
            hostel_dict = hostel.to_dict()
            hostels_data.append(hostel_dict)
        
        return jsonify({
            'success': True,
            'message': f'Found {len(hostels_data)} available hostels',
            'data': {
                'hostels': hostels_data,
                'total_available': len(hostels_data)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving available hostels: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve available hostels',
            'error': str(e)
        }), 500


@hostel_bp.route('/allocate', methods=['POST'])
@jwt_required()
@staff_required
def allocate_hostel():
    """
    POST /api/hostel/allocate
    Allocate hostel to student
    Check availability before allocation
    Update available beds count
    Prevent duplicate allocation
    Send allocation confirmation
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'student_id' not in data or 'hostel_id' not in data:
            return jsonify({
                'success': False,
                'message': 'student_id and hostel_id are required'
            }), 400
        
        student_id = data.get('student_id')
        hostel_id = data.get('hostel_id')
        room_number = data.get('room_number', None)
        
        # Check if student exists
        student = Student.query.filter_by(roll_no=student_id).first()
        if not student:
            return jsonify({
                'success': False,
                'message': 'Student not found'
            }), 404
        
        # Check if student already has hostel allocation
        if student.hostel_id:
            return jsonify({
                'success': False,
                'message': 'Student is already allocated to a hostel'
            }), 400
        
        # Check if hostel exists
        hostel = Hostel.query.get(hostel_id)
        if not hostel:
            return jsonify({
                'success': False,
                'message': 'Hostel not found'
            }), 404
        
        # Check if hostel is active
        if not hostel.is_active:
            return jsonify({
                'success': False,
                'message': 'Hostel is not active'
            }), 400
        
        # Check hostel availability
        if not hostel.has_available_beds():
            return jsonify({
                'success': False,
                'message': 'No available beds in this hostel'
            }), 400
        
        # Check gender compatibility
        student_gender = student.gender.value if hasattr(student.gender, 'value') else student.gender
        if hostel.hostel_type == 'Boys' and student_gender.lower() != 'male':
            return jsonify({
                'success': False,
                'message': 'This hostel is for male students only'
            }), 400
        elif hostel.hostel_type == 'Girls' and student_gender.lower() != 'female':
            return jsonify({
                'success': False,
                'message': 'This hostel is for female students only'
            }), 400
        
        # Allocate hostel to student
        success, message = student.allocate_hostel(hostel_id, room_number)
        
        if success:
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Hostel allocated successfully',
                'data': {
                    'student_id': student.roll_no,
                    'student_name': student.name,
                    'hostel_id': hostel.id,
                    'hostel_name': hostel.name,
                    'room_number': room_number,
                    'allocation_date': student.updated_on.isoformat(),
                    'monthly_rent': hostel.monthly_rent,
                    'security_deposit': hostel.security_deposit
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error during hostel allocation: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Database error during allocation',
            'error': str(e)
        }), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error allocating hostel: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to allocate hostel',
            'error': str(e)
        }), 500


@hostel_bp.route('/vacate/<string:student_id>', methods=['PUT'])
@jwt_required()
@staff_required
def vacate_hostel(student_id):
    """
    PUT /api/hostel/vacate/{student_id}
    Remove student from hostel
    Increment available beds
    Log vacation reason and date
    """
    try:
        data = request.get_json() or {}
        vacation_reason = data.get('reason', 'Not specified')
        
        # Find student
        student = Student.query.filter_by(roll_no=student_id).first()
        if not student:
            return jsonify({
                'success': False,
                'message': 'Student not found'
            }), 404
        
        # Check if student has hostel allocation
        if not student.hostel_id:
            return jsonify({
                'success': False,
                'message': 'Student is not allocated to any hostel'
            }), 400
        
        # Get hostel details before vacating
        hostel = Hostel.query.get(student.hostel_id)
        if not hostel:
            return jsonify({
                'success': False,
                'message': 'Associated hostel not found'
            }), 404
        
        # Store allocation details for response
        allocation_details = {
            'student_id': student.roll_no,
            'student_name': student.name,
            'hostel_id': hostel.id,
            'hostel_name': hostel.name,
            'vacation_reason': vacation_reason,
            'vacation_date': None
        }
        
        # Vacate hostel
        success, message = student.vacate_hostel(vacation_reason)
        
        if success:
            # Update hostel available beds count
            hostel.vacate_bed()
            
            # Update vacation date
            allocation_details['vacation_date'] = student.updated_on.isoformat()
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Hostel vacated successfully',
                'data': allocation_details
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error during hostel vacation: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Database error during vacation',
            'error': str(e)
        }), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error vacating hostel: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to vacate hostel',
            'error': str(e)
        }), 500


@hostel_bp.route('/occupancy-report', methods=['GET'])
@jwt_required()
@admin_required
def get_occupancy_report():
    """
    GET /api/hostel/occupancy-report
    Admin only: Get occupancy statistics
    Return data for dashboard visualization
    """
    try:
        # Get overall statistics
        overall_stats = Hostel.get_occupancy_stats()
        
        # Get individual hostel details
        hostels = Hostel.query.filter_by(is_active=True).all()
        hostel_details = []
        
        for hostel in hostels:
            hostel_data = {
                'id': hostel.id,
                'name': hostel.name,
                'hostel_type': hostel.hostel_type,
                'total_beds': hostel.total_beds,
                'occupied_beds': hostel.occupied_beds,
                'available_beds': hostel.available_beds,
                'occupancy_percentage': hostel.get_occupancy_percentage(),
                'warden_name': hostel.warden_name,
                'warden_phone': hostel.warden_phone,
                'monthly_rent': hostel.monthly_rent,
                'facilities': hostel.facilities,
                'mess_facility': hostel.mess_facility,
                'wifi_available': hostel.wifi_available
            }
            hostel_details.append(hostel_data)
        
        # Get students by hostel
        students_by_hostel = {}
        for hostel in hostels:
            students = Student.query.filter_by(hostel_id=hostel.id).all()
            students_by_hostel[hostel.id] = [
                {
                    'roll_no': s.roll_no,
                    'name': s.name,
                    'gender': s.gender.value if hasattr(s.gender, 'value') else s.gender,
                    'course_name': s.course.course_name if s.course else 'Unknown',
                    'allocation_date': s.updated_on.isoformat() if s.updated_on else None
                }
                for s in students
            ]
        
        # Calculate gender-wise occupancy
        gender_stats = {
            'male_students': 0,
            'female_students': 0,
            'boys_hostels': 0,
            'girls_hostels': 0,
            'mixed_hostels': 0
        }
        
        for hostel in hostels:
            if hostel.hostel_type == 'Boys':
                gender_stats['boys_hostels'] += 1
            elif hostel.hostel_type == 'Girls':
                gender_stats['girls_hostels'] += 1
            else:
                gender_stats['mixed_hostels'] += 1
        
        # Count students by gender
        all_hostel_students = Student.query.filter(Student.hostel_id.isnot(None)).all()
        for student in all_hostel_students:
            student_gender = student.gender.value if hasattr(student.gender, 'value') else student.gender
            if student_gender.lower() == 'male':
                gender_stats['male_students'] += 1
            else:
                gender_stats['female_students'] += 1
        
        return jsonify({
            'success': True,
            'message': 'Occupancy report generated successfully',
            'data': {
                'overall_statistics': overall_stats,
                'hostel_details': hostel_details,
                'students_by_hostel': students_by_hostel,
                'gender_statistics': gender_stats,
                'report_generated_at': datetime.utcnow().isoformat()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating occupancy report: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to generate occupancy report',
            'error': str(e)
        }), 500


# Additional utility endpoints

@hostel_bp.route('/student/<string:student_id>', methods=['GET'])
@jwt_required()
def get_student_hostel_details(student_id):
    """
    GET /api/hostel/student/{student_id}
    Get hostel details for a specific student
    """
    try:
        # Find student
        student = Student.query.filter_by(roll_no=student_id).first()
        if not student:
            return jsonify({
                'success': False,
                'message': 'Student not found'
            }), 404
        
        # Check JWT identity matches student (for student users) or is staff/admin
        current_user = get_jwt_identity()
        if current_user != student_id:
            # Check if current user is staff/admin
            staff = Staff.query.filter_by(employee_id=current_user).first()
            if not staff:
                return jsonify({
                    'success': False,
                    'message': 'Access denied'
                }), 403
        
        if not student.hostel_id:
            return jsonify({
                'success': True,
                'message': 'Student is not allocated to any hostel',
                'data': {
                    'student_id': student.roll_no,
                    'student_name': student.name,
                    'hostel_allocated': False,
                    'hostel_details': None
                }
            }), 200
        
        hostel = Hostel.query.get(student.hostel_id)
        if not hostel:
            return jsonify({
                'success': False,
                'message': 'Hostel data not found'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Student hostel details retrieved successfully',
            'data': {
                'student_id': student.roll_no,
                'student_name': student.name,
                'hostel_allocated': True,
                'hostel_details': {
                    'id': hostel.id,
                    'name': hostel.name,
                    'hostel_type': hostel.hostel_type,
                    'warden_name': hostel.warden_name,
                    'warden_phone': hostel.warden_phone,
                    'address': hostel.address,
                    'facilities': hostel.facilities,
                    'mess_facility': hostel.mess_facility,
                    'wifi_available': hostel.wifi_available,
                    'monthly_rent': hostel.monthly_rent,
                    'security_deposit': hostel.security_deposit,
                    'allocation_date': student.updated_on.isoformat() if student.updated_on else None
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving student hostel details: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve student hostel details',
            'error': str(e)
        }), 500


@hostel_bp.route('/statistics', methods=['GET'])
@jwt_required()
@staff_required
def get_hostel_statistics():
    """
    GET /api/hostel/statistics
    Get basic hostel statistics for staff dashboard
    """
    try:
        # Get overall statistics
        stats = Hostel.get_occupancy_stats()
        
        # Get additional statistics
        total_students_with_hostel = Student.query.filter(Student.hostel_id.isnot(None)).count()
        total_students_without_hostel = Student.query.filter(Student.hostel_id.is_(None)).count()
        
        # Get hostel type breakdown
        boys_hostels = Hostel.query.filter_by(hostel_type='Boys', is_active=True).count()
        girls_hostels = Hostel.query.filter_by(hostel_type='Girls', is_active=True).count()
        mixed_hostels = Hostel.query.filter_by(hostel_type='Mixed', is_active=True).count()
        
        enhanced_stats = {
            **stats,
            'students_with_hostel': total_students_with_hostel,
            'students_without_hostel': total_students_without_hostel,
            'hostel_types': {
                'boys_hostels': boys_hostels,
                'girls_hostels': girls_hostels,
                'mixed_hostels': mixed_hostels
            }
        }
        
        return jsonify({
            'success': True,
            'message': 'Hostel statistics retrieved successfully',
            'data': enhanced_stats
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving hostel statistics: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve hostel statistics',
            'error': str(e)
        }), 500
