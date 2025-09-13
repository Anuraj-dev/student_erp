from flask import Blueprint, jsonify, g, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, verify_jwt_in_request
from flask_socketio import emit, join_room, leave_room, rooms
from sqlalchemy import func, extract, and_, or_
from datetime import datetime, timedelta, date
from collections import defaultdict
import calendar

from app import db, socketio
from app.models import (
    Student, StudentGender,
    Staff, StaffRole,
    AdmissionApplication, ApplicationStatus,
    Fee, FeeStatus, PaymentMethod, FeeType,
    Hostel, Course, Examination
)
from app.utils.decorators import jwt_required_custom, admin_required, staff_required, student_required

# Dashboard routes blueprint
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')

def get_dashboard_cache_key(user_id, endpoint):
    """Generate cache key for dashboard data"""
    return f"dashboard:{user_id}:{endpoint}:{datetime.now().strftime('%Y%m%d_%H%M')}"

def format_response(success=True, data=None, message=None, status_code=200):
    """Standard response format for dashboard endpoints"""
    response = {
        'success': success,
        'timestamp': datetime.utcnow().isoformat(),
        'data': data or {},
        'message': message
    }
    return jsonify(response), status_code

@dashboard_bp.route('/health')
def dashboard_health():
    """Health check endpoint"""
    return format_response(data={'status': 'dashboard routes active'})

@dashboard_bp.route('/summary')
@jwt_required_custom
def dashboard_summary():
    """
    GET /api/dashboard/summary
    Return key metrics based on user role
    """
    try:
        user = g.current_user
        user_type = g.user_type
        
        if user_type == 'staff':
            # Admin gets full system metrics, Staff gets limited metrics
            if hasattr(user, 'role') and user.role == StaffRole.ADMIN:
                data = _get_admin_summary()
            else:
                data = _get_staff_summary()
        elif user_type == 'student':
            data = _get_student_summary(user.roll_no)
        else:
            return format_response(False, message="Invalid user type", status_code=403)
        
        return format_response(data=data)
        
    except Exception as e:
        return format_response(
            False, 
            message=f"Error fetching dashboard summary: {str(e)}", 
            status_code=500
        )

def _get_admin_summary():
    """Get complete system overview for admin"""
    # Total students by status
    total_students = db.session.query(func.count(Student.roll_no)).scalar() or 0
    active_students = db.session.query(func.count(Student.roll_no)).filter_by(is_active=True).scalar() or 0
    
    # Admission statistics
    total_applications = db.session.query(func.count(AdmissionApplication.id)).scalar() or 0
    pending_applications = db.session.query(func.count(AdmissionApplication.id)).filter_by(status=ApplicationStatus.SUBMITTED).scalar() or 0
    approved_applications = db.session.query(func.count(AdmissionApplication.id)).filter_by(status=ApplicationStatus.APPROVED).scalar() or 0
    
    # Fee collection stats
    total_fee_collected = db.session.query(func.sum(Fee.amount)).filter_by(status=FeeStatus.PAID).scalar() or 0
    total_fee_pending = db.session.query(func.sum(Fee.amount)).filter_by(status=FeeStatus.PENDING).scalar() or 0
    today_collection = db.session.query(func.sum(Fee.amount)).filter(
        and_(Fee.status == FeeStatus.PAID, func.date(Fee.payment_date) == date.today())
    ).scalar() or 0
    
    # Hostel occupancy
    total_beds = db.session.query(func.sum(Hostel.total_beds)).scalar() or 0
    occupied_beds = db.session.query(func.count(Student.roll_no)).filter(Student.hostel_id.isnot(None)).scalar() or 0
    
    return {
        'students': {
            'total': total_students,
            'active': active_students,
            'inactive': total_students - active_students
        },
        'admissions': {
            'total_applications': total_applications,
            'pending': pending_applications,
            'approved': approved_applications,
            'declined': total_applications - pending_applications - approved_applications
        },
        'fees': {
            'total_collected': float(total_fee_collected) / 100 if total_fee_collected else 0,  # Convert paise to rupees
            'total_pending': float(total_fee_pending) / 100 if total_fee_pending else 0,
            'today_collection': float(today_collection) / 100 if today_collection else 0,
            'collection_rate': (total_fee_collected / (total_fee_collected + total_fee_pending)) * 100 if (total_fee_collected + total_fee_pending) > 0 else 0
        },
        'hostels': {
            'total_beds': total_beds,
            'occupied': occupied_beds,
            'available': total_beds - occupied_beds,
            'occupancy_rate': (occupied_beds / total_beds) * 100 if total_beds > 0 else 0
        }
    }

