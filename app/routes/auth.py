from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required,
    get_jwt_identity, get_jwt, verify_jwt_in_request
)
from datetime import datetime, timedelta
from app import db
from app.models.student import Student
from app.models.staff import Staff
from app.models.admission import AdmissionApplication

# Authentication routes blueprint
auth_bp = Blueprint('auth', __name__)

def blacklist_token(jti):
    """Add token to blacklist in Redis"""
    try:
        if current_app.redis:
            # Set token in Redis with expiration (24 hours for access token)
            current_app.redis.set(jti, 'blacklisted', ex=86400)
            return True
    except Exception as e:
        current_app.logger.error(f"Error blacklisting token: {e}")
    return False

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    User login endpoint
    Accepts email/roll_no and password
    Returns JWT token with role and user data
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': True,
                'message': 'Invalid request format',
                'code': 'INVALID_REQUEST'
            }), 400
        
        identifier = data.get('identifier')  # email or roll_no
        password = data.get('password')
        
        if not identifier or not password:
            return jsonify({
                'error': True,
                'message': 'Identifier and password are required',
                'code': 'MISSING_CREDENTIALS'
            }), 400
        
        user = None
        user_type = None
        
        # Try to find student first (by roll_no or email)
        if '@' in identifier:
            user = Student.get_by_email(identifier)
            if user:
                user_type = 'student'
        else:
            user = Student.get_by_roll_no(identifier)
            if user:
                user_type = 'student'
        
        # If not found as student, try staff
        if not user and '@' in identifier:
            user = Staff.get_by_email(identifier)
            if user:
                user_type = 'staff'
        
        # If still not found, try admission application
        if not user:
            user = AdmissionApplication.get_by_application_id(identifier)
            if user:
                user_type = 'applicant'
        
        if not user or not user.check_password(password):
            return jsonify({
                'error': True,
                'message': 'Invalid credentials',
                'code': 'INVALID_CREDENTIALS'
            }), 401
        
        # Check if user is active
        if hasattr(user, 'is_active') and not user.is_active:
            return jsonify({
                'error': True,
                'message': 'Account is deactivated',
                'code': 'ACCOUNT_DEACTIVATED'
            }), 401
        
        # Create JWT tokens
        user_id = getattr(user, 'roll_no', None) or getattr(user, 'employee_id', None) or getattr(user, 'application_id', None)
        
        # Token expiry based on user type
        if user_type == 'staff':
            access_expires = timedelta(hours=8)
            refresh_expires = timedelta(days=7)
        else:
            access_expires = timedelta(hours=24)
            refresh_expires = timedelta(days=30)
        
        # Additional claims for JWT
        additional_claims = {
            'user_type': user_type,
            'role': getattr(user, 'role', None).value if hasattr(user, 'role') and user.role else 'student',
            'name': user.name,
            'email': user.email
        }
        
        access_token = create_access_token(
            identity=user_id,
            expires_delta=access_expires,
            additional_claims=additional_claims
        )
        
        refresh_token = create_refresh_token(
            identity=user_id,
            expires_delta=refresh_expires,
            additional_claims={'user_type': user_type}
        )
        
        # Update last login
        if hasattr(user, 'update_last_login'):
            user.update_last_login()
        
        # Prepare user data for response
        user_data = user.to_dict()
        
        # Determine permissions based on role
        permissions = []
        if user_type == 'staff':
            if user.role.value == 'admin':
                permissions = ['read', 'write', 'delete', 'admin']
            elif user.role.value == 'staff':
                permissions = ['read', 'write']
            elif user.role.value == 'faculty':
                permissions = ['read', 'grades']
        elif user_type == 'student':
            permissions = ['read', 'student']
        elif user_type == 'applicant':
            permissions = ['read', 'applicant']
        
        return jsonify({
            'error': False,
            'message': 'Login successful',
            'data': {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user_type': user_type,
                'user_data': user_data,
                'permissions': permissions,
                'expires_in': access_expires.total_seconds()
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Login error: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error during login',
            'code': 'LOGIN_ERROR'
        }), 500

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Refresh access token using refresh token
    """
    try:
        current_user_id = get_jwt_identity()
        claims = get_jwt()
        user_type = claims.get('user_type', 'student')
        
        # Verify user still exists and is active
        user = None
        if user_type == 'student':
            user = Student.get_by_roll_no(current_user_id)
        elif user_type == 'staff':
            user = Staff.get_by_employee_id(current_user_id)
        elif user_type == 'applicant':
            user = AdmissionApplication.get_by_application_id(current_user_id)
        
        if not user or (hasattr(user, 'is_active') and not user.is_active):
            return jsonify({
                'error': True,
                'message': 'User not found or inactive',
                'code': 'USER_INACTIVE'
            }), 401
        
        # Create new access token
        access_expires = timedelta(hours=8 if user_type == 'staff' else 24)
        
        additional_claims = {
            'user_type': user_type,
            'role': getattr(user, 'role', None).value if hasattr(user, 'role') and user.role else 'student',
            'name': user.name,
            'email': user.email
        }
        
        new_access_token = create_access_token(
            identity=current_user_id,
            expires_delta=access_expires,
            additional_claims=additional_claims
        )
        
        return jsonify({
            'error': False,
            'message': 'Token refreshed successfully',
            'data': {
                'access_token': new_access_token,
                'expires_in': access_expires.total_seconds()
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Token refresh error: {e}")
        return jsonify({
            'error': True,
            'message': 'Token refresh failed',
            'code': 'REFRESH_ERROR'
        }), 500

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout user by blacklisting current token
    """
    try:
        jti = get_jwt()['jti']
        
        # Add token to blacklist
        blacklisted = blacklist_token(jti)
        
        if blacklisted:
            return jsonify({
                'error': False,
                'message': 'Successfully logged out'
            }), 200
        else:
            return jsonify({
                'error': False,
                'message': 'Logged out (token blacklisting unavailable)'
            }), 200
            
    except Exception as e:
        current_app.logger.error(f"Logout error: {e}")
        return jsonify({
            'error': True,
            'message': 'Logout failed',
            'code': 'LOGOUT_ERROR'
        }), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """
    Get current user profile
    """
    try:
        current_user_id = get_jwt_identity()
        claims = get_jwt()
        user_type = claims.get('user_type', 'student')
        
        # Get user based on type
        user = None
        if user_type == 'student':
            user = Student.get_by_roll_no(current_user_id)
        elif user_type == 'staff':
            user = Staff.get_by_employee_id(current_user_id)
        elif user_type == 'applicant':
            user = AdmissionApplication.get_by_application_id(current_user_id)
        
        if not user:
            return jsonify({
                'error': True,
                'message': 'User not found',
                'code': 'USER_NOT_FOUND'
            }), 404
        
        return jsonify({
            'error': False,
            'message': 'Profile retrieved successfully',
            'data': {
                'user_type': user_type,
                'user_data': user.to_dict(),
                'role': claims.get('role', 'student')
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Profile error: {e}")
        return jsonify({
            'error': True,
            'message': 'Failed to get profile',
            'code': 'PROFILE_ERROR'
        }), 500

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """
    Change user password
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': True,
                'message': 'Invalid request format',
                'code': 'INVALID_REQUEST'
            }), 400
        
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({
                'error': True,
                'message': 'Current password and new password are required',
                'code': 'MISSING_PASSWORDS'
            }), 400
        
        if len(new_password) < 8:
            return jsonify({
                'error': True,
                'message': 'New password must be at least 8 characters long',
                'code': 'PASSWORD_TOO_SHORT'
            }), 400
        
        current_user_id = get_jwt_identity()
        claims = get_jwt()
        user_type = claims.get('user_type', 'student')
        
        # Get user based on type
        user = None
        if user_type == 'student':
            user = Student.get_by_roll_no(current_user_id)
        elif user_type == 'staff':
            user = Staff.get_by_employee_id(current_user_id)
        elif user_type == 'applicant':
            user = AdmissionApplication.get_by_application_id(current_user_id)
        
        if not user:
            return jsonify({
                'error': True,
                'message': 'User not found',
                'code': 'USER_NOT_FOUND'
            }), 404
        
        # Verify current password
        if not user.check_password(current_password):
            return jsonify({
                'error': True,
                'message': 'Current password is incorrect',
                'code': 'INVALID_CURRENT_PASSWORD'
            }), 401
        
        # Update password
        user.password = new_password
        db.session.commit()
        
        return jsonify({
            'error': False,
            'message': 'Password changed successfully'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Change password error: {e}")
        db.session.rollback()
        return jsonify({
            'error': True,
            'message': 'Failed to change password',
            'code': 'PASSWORD_CHANGE_ERROR'
        }), 500

@auth_bp.route('/verify-token', methods=['POST'])
@jwt_required()
def verify_token():
    """
    Verify if current token is valid
    """
    try:
        current_user_id = get_jwt_identity()
        claims = get_jwt()
        
        return jsonify({
            'error': False,
            'message': 'Token is valid',
            'data': {
                'user_id': current_user_id,
                'user_type': claims.get('user_type'),
                'role': claims.get('role'),
                'name': claims.get('name'),
                'email': claims.get('email')
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Token verification error: {e}")
        return jsonify({
            'error': True,
            'message': 'Token verification failed',
            'code': 'TOKEN_VERIFICATION_ERROR'
        }), 500

# Health check endpoint
@auth_bp.route('/health')
def auth_health():
    return {
        'status': 'auth routes operational',
        'endpoints': [
            'POST /login',
            'POST /refresh', 
            'POST /logout',
            'GET /profile',
            'POST /change-password',
            'POST /verify-token'
        ]
    }
