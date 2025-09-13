from functools import wraps
from flask import jsonify, request, current_app, g
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, verify_jwt_in_request
from app.models.student import Student
from app.models.staff import Staff, StaffRole
from app.models.admission import AdmissionApplication

def get_current_user():
    """Get current user from JWT token"""
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        claims = get_jwt()
        user_type = claims.get('user_type', 'student')
        
        user = None
        if user_type == 'student':
            user = Student.get_by_roll_no(user_id)
        elif user_type == 'staff':
            user = Staff.get_by_employee_id(user_id)
        elif user_type == 'applicant':
            user = AdmissionApplication.get_by_application_id(user_id)
        
        return user, user_type, claims
    except Exception as e:
        current_app.logger.error(f"Error getting current user: {e}")
        return None, None, None

def jwt_required_custom(f):
    """Custom JWT required decorator that loads user into context"""
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        user, user_type, claims = get_current_user()
        
        if not user:
            return jsonify({
                'error': True,
                'message': 'User not found or inactive',
                'code': 'USER_NOT_FOUND'
            }), 401
        
        # Check if user is active
        if hasattr(user, 'is_active') and not user.is_active:
            return jsonify({
                'error': True,
                'message': 'Account is deactivated',
                'code': 'ACCOUNT_DEACTIVATED'
            }), 401
        
        # Store user info in Flask's g object for use in routes
        g.current_user = user
        g.user_type = user_type
        g.user_claims = claims
        
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    """Decorator that requires admin role"""
    @wraps(f)
    @jwt_required_custom
    def decorated(*args, **kwargs):
        user = g.current_user
        user_type = g.user_type
        
        if user_type != 'staff' or not hasattr(user, 'role') or user.role != StaffRole.ADMIN:
            return jsonify({
                'error': True,
                'message': 'Admin access required',
                'code': 'ADMIN_REQUIRED'
            }), 403
        
        return f(*args, **kwargs)
    return decorated

def staff_required(f):
    """Decorator that requires staff or admin role"""
    @wraps(f)
    @jwt_required_custom
    def decorated(*args, **kwargs):
        user = g.current_user
        user_type = g.user_type
        
        if user_type != 'staff':
            return jsonify({
                'error': True,
                'message': 'Staff access required',
                'code': 'STAFF_REQUIRED'
            }), 403
        
        # Check if staff has sufficient role (staff or admin)
        if not hasattr(user, 'role') or user.role not in [StaffRole.STAFF, StaffRole.ADMIN]:
            return jsonify({
                'error': True,
                'message': 'Insufficient privileges',
                'code': 'INSUFFICIENT_PRIVILEGES'
            }), 403
        
        return f(*args, **kwargs)
    return decorated

def faculty_required(f):
    """Decorator that allows faculty, staff, and admin roles"""
    @wraps(f)
    @jwt_required_custom
    def decorated(*args, **kwargs):
        user = g.current_user
        user_type = g.user_type
        
        if user_type != 'staff':
            return jsonify({
                'error': True,
                'message': 'Faculty access required',
                'code': 'FACULTY_REQUIRED'
            }), 403
        
        # Check if user has any staff role
        if not hasattr(user, 'role') or user.role not in [StaffRole.FACULTY, StaffRole.STAFF, StaffRole.ADMIN]:
            return jsonify({
                'error': True,
                'message': 'Faculty privileges required',
                'code': 'FACULTY_PRIVILEGES_REQUIRED'
            }), 403
        
        return f(*args, **kwargs)
    return decorated

def student_required(f):
    """Decorator that requires student role"""
    @wraps(f)
    @jwt_required_custom
    def decorated(*args, **kwargs):
        user_type = g.user_type
        
        if user_type != 'student':
            return jsonify({
                'error': True,
                'message': 'Student access required',
                'code': 'STUDENT_REQUIRED'
            }), 403
        
        return f(*args, **kwargs)
    return decorated

def owner_or_admin_required(resource_id_param='id'):
    """
    Decorator that allows resource owner or admin access
    resource_id_param: parameter name in URL that contains the resource ID to check ownership
    """
    def decorator(f):
        @wraps(f)
        @jwt_required_custom
        def decorated(*args, **kwargs):
            user = g.current_user
            user_type = g.user_type
            
            # Get resource ID from URL parameters or request data
            resource_id = kwargs.get(resource_id_param)
            if not resource_id and request.method in ['POST', 'PUT']:
                data = request.get_json() or {}
                resource_id = data.get(resource_id_param)
            
            # Admin can access everything
            if user_type == 'staff' and hasattr(user, 'role') and user.role == StaffRole.ADMIN:
                return f(*args, **kwargs)
            
            # Check ownership based on user type
            if user_type == 'student':
                user_id = getattr(user, 'roll_no', None)
            elif user_type == 'staff':
                user_id = getattr(user, 'employee_id', None)
            elif user_type == 'applicant':
                user_id = getattr(user, 'application_id', None)
            else:
                user_id = None
            
            # Check if user owns the resource
            if str(resource_id) != str(user_id):
                return jsonify({
                    'error': True,
                    'message': 'Access denied. You can only access your own resources.',
                    'code': 'ACCESS_DENIED'
                }), 403
            
            return f(*args, **kwargs)
        return decorated
    return decorator