def _get_staff_summary():
    """Get limited metrics for staff"""
    # Pending applications for processing
    pending_applications = db.session.query(func.count(AdmissionApplication.id)).filter_by(status=ApplicationStatus.SUBMITTED).scalar() or 0
    
    # Today's fee collection
    today_collection = db.session.query(func.sum(Fee.amount)).filter(
        and_(Fee.status == FeeStatus.PAID, func.date(Fee.payment_date) == date.today())
    ).scalar() or 0
    
    # Recently submitted applications (last 7 days)
    week_ago = date.today() - timedelta(days=7)
    recent_applications = db.session.query(func.count(AdmissionApplication.id)).filter(
        func.date(AdmissionApplication.application_date) >= week_ago
    ).scalar() or 0
    
    return {
        'pending_applications': pending_applications,
        'today_collection': float(today_collection) / 100 if today_collection else 0,
        'recent_applications': recent_applications,
        'tasks': {
            'applications_to_review': pending_applications,
            'documents_pending': db.session.query(func.count(AdmissionApplication.id)).filter_by(status=ApplicationStatus.DOCUMENTS_PENDING).scalar() or 0
        }
    }

def _get_student_summary(roll_no):
    """Get personal academic progress and fee status for student"""
    student = Student.query.get(roll_no)
    if not student:
        return {}
    
    # Fee status
    total_fees = db.session.query(func.sum(Fee.amount)).filter_by(student_id=roll_no).scalar() or 0
    paid_fees = db.session.query(func.sum(Fee.amount)).filter(
        and_(Fee.student_id == roll_no, Fee.status == FeeStatus.PAID)
    ).scalar() or 0
    pending_fees = total_fees - paid_fees
    
    # Academic progress
    total_exams = db.session.query(func.count(Examination.id)).filter_by(student_id=roll_no).scalar() or 0
    passed_exams = db.session.query(func.count(Examination.id)).filter(
        and_(Examination.student_id == roll_no, Examination.marks_obtained >= 40)  # Assuming 40 is pass marks
    ).scalar() or 0
    
    return {
        'personal_info': {
            'name': student.name,
            'roll_no': student.roll_no,
            'course': student.course.course_name if student.course else None,
            'current_semester': student.current_semester,
            'hostel_allocated': student.hostel.name if student.hostel else None
        },
        'academic_progress': {
            'total_exams': total_exams,
            'passed_exams': passed_exams,
            'success_rate': (passed_exams / total_exams) * 100 if total_exams > 0 else 0
        },
        'fee_status': {
            'total_fees': float(total_fees) / 100 if total_fees else 0,
            'paid_fees': float(paid_fees) / 100 if paid_fees else 0,
            'pending_fees': float(pending_fees) / 100 if pending_fees else 0,
        }
    }

@dashboard_bp.route('/charts/enrollment')
@staff_required
def charts_enrollment():
    """
    GET /api/dashboard/charts/enrollment
    Return enrollment data by course and year, formatted for Chart.js visualization
    """
    try:
        # Get enrollment data grouped by course and year
        enrollment_data = db.session.query(
            Course.course_name,
            Student.admission_year,
            func.count(Student.roll_no).label('student_count')
        ).join(
            Course, Student.course_id == Course.id
        ).group_by(
            Course.course_name, Student.admission_year
        ).all()
        
        # Format data for Chart.js
        courses = {}
        years = set()
        
        for course_name, year, count in enrollment_data:
            if course_name not in courses:
                courses[course_name] = {}
            courses[course_name][year] = count
            years.add(year)
        
        years = sorted(list(years))
        
        # Create Chart.js compatible format
        datasets = []
        colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']
        
        for idx, (course_name, year_data) in enumerate(courses.items()):
            dataset = {
                'label': course_name,
                'data': [year_data.get(year, 0) for year in years],
                'backgroundColor': colors[idx % len(colors)],
                'borderColor': colors[idx % len(colors)],
                'fill': False
            }
            datasets.append(dataset)
        
        # Calculate trends (year-over-year growth)
        trends = {}
        for course_name, year_data in courses.items():
            if len(year_data) > 1:
                sorted_years = sorted(year_data.keys())
                latest_year = sorted_years[-1]
                previous_year = sorted_years[-2]
                
                current_count = year_data[latest_year]
                previous_count = year_data[previous_year]
                
                if previous_count > 0:
                    growth = ((current_count - previous_count) / previous_count) * 100
                    trends[course_name] = round(growth, 2)
        
        return format_response(data={
            'chart_type': 'line',
            'labels': [str(year) for year in years],
            'datasets': datasets,
            'options': {
                'responsive': True,
                'scales': {
                    'y': {
                        'beginAtZero': True,
                        'title': {
                            'display': True,
                            'text': 'Number of Students'
                        }
                    },
                    'x': {
                        'title': {
                            'display': True,
                            'text': 'Academic Year'
                        }
                    }
                }
            },
            'trends': trends,
            'metadata': {
                'total_courses': len(courses),
                'years_covered': len(years),
                'total_students': sum(sum(year_data.values()) for year_data in courses.values())
            }
        })
        
    except Exception as e:
        return format_response(
            False,
            message=f"Error fetching enrollment charts: {str(e)}",
            status_code=500
        )

