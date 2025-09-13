"""
API Documentation Configuration
Comprehensive Swagger/OpenAPI documentation for the ERP Student Management System
"""

from flask_restx import Api
from flask import Blueprint

# Create documentation blueprint
doc_bp = Blueprint('documentation', __name__)

# Configure API documentation
api = Api(
    doc_bp,
    version='1.0',
    title='Student ERP Management System API',
    description='''
    **Comprehensive ERP System for Educational Institutions**
    
    This API provides complete management functionality for:
    - **Student Management**: Registration, profiles, academic records
    - **Fee Management**: Payment processing, receipt generation, tracking
    - **Admission Management**: Application processing, document verification
    - **Hostel Management**: Room allocation, maintenance, visitor tracking
    - **Library Management**: Book inventory, issue/return, analytics
    - **Authentication**: JWT-based auth with role-based access control
    - **Dashboard & Analytics**: Real-time insights and reporting
    
    ## Authentication
    
    This API uses JWT (JSON Web Tokens) for authentication. Include the token in the Authorization header:
    ```
    Authorization: Bearer <your_jwt_token>
    ```
    
    ## Rate Limiting
    
    API endpoints are rate-limited:
    - General endpoints: 100 requests per minute
    - Authentication endpoints: 10 requests per 5 minutes
    
    ## Error Responses
    
    All endpoints return consistent error responses:
    ```json
    {
        "error": true,
        "message": "Error description",
        "code": "ERROR_CODE",
        "details": {}
    }
    ```
    
    ## Status Codes
    
    - **200**: Success
    - **201**: Created successfully  
    - **400**: Bad request (validation errors)
    - **401**: Unauthorized (authentication required)
    - **403**: Forbidden (insufficient permissions)
    - **404**: Resource not found
    - **429**: Rate limit exceeded
    - **500**: Internal server error
    ''',
    doc='/docs/',
    contact='ERP Development Team',
    license='MIT License',
    authorizations={
        'Bearer Auth': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization',
            'description': 'JWT Authorization header using the Bearer scheme. Example: "Authorization: Bearer {token}"'
        }
    },
    security='Bearer Auth'
)

# Configure namespaces for different modules
auth_ns = api.namespace('auth', description='Authentication and Authorization')
student_ns = api.namespace('students', description='Student Management Operations')  
fee_ns = api.namespace('fees', description='Fee Management and Payment Processing')
admission_ns = api.namespace('admissions', description='Admission Application Management')
hostel_ns = api.namespace('hostels', description='Hostel Management Operations')
library_ns = api.namespace('library', description='Library Management System')
dashboard_ns = api.namespace('dashboard', description='Analytics and Dashboard')

# Common response models
from flask_restx import fields

# Success response model
success_model = api.model('Success Response', {
    'success': fields.Boolean(required=True, description='Operation success status'),
    'message': fields.String(required=True, description='Success message'),
    'data': fields.Raw(description='Response data')
})

# Error response model  
error_model = api.model('Error Response', {
    'error': fields.Boolean(required=True, description='Error flag'),
    'message': fields.String(required=True, description='Error message'),
    'code': fields.String(description='Error code'),
    'details': fields.Raw(description='Additional error details')
})

# Pagination model
pagination_model = api.model('Pagination', {
    'page': fields.Integer(required=True, description='Current page number'),
    'per_page': fields.Integer(required=True, description='Items per page'),
    'total': fields.Integer(required=True, description='Total number of items'),
    'pages': fields.Integer(required=True, description='Total number of pages')
})

# JWT token response model
token_model = api.model('JWT Token', {
    'access_token': fields.String(required=True, description='JWT access token'),
    'token_type': fields.String(required=True, description='Token type (Bearer)'),
    'expires_in': fields.Integer(required=True, description='Token expiry time in seconds'),
    'user_type': fields.String(required=True, description='User type (student/staff)'),
    'permissions': fields.List(fields.String(), description='User permissions')
})