def role_required(*allowed_roles):
    """
    Decorator that checks for specific roles
    Usage: @role_required('admin', 'staff')
    """
    def decorator(f):
        @wraps(f)
        @jwt_required_custom
        def decorated(*args, **kwargs):
            user = g.current_user
            user_type = g.user_type
            claims = g.user_claims
            
            user_role = claims.get('role', 'student')
            
            if user_role not in allowed_roles:
                return jsonify({
                    'error': True,
                    'message': f'Access denied. Required roles: {", ".join(allowed_roles)}',
                    'code': 'INSUFFICIENT_ROLE'
                }), 403
            
            return f(*args, **kwargs)
        return decorated
    return decorator

def permission_required(*required_permissions):
    """
    Decorator that checks for specific permissions
    Usage: @permission_required('read', 'write')
    """
    def decorator(f):
        @wraps(f)
        @jwt_required_custom
        def decorated(*args, **kwargs):
            user = g.current_user
            user_type = g.user_type
            claims = g.user_claims
            
            # Get user permissions based on role
            user_permissions = []
            user_role = claims.get('role', 'student')
            
            if user_type == 'staff':
                if user_role == 'admin':
                    user_permissions = ['read', 'write', 'delete', 'admin']
                elif user_role == 'staff':
                    user_permissions = ['read', 'write']
                elif user_role == 'faculty':
                    user_permissions = ['read', 'grades']
            elif user_type == 'student':
                user_permissions = ['read', 'student']
            elif user_type == 'applicant':
                user_permissions = ['read', 'applicant']
            
            # Check if user has all required permissions
            if not all(perm in user_permissions for perm in required_permissions):
                return jsonify({
                    'error': True,
                    'message': f'Access denied. Required permissions: {", ".join(required_permissions)}',
                    'code': 'INSUFFICIENT_PERMISSIONS'
                }), 403
            
            return f(*args, **kwargs)
        return decorated
    return decorator

def log_access(action_description=""):
    """
    Decorator to log user actions for audit trail
    """
    def decorator(f):
        @wraps(f)
        @jwt_required_custom
        def decorated(*args, **kwargs):
            user = g.current_user
            user_type = g.user_type
            user_id = get_jwt_identity()
            
            # Log the action
            current_app.logger.info(
                f"Action: {action_description or f.__name__} | "
                f"User: {user_id} ({user_type}) | "
                f"IP: {request.remote_addr} | "
                f"Method: {request.method} | "
                f"Endpoint: {request.endpoint}"
            )
            
            result = f(*args, **kwargs)
            
            # Log successful completion
            current_app.logger.info(f"Action completed: {action_description or f.__name__} by {user_id}")
            
            return result
        return decorated
    return decorator

# Convenience decorators combining common patterns
def admin_or_owner_required(resource_id_param='id'):
    """Combines admin_required and owner_required logic"""
    def decorator(f):
        @wraps(f)
        @jwt_required_custom
        def decorated(*args, **kwargs):
            user = g.current_user
            user_type = g.user_type
            
            # Check if admin
            if user_type == 'staff' and hasattr(user, 'role') and user.role == StaffRole.ADMIN:
                return f(*args, **kwargs)
            
            # Apply owner check for non-admin users
            resource_id = kwargs.get(resource_id_param)
            if not resource_id and request.method in ['POST', 'PUT']:
                data = request.get_json() or {}
                resource_id = data.get(resource_id_param)
            
            # Check ownership based on user type
            if user_type == 'student':
                user_id = getattr(user, 'roll_no', None)
            elif user_type == 'staff':
                user_id = getattr(user, 'employee_id', None)
            elif user_type == 'applicant':
                user_id = getattr(user, 'application_id', None)
            else:
                user_id = None
            
            # Check if user owns the resource
            if str(resource_id) != str(user_id):
                return jsonify({
                    'error': True,
                    'message': 'Access denied. You can only access your own resources.',
                    'code': 'ACCESS_DENIED'
                }), 403
            
            return f(*args, **kwargs)
        return decorated
    return decorator
