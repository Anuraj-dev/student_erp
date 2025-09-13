"""
Authentication API Documentation
Comprehensive documentation for authentication and authorization endpoints
"""

from flask_restx import Resource, fields
from flask import request
from app.documentation import (
    auth_ns, login_model, register_student_model, token_model, 
    success_model, error_model, user_info_model
)

@auth_ns.route('/login')
class LoginAPI(Resource):
    @auth_ns.doc('login_user',
        description='''
        **User Authentication**
        
        Authenticate users (students or staff) and generate JWT access tokens.
        
        **Process:**
        1. Validates email/roll_no and password
        2. Checks both Student and Staff tables
        3. Generates JWT token with user role and permissions
        4. Returns user information and access token
        
        **Token Expiry:**
        - Students: 24 hours
        - Staff: 8 hours
        - Admin: 8 hours
        
        **Rate Limiting:** 10 requests per 5 minutes per IP
        ''')
    @auth_ns.expect(login_model, validate=True)
    @auth_ns.marshal_with(token_model, code=200, description='Login successful')
    @auth_ns.response(400, 'Invalid credentials', error_model)
    @auth_ns.response(401, 'Authentication failed', error_model)
    @auth_ns.response(429, 'Rate limit exceeded', error_model)
    def post(self):
        """Login user and generate JWT token"""
        pass

@auth_ns.route('/register/student')
class StudentRegisterAPI(Resource):
    @auth_ns.doc('register_student',
        description='''
        **Student Self-Registration**
        
        Allow students to register themselves in the system.
        
        **Process:**
        1. Validates all input data
        2. Checks for existing email/phone duplicates
        3. Generates unique roll number
        4. Creates student record with hashed password
        5. Sends welcome email with login instructions
        
        **Roll Number Format:** YEAR + COURSE_CODE + SERIAL (e.g., 2024CS001)
        
        **Password Requirements:**
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter  
        - At least one number
        - At least one special character
        ''')
    @auth_ns.expect(register_student_model, validate=True)
    @auth_ns.marshal_with(success_model, code=201, description='Registration successful')
    @auth_ns.response(400, 'Validation errors', error_model)
    @auth_ns.response(409, 'Email or phone already exists', error_model)
    def post(self):
        """Register new student"""
        pass

@auth_ns.route('/refresh')
class TokenRefreshAPI(Resource):
    @auth_ns.doc('refresh_token',
        description='''
        **Token Refresh**
        
        Generate new access token using refresh token.
        
        **Process:**
        1. Validates refresh token from request
        2. Checks if token is not blacklisted
        3. Generates new access token
        4. Maintains same permissions and user info
        
        **Headers Required:**
        ```
        Authorization: Bearer <refresh_token>
        ```
        ''',
        security='Bearer Auth')
    @auth_ns.marshal_with(token_model, code=200, description='Token refreshed successfully')
    @auth_ns.response(401, 'Invalid or expired refresh token', error_model)
    @auth_ns.response(403, 'Token blacklisted', error_model)
    def post(self):
        """Refresh JWT access token"""
        pass

@auth_ns.route('/logout')
class LogoutAPI(Resource):
    @auth_ns.doc('logout_user',
        description='''
        **User Logout**
        
        Logout user and blacklist current token.
        
        **Process:**
        1. Extracts JWT token from Authorization header
        2. Adds token to blacklist (Redis/memory)
        3. Clears any server-side sessions
        4. Logs logout activity
        
        **Headers Required:**
        ```
        Authorization: Bearer <access_token>
        ```
        ''',
        security='Bearer Auth')
    @auth_ns.marshal_with(success_model, code=200, description='Logout successful')
    @auth_ns.response(401, 'Invalid token', error_model)
    def post(self):
        """Logout user and blacklist token"""
        pass

@auth_ns.route('/me')
class UserProfileAPI(Resource):
    @auth_ns.doc('get_user_profile',
        description='''
        **Get Current User Profile**
        
        Retrieve current authenticated user's profile information.
        
        **Returns:**
        - User basic information
        - Role and permissions
        - Last login time
        - Account status
        
        **Headers Required:**
        ```
        Authorization: Bearer <access_token>
        ```
        ''',
        security='Bearer Auth')
    @auth_ns.marshal_with(user_info_model, code=200, description='User profile retrieved')
    @auth_ns.response(401, 'Authentication required', error_model)
    def get(self):
        """Get current user profile"""
        pass