# User info model
user_info_model = api.model('User Info', {
    'id': fields.String(required=True, description='User ID'),
    'name': fields.String(required=True, description='Full name'),
    'email': fields.String(required=True, description='Email address'),
    'role': fields.String(required=True, description='User role'),
    'permissions': fields.List(fields.String(), description='User permissions')
})


# Authentication Models
login_model = api.model('Login Request', {
    'email': fields.String(required=True, description='User email or roll number', example='student@example.com'),
    'password': fields.String(required=True, description='User password', example='password123')
})

register_student_model = api.model('Student Registration', {
    'full_name': fields.String(required=True, description='Full name', example='John Doe'),
    'email': fields.String(required=True, description='Email address', example='john@example.com'),
    'phone': fields.String(required=True, description='Phone number', example='+91-9876543210'),
    'date_of_birth': fields.Date(required=True, description='Date of birth', example='2000-05-15'),
    'gender': fields.String(required=True, description='Gender', enum=['male', 'female', 'other'], example='male'),
    'address': fields.String(required=True, description='Address', example='123 Main St, City'),
    'course_id': fields.Integer(required=True, description='Course ID', example=1),
    'password': fields.String(required=True, description='Password', example='SecurePass123!')
})

# Student Models
student_model = api.model('Student', {
    'roll_no': fields.String(required=True, description='Roll number', example='2024CS001'),
    'full_name': fields.String(required=True, description='Full name', example='John Doe'),
    'email': fields.String(required=True, description='Email address', example='john@example.com'),
    'phone': fields.String(required=True, description='Phone number', example='+91-9876543210'),
    'date_of_birth': fields.Date(required=True, description='Date of birth', example='2000-05-15'),
    'gender': fields.String(required=True, description='Gender', enum=['male', 'female', 'other']),
    'address': fields.String(description='Address'),
    'course_id': fields.Integer(required=True, description='Course ID'),
    'hostel_id': fields.Integer(description='Hostel ID if allocated'),
    'admission_year': fields.Integer(description='Year of admission'),
    'is_active': fields.Boolean(description='Student active status'),
    'created_on': fields.DateTime(description='Registration date')
})

student_update_model = api.model('Student Update', {
    'full_name': fields.String(description='Full name'),
    'email': fields.String(description='Email address'),
    'phone': fields.String(description='Phone number'),
    'address': fields.String(description='Address'),
    'is_active': fields.Boolean(description='Student status')
})

# Course Models
course_model = api.model('Course', {
    'id': fields.Integer(required=True, description='Course ID'),
    'program_level': fields.String(required=True, description='Program level', example='Bachelor'),
    'degree_name': fields.String(required=True, description='Degree name', example='Engineering'),
    'course_name': fields.String(required=True, description='Course name', example='Computer Science'),
    'course_code': fields.String(required=True, description='Course code', example='CS'),
    'duration_years': fields.Integer(required=True, description='Course duration in years'),
    'fees_per_semester': fields.Integer(required=True, description='Fee per semester'),
    'total_seats': fields.Integer(description='Total available seats'),
    'is_active': fields.Boolean(description='Course active status')
})

# Fee Models
fee_model = api.model('Fee', {
    'id': fields.Integer(required=True, description='Fee ID'),
    'student_id': fields.String(required=True, description='Student roll number'),
    'fee_type': fields.String(required=True, description='Fee type', example='tuition'),
    'amount': fields.Float(required=True, description='Fee amount'),
    'due_date': fields.Date(required=True, description='Due date'),
    'status': fields.String(required=True, description='Payment status', enum=['pending', 'paid', 'overdue']),
    'semester': fields.Integer(description='Semester number'),
    'academic_year': fields.String(description='Academic year')
})