@dashboard_bp.route('/charts/fee-collection')
@staff_required
def charts_fee_collection():
    """
    GET /api/dashboard/charts/fee-collection
    Return monthly fee collection data with breakdown by payment method
    """
    try:
        # Get current year or from query parameter
        current_year = request.args.get('year', datetime.now().year, type=int)
        
        # Monthly fee collection data
        monthly_data = db.session.query(
            extract('month', Fee.payment_date).label('month'),
            func.sum(Fee.amount).label('total_amount')
        ).filter(
            and_(
                Fee.status == FeeStatus.PAID,
                extract('year', Fee.payment_date) == current_year
            )
        ).group_by(
            extract('month', Fee.payment_date)
        ).all()
        
        # Payment method breakdown
        payment_method_data = db.session.query(
            Fee.payment_method,
            func.sum(Fee.amount).label('total_amount'),
            func.count(Fee.id).label('transaction_count')
        ).filter(
            and_(
                Fee.status == FeeStatus.PAID,
                extract('year', Fee.payment_date) == current_year
            )
        ).group_by(Fee.payment_method).all()
        
        # Pending vs Collected ratio
        total_collected = db.session.query(func.sum(Fee.amount)).filter_by(status=FeeStatus.PAID).scalar() or 0
        total_pending = db.session.query(func.sum(Fee.amount)).filter_by(status=FeeStatus.PENDING).scalar() or 0
        
        # Format monthly collection data
        months = list(range(1, 13))
        monthly_amounts = {}
        for month, amount in monthly_data:
            monthly_amounts[int(month)] = float(amount) / 100  # Convert paise to rupees
        
        monthly_chart_data = [monthly_amounts.get(month, 0) for month in months]
        month_labels = [calendar.month_abbr[month] for month in months]
        
        # Format payment method data
        payment_methods = []
        payment_amounts = []
        payment_colors = {
            PaymentMethod.CASH: '#FF6384',
            PaymentMethod.ONLINE: '#36A2EB', 
            PaymentMethod.BANK_TRANSFER: '#FFCE56',
            PaymentMethod.CHEQUE: '#4BC0C0',
            PaymentMethod.DD: '#9966FF'
        }
        
        for method, amount, count in payment_method_data:
            payment_methods.append(method.value.replace('_', ' ').title())
            payment_amounts.append(float(amount) / 100)
        
        return format_response(data={
            'monthly_collection': {
                'chart_type': 'bar',
                'labels': month_labels,
                'datasets': [{
                    'label': f'Fee Collection {current_year}',
                    'data': monthly_chart_data,
                    'backgroundColor': '#36A2EB',
                    'borderColor': '#36A2EB',
                    'borderWidth': 1
                }],
                'options': {
                    'responsive': True,
                    'scales': {
                        'y': {
                            'beginAtZero': True,
                            'title': {
                                'display': True,
                                'text': 'Amount (₹)'
                            }
                        }
                    }
                }
            },
            'payment_method_breakdown': {
                'chart_type': 'pie',
                'labels': payment_methods,
                'datasets': [{
                    'data': payment_amounts,
                    'backgroundColor': [payment_colors.get(method, '#999999') for method in PaymentMethod]
                }],
                'options': {
                    'responsive': True,
                    'plugins': {
                        'legend': {
                            'position': 'right'
                        }
                    }
                }
            },
            'collection_summary': {
                'total_collected': float(total_collected) / 100,
                'total_pending': float(total_pending) / 100,
                'collection_rate': (total_collected / (total_collected + total_pending)) * 100 if (total_collected + total_pending) > 0 else 0,
                'chart_type': 'doughnut',
                'labels': ['Collected', 'Pending'],
                'datasets': [{
                    'data': [float(total_collected) / 100, float(total_pending) / 100],
                    'backgroundColor': ['#4BC0C0', '#FF6384']
                }]
            },
            'metadata': {
                'year': current_year,
                'total_transactions': sum(count for _, _, count in payment_method_data),
                'last_updated': datetime.utcnow().isoformat()
            }
        })
        
    except Exception as e:
        return format_response(
            False,
            message=f"Error fetching fee collection charts: {str(e)}",
            status_code=500
        )