@auth_ns.route('/change-password')  
class ChangePasswordAPI(Resource):
    @auth_ns.doc('change_password',
        description='''
        **Change User Password**
        
        Allow authenticated users to change their password.
        
        **Process:**
        1. Validates current password
        2. Checks new password strength
        3. Updates password with secure hashing
        4. Invalidates all existing tokens (forces re-login)
        5. Logs password change activity
        
        **Password Policy:**
        - Minimum 8 characters
        - Must contain uppercase, lowercase, number, and special character
        - Cannot be same as last 3 passwords
        - Cannot contain common dictionary words
        ''',
        security='Bearer Auth')
    @auth_ns.expect(auth_ns.model('ChangePassword', {
        'current_password': fields.String(required=True, description='Current password'),
        'new_password': fields.String(required=True, description='New password'),
        'confirm_password': fields.String(required=True, description='Confirm new password')
    }), validate=True)
    @auth_ns.marshal_with(success_model, code=200, description='Password changed successfully')
    @auth_ns.response(400, 'Password validation failed', error_model)
    @auth_ns.response(401, 'Current password incorrect', error_model)
    def post(self):
        """Change user password"""
        pass

@auth_ns.route('/forgot-password')
class ForgotPasswordAPI(Resource):
    @auth_ns.doc('forgot_password',
        description='''
        **Forgot Password Request**
        
        Initiate password reset process for users.
        
        **Process:**
        1. Validates email/roll_no exists in system
        2. Generates secure password reset token
        3. Sends reset link via email
        4. Token expires in 1 hour
        5. Logs password reset request
        
        **Rate Limiting:** 3 requests per hour per email
        ''')
    @auth_ns.expect(auth_ns.model('ForgotPassword', {
        'email': fields.String(required=True, description='Email or roll number')
    }), validate=True)
    @auth_ns.marshal_with(success_model, code=200, description='Reset email sent')
    @auth_ns.response(404, 'User not found', error_model)
    @auth_ns.response(429, 'Too many reset requests', error_model)
    def post(self):
        """Request password reset"""
        pass

@auth_ns.route('/reset-password')
class ResetPasswordAPI(Resource):
    @auth_ns.doc('reset_password',
        description='''
        **Reset Password**
        
        Reset user password using reset token from email.
        
        **Process:**
        1. Validates reset token
        2. Checks token expiry (1 hour)
        3. Validates new password strength
        4. Updates password with secure hashing
        5. Invalidates reset token
        6. Sends confirmation email
        ''')
    @auth_ns.expect(auth_ns.model('ResetPassword', {
        'token': fields.String(required=True, description='Password reset token'),
        'new_password': fields.String(required=True, description='New password'),
        'confirm_password': fields.String(required=True, description='Confirm new password')
    }), validate=True)
    @auth_ns.marshal_with(success_model, code=200, description='Password reset successful')
    @auth_ns.response(400, 'Invalid or expired token', error_model)
    @auth_ns.response(422, 'Password validation failed', error_model)
    def post(self):
        """Reset password with token"""
        pass

@auth_ns.route('/verify-token')
class VerifyTokenAPI(Resource):
    @auth_ns.doc('verify_token',
        description='''
        **Verify JWT Token**
        
        Verify if the provided JWT token is valid and not expired.
        
        **Use Cases:**
        - Frontend token validation
        - API gateway authentication
        - Session management
        
        **Returns:**
        - Token validity status
        - User information if valid
        - Expiry time remaining
        ''',
        security='Bearer Auth')
    @auth_ns.marshal_with(user_info_model, code=200, description='Token is valid')
    @auth_ns.response(401, 'Invalid or expired token', error_model)
    @auth_ns.response(403, 'Token blacklisted', error_model)
    def get(self):
        """Verify JWT token validity"""
        pass