fee_payment_model = api.model('Fee Payment', {
    'student_id': fields.String(required=True, description='Student roll number'),
    'amount': fields.Float(required=True, description='Payment amount'),
    'payment_method': fields.String(required=True, description='Payment method', 
                                  enum=['cash', 'online', 'bank_transfer', 'dd', 'cheque']),
    'transaction_id': fields.String(description='Transaction ID for online payments'),
    'remarks': fields.String(description='Payment remarks')
})

fee_receipt_model = api.model('Fee Receipt', {
    'receipt_no': fields.String(required=True, description='Receipt number'),
    'student_name': fields.String(required=True, description='Student name'),
    'amount': fields.Float(required=True, description='Paid amount'),
    'payment_date': fields.DateTime(required=True, description='Payment date'),
    'payment_method': fields.String(required=True, description='Payment method'),
    'transaction_id': fields.String(description='Transaction ID'),
    'download_url': fields.String(description='PDF download URL')
})

# Admission Models
admission_application_model = api.model('Admission Application', {
    'id': fields.Integer(description='Application ID'),
    'application_no': fields.String(description='Application number'),
    'full_name': fields.String(required=True, description='Full name'),
    'email': fields.String(required=True, description='Email address'),
    'phone': fields.String(required=True, description='Phone number'),
    'date_of_birth': fields.Date(required=True, description='Date of birth'),
    'gender': fields.String(required=True, description='Gender'),
    'address': fields.String(required=True, description='Address'),
    'course_id': fields.Integer(required=True, description='Desired course ID'),
    'previous_education': fields.String(required=True, description='Previous education details'),
    'documents': fields.Raw(description='Uploaded documents'),
    'status': fields.String(description='Application status', 
                           enum=['pending', 'under_review', 'approved', 'rejected']),
    'applied_on': fields.DateTime(description='Application date'),
    'processed_by': fields.String(description='Staff who processed'),
    'remarks': fields.String(description='Processing remarks')
})

admission_create_model = api.model('Create Admission Application', {
    'full_name': fields.String(required=True, description='Full name'),
    'email': fields.String(required=True, description='Email address'),
    'phone': fields.String(required=True, description='Phone number'),
    'date_of_birth': fields.Date(required=True, description='Date of birth'),
    'gender': fields.String(required=True, description='Gender'),
    'address': fields.String(required=True, description='Address'),
    'course_id': fields.Integer(required=True, description='Course ID'),
    'previous_education': fields.String(required=True, description='Previous education'),
    'guardian_name': fields.String(description='Guardian name'),
    'guardian_phone': fields.String(description='Guardian phone'),
    'documents': fields.Raw(description='Document uploads')
})

# Hostel Models
hostel_model = api.model('Hostel', {
    'id': fields.Integer(required=True, description='Hostel ID'),
    'name': fields.String(required=True, description='Hostel name'),
    'hostel_type': fields.String(required=True, description='Hostel type', enum=['boys', 'girls']),
    'total_rooms': fields.Integer(required=True, description='Total rooms'),
    'occupied_rooms': fields.Integer(description='Occupied rooms'),
    'fee_per_month': fields.Float(required=True, description='Monthly fee'),
    'warden_name': fields.String(description='Warden name'),
    'warden_contact': fields.String(description='Warden contact'),
    'facilities': fields.List(fields.String(), description='Available facilities'),
    'is_active': fields.Boolean(description='Hostel status')
})

hostel_allocation_model = api.model('Hostel Allocation', {
    'student_id': fields.String(required=True, description='Student roll number'),
    'hostel_id': fields.Integer(required=True, description='Hostel ID'),
    'room_number': fields.String(required=True, description='Room number'),
    'allocation_date': fields.Date(description='Allocation date'),
    'remarks': fields.String(description='Allocation remarks')
})