# WebSocket Events for Real-time Dashboard Updates
@socketio.on('connect', namespace='/dashboard')
def handle_dashboard_connect(auth):
    """Handle WebSocket connection for dashboard updates"""
    try:
        # Authenticate user using JWT token
        if not auth or 'token' not in auth:
            return False
        
        token = auth['token']
        
        # Verify JWT token
        from flask_jwt_extended import decode_token
        try:
            decoded = decode_token(token)
            user_id = decoded['sub']
            user_type = decoded.get('user_type', 'student')
            
            # Join appropriate room based on user role
            if user_type == 'staff':
                staff = Staff.get_by_employee_id(user_id)
                if staff and staff.role == StaffRole.ADMIN:
                    join_room('admin_dashboard')
                else:
                    join_room('staff_dashboard')
            elif user_type == 'student':
                join_room('student_dashboard')
                join_room(f'student_{user_id}')  # Personal room for student-specific updates
            
            emit('connection_status', {
                'status': 'connected',
                'user_type': user_type,
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            return False
            
    except Exception as e:
        return False

@socketio.on('disconnect', namespace='/dashboard')
def handle_dashboard_disconnect():
    """Handle WebSocket disconnection"""
    pass

@socketio.on('request_stats', namespace='/dashboard')
def handle_stats_request(data):
    """Handle request for real-time stats"""
    try:
        # Get current user from rooms to determine access level
        user_rooms = rooms()
        
        if 'admin_dashboard' in user_rooms:
            stats = _get_real_time_admin_stats()
        elif 'staff_dashboard' in user_rooms:
            stats = _get_real_time_staff_stats()
        else:
            stats = {'message': 'Limited access'}
        
        emit('stats_update', {
            'data': stats,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        emit('error', {'message': 'Error fetching stats'})

def _get_real_time_admin_stats():
    """Get real-time statistics for admin dashboard"""
    return {
        'pending_applications': db.session.query(func.count(AdmissionApplication.id)).filter_by(status=ApplicationStatus.SUBMITTED).scalar() or 0,
        'today_admissions': db.session.query(func.count(AdmissionApplication.id)).filter(
            func.date(AdmissionApplication.application_date) == date.today()
        ).scalar() or 0,
        'today_fee_collection': db.session.query(func.sum(Fee.amount)).filter(
            and_(Fee.status == FeeStatus.PAID, func.date(Fee.payment_date) == date.today())
        ).scalar() or 0,
        'online_students': db.session.query(func.count(Student.roll_no)).filter_by(is_active=True).scalar() or 0
    }

def _get_real_time_staff_stats():
    """Get real-time statistics for staff dashboard"""
    return {
        'pending_applications': db.session.query(func.count(AdmissionApplication.id)).filter_by(status=ApplicationStatus.SUBMITTED).scalar() or 0,
        'today_fee_collection': db.session.query(func.sum(Fee.amount)).filter(
            and_(Fee.status == FeeStatus.PAID, func.date(Fee.payment_date) == date.today())
        ).scalar() or 0
    }

# Utility functions for broadcasting real-time updates
def broadcast_admission_update(application_id, status, user_type='admin'):
    """Broadcast admission status update to dashboard clients"""
    try:
        room = 'admin_dashboard' if user_type == 'admin' else 'staff_dashboard'
        socketio.emit('admission_update', {
            'application_id': application_id,
            'status': status,
            'timestamp': datetime.utcnow().isoformat(),
            'stats': _get_real_time_admin_stats() if user_type == 'admin' else _get_real_time_staff_stats()
        }, room=room, namespace='/dashboard')
    except Exception as e:
        pass

def broadcast_fee_payment_update(student_id, amount, payment_method):
    """Broadcast fee payment update to dashboard clients"""
    try:
        socketio.emit('fee_payment_update', {
            'student_id': student_id,
            'amount': float(amount) / 100,  # Convert paise to rupees
            'payment_method': payment_method.value if hasattr(payment_method, 'value') else str(payment_method),
            'timestamp': datetime.utcnow().isoformat(),
            'stats': _get_real_time_admin_stats()
        }, room='admin_dashboard', namespace='/dashboard')
        
        # Also send to the specific student
        socketio.emit('personal_fee_update', {
            'amount': float(amount) / 100,
            'payment_method': payment_method.value if hasattr(payment_method, 'value') else str(payment_method),
            'status': 'paid',
            'timestamp': datetime.utcnow().isoformat()
        }, room=f'student_{student_id}', namespace='/dashboard')
        
    except Exception as e:
        pass

def broadcast_system_alert(message, level='info', target_rooms=None):
    """Broadcast system-wide alerts to dashboard clients"""
    try:
        if target_rooms is None:
            target_rooms = ['admin_dashboard', 'staff_dashboard']
        
        for room in target_rooms:
            socketio.emit('system_alert', {
                'message': message,
                'level': level,
                'timestamp': datetime.utcnow().isoformat()
            }, room=room, namespace='/dashboard')
            
    except Exception as e:
        pass