# Library Models
library_book_model = api.model('Library Book', {
    'id': fields.Integer(description='Book ID'),
    'title': fields.String(required=True, description='Book title'),
    'author': fields.String(required=True, description='Author name'),
    'isbn': fields.String(required=True, description='ISBN number'),
    'category': fields.String(required=True, description='Book category'),
    'publisher': fields.String(description='Publisher name'),
    'published_year': fields.Integer(description='Publication year'),
    'total_copies': fields.Integer(required=True, description='Total copies'),
    'available_copies': fields.Integer(description='Available copies'),
    'location': fields.String(description='Library location/shelf'),
    'is_active': fields.Boolean(description='Book status')
})

book_issue_model = api.model('Book Issue', {
    'student_id': fields.String(required=True, description='Student roll number'),
    'book_id': fields.Integer(required=True, description='Book ID'),
    'issue_date': fields.Date(description='Issue date'),
    'due_date': fields.Date(description='Due date'),
    'returned_date': fields.Date(description='Return date'),
    'status': fields.String(description='Issue status', enum=['issued', 'returned', 'overdue']),
    'fine_amount': fields.Float(description='Fine amount if overdue')
})

# Dashboard Models
dashboard_stats_model = api.model('Dashboard Statistics', {
    'total_students': fields.Integer(description='Total students'),
    'total_staff': fields.Integer(description='Total staff'),
    'pending_admissions': fields.Integer(description='Pending admissions'),
    'total_fee_collected': fields.Float(description='Total fee collected'),
    'pending_fees': fields.Float(description='Pending fees'),
    'hostel_occupancy': fields.Float(description='Hostel occupancy percentage'),
    'library_books_issued': fields.Integer(description='Books currently issued'),
    'recent_activities': fields.List(fields.Raw(), description='Recent system activities')
})

# Additional missing models
fee_structure_model = api.model('Fee Structure', {
    'course_id': fields.Integer(required=True, description='Course ID'),
    'course_name': fields.String(description='Course name'),
    'tuition_fee': fields.Float(required=True, description='Tuition fee amount'),
    'hostel_fee': fields.Float(description='Hostel fee amount'),
    'library_fee': fields.Float(description='Library fee amount'),
    'laboratory_fee': fields.Float(description='Laboratory fee amount'),
    'sports_fee': fields.Float(description='Sports fee amount'),
    'miscellaneous_fee': fields.Float(description='Miscellaneous fee amount'),
    'total_fee': fields.Float(description='Total fee amount'),
    'academic_year': fields.String(description='Academic year'),
    'effective_date': fields.DateTime(description='Effective date')
})

dashboard_activity_model = api.model('Dashboard Activity', {
    'id': fields.Integer(description='Activity ID'),
    'type': fields.String(description='Activity type'),
    'title': fields.String(description='Activity title'),
    'description': fields.String(description='Activity description'),
    'user': fields.String(description='User who performed the activity'),
    'timestamp': fields.DateTime(description='Activity timestamp'),
    'status': fields.String(description='Activity status')
})

# Additional model aliases for compatibility
student_update_model = student_model
hostel_room_model = hostel_model
library_member_model = student_model
book_model = library_book_model
admission_model = admission_application_model
admission_update_model = admission_application_model

# Export all models and namespaces
__all__ = [
    'api', 'doc_bp',
    'auth_ns', 'student_ns', 'fee_ns', 'admission_ns', 'hostel_ns', 'library_ns', 'dashboard_ns',
    'success_model', 'error_model', 'pagination_model', 'token_model', 'user_info_model',
    'login_model', 'register_student_model', 'student_model', 'student_update_model',
    'course_model', 'fee_model', 'fee_payment_model', 'fee_receipt_model', 'fee_structure_model',
    'admission_application_model', 'admission_create_model', 'admission_model', 'admission_update_model',
    'hostel_model', 'hostel_allocation_model', 'hostel_room_model',
    'library_book_model', 'book_issue_model', 'book_model', 'library_member_model',
    'dashboard_stats_model', 'dashboard_activity_model'
]
