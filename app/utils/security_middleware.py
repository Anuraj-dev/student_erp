"""
Security Middleware for ERP System
Implements comprehensive security measures including:
- Security headers
- Rate limiting
- SQL injection prevention
- XSS protection
- CSRF protection
- Input validation and sanitization
"""

import time
import hashlib
import re
from collections import defaultdict, deque
from datetime import datetime, timedelta
from functools import wraps

from flask import request, jsonify, g, current_app
import redis
import html


class SecurityMiddleware:
    def __init__(self, app=None):
        self.app = app
        self.rate_limit_storage = defaultdict(lambda: deque())
        self.redis_client = None
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize security middleware with Flask app"""
        self.app = app
        
        # Get Redis client if available
        self.redis_client = app.config.get('redis_client')
        
        # Register before_request and after_request handlers
        app.before_request(self.before_request)
        app.after_request(self.after_request)
    
    def before_request(self):
        """Security checks before processing request"""
        # Set start time for performance monitoring
        g.start_time = time.time()
        
        # Apply security headers
        self.apply_security_headers()
        
        # Rate limiting
        if not self.check_rate_limit():
            return jsonify({
                'error': True,
                'message': 'Rate limit exceeded. Please try again later.',
                'code': 'RATE_LIMIT_EXCEEDED'
            }), 429
        
        # Input validation and sanitization
        if not self.validate_and_sanitize_input():
            return jsonify({
                'error': True,
                'message': 'Invalid or potentially malicious input detected',
                'code': 'INVALID_INPUT'
            }), 400
        
        # SQL injection prevention
        if self.detect_sql_injection():
            current_app.logger.warning(f"SQL injection attempt detected from {request.remote_addr}")
            return jsonify({
                'error': True,
                'message': 'Invalid request format',
                'code': 'INVALID_REQUEST'
            }), 400
        
        # XSS prevention
        if self.detect_xss_attempt():
            current_app.logger.warning(f"XSS attempt detected from {request.remote_addr}")
            return jsonify({
                'error': True,
                'message': 'Invalid content detected',
                'code': 'INVALID_CONTENT'
            }), 400
    
    def after_request(self, response):
        """Apply security headers after processing request"""
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'"
        )
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Remove server information
        response.headers.pop('Server', None)
        
        # Log performance metrics
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            if duration > 1.0:  # Log slow requests
                current_app.logger.warning(
                    f"Slow request: {request.method} {request.path} took {duration:.2f}s"
                )
        
        return response
    
    def apply_security_headers(self):
        """Apply additional security headers"""
        # Prevent MIME type sniffing
        g.security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block'
        }
    
    def check_rate_limit(self):
        """Implement rate limiting based on IP address"""
        if not hasattr(current_app, 'config'):
            return True
        
        client_ip = self.get_client_ip()
        current_time = time.time()
        
        # Different limits for different endpoints
        if request.endpoint and 'auth' in request.endpoint:
            # Stricter limits for auth endpoints
            limit = 10  # requests
            window = 300  # 5 minutes
        else:
            # General API limits
            limit = 100  # requests
            window = 60   # 1 minute
        
        # Use Redis if available, otherwise use in-memory storage
        if self.redis_client:
            return self._check_rate_limit_redis(client_ip, limit, window)
        else:
            return self._check_rate_limit_memory(client_ip, limit, window)
    
    def _check_rate_limit_redis(self, client_ip, limit, window):
        """Rate limiting using Redis"""
        try:
            key = f"rate_limit:{client_ip}"
            current_count = self.redis_client.incr(key)
            
            if current_count == 1:
                self.redis_client.expire(key, window)
            
            return current_count <= limit
        except Exception as e:
            current_app.logger.error(f"Redis rate limiting error: {e}")
            return True  # Allow request if Redis fails
    
    def _check_rate_limit_memory(self, client_ip, limit, window):
        """Rate limiting using in-memory storage"""
        current_time = time.time()
        requests = self.rate_limit_storage[client_ip]
        
        # Remove old requests outside the window
        while requests and requests[0] < current_time - window:
            requests.popleft()
        
        # Check if limit exceeded
        if len(requests) >= limit:
            return False
        
        # Add current request
        requests.append(current_time)
        return True
    
    def get_client_ip(self):
        """Get client IP address considering proxies"""
        # Check for forwarded IPs (when behind proxy/load balancer)
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        else:
            return request.remote_addr or '127.0.0.1'
    
    def validate_and_sanitize_input(self):
        """Validate and sanitize all input data"""
        try:
            # Sanitize URL parameters
            if request.args:
                for key, value in request.args.items():
                    if not self._is_safe_input(value):
                        return False
            
            # Sanitize JSON data
            if request.is_json and request.get_json():
                data = request.get_json()
                if not self._sanitize_json_recursively(data):
                    return False
            
            # Sanitize form data
            if request.form:
                for key, value in request.form.items():
                    if not self._is_safe_input(value):
                        return False
            
            return True
        except Exception as e:
            current_app.logger.error(f"Input validation error: {e}")
            return False
    
    def _sanitize_json_recursively(self, data):
        """Recursively sanitize JSON data"""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str):
                    if not self._is_safe_input(value):
                        return False
                    # Sanitize the value
                    data[key] = self._sanitize_string(value)
                elif isinstance(value, (dict, list)):
                    if not self._sanitize_json_recursively(value):
                        return False
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, str):
                    if not self._is_safe_input(item):
                        return False
                    data[i] = self._sanitize_string(item)
                elif isinstance(item, (dict, list)):
                    if not self._sanitize_json_recursively(item):
                        return False
        
        return True
    
    def _is_safe_input(self, value):
        """Check if input is safe from common attacks"""
        if not isinstance(value, str):
            return True
        
        # Check for extremely long inputs (potential DoS)
        if len(value) > 10000:
            return False
        
        # Check for null bytes
        if '\x00' in value:
            return False
        
        # Check for control characters (except common ones like \n, \t, \r)
        for char in value:
            if ord(char) < 32 and char not in ['\n', '\t', '\r']:
                return False
        
        return True
    
    def _sanitize_string(self, value):
        """Sanitize string input"""
        # HTML escape
        sanitized = html.escape(value)
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        # Remove/escape potentially dangerous characters
        sanitized = re.sub(r'[<>"\']', '', sanitized)
        
        return sanitized.strip()
    
    def detect_sql_injection(self):
        """Detect potential SQL injection attempts"""
        sql_keywords = [
            'union', 'select', 'insert', 'update', 'delete', 'drop', 'create',
            'alter', 'exec', 'execute', 'script', 'xp_', 'sp_', 'declare',
            'cast', 'convert', 'concat', 'char', 'ascii', 'substring',
            'information_schema', 'sys.', 'master.', 'msdb.', 'tempdb.',
            'pg_', 'mysql.', 'sqlite_'
        ]
        
        # Check URL parameters
        if request.args:
            for key, value in request.args.items():
                if self._contains_sql_injection(value, sql_keywords):
                    return True
        
        # Check JSON data
        if request.is_json:
            try:
                data = request.get_json()
                if self._check_json_for_sql_injection(data, sql_keywords):
                    return True
            except Exception:
                pass
        
        # Check form data
        if request.form:
            for key, value in request.form.items():
                if self._contains_sql_injection(value, sql_keywords):
                    return True
        
        return False
    
    def _contains_sql_injection(self, value, sql_keywords):
        """Check if value contains SQL injection patterns"""
        if not isinstance(value, str):
            return False
        
        value_lower = value.lower()
        
        # Check for SQL keywords
        for keyword in sql_keywords:
            if keyword in value_lower:
                return True
        
        # Check for common SQL injection patterns
        patterns = [
            r"'.*or.*'.*'",  # ' OR '1'='1
            r'".*or.*".*"',  # " OR "1"="1
            r";\s*(drop|delete|update|insert)",  # ; DROP TABLE
            r"--",  # SQL comment
            r"/\*.*\*/",  # SQL comment
            r"@@\w+",  # System variables
            r"0x[0-9a-f]+",  # Hex values
        ]
        
        for pattern in patterns:
            if re.search(pattern, value_lower):
                return True
        
        return False
    
    def _check_json_for_sql_injection(self, data, sql_keywords):
        """Recursively check JSON data for SQL injection"""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str):
                    if self._contains_sql_injection(value, sql_keywords):
                        return True
                elif isinstance(value, (dict, list)):
                    if self._check_json_for_sql_injection(value, sql_keywords):
                        return True
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    if self._contains_sql_injection(item, sql_keywords):
                        return True
                elif isinstance(item, (dict, list)):
                    if self._check_json_for_sql_injection(item, sql_keywords):
                        return True
        
        return False
    
    def detect_xss_attempt(self):
        """Detect potential XSS attempts"""
        xss_patterns = [
            r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe\b',
            r'<object\b',
            r'<embed\b',
            r'<form\b',
            r'<img\b[^>]*src\s*=\s*["\']?\s*javascript:',
            r'<svg\b[^>]*onload',
            r'expression\s*\(',
            r'vbscript:',
            r'data:text/html',
        ]
        
        # Check URL parameters
        if request.args:
            for key, value in request.args.items():
                if self._contains_xss(value, xss_patterns):
                    return True
        
        # Check JSON data
        if request.is_json:
            try:
                data = request.get_json()
                if self._check_json_for_xss(data, xss_patterns):
                    return True
            except Exception:
                pass
        
        # Check form data
        if request.form:
            for key, value in request.form.items():
                if self._contains_xss(value, xss_patterns):
                    return True
        
        return False
    
    def _contains_xss(self, value, xss_patterns):
        """Check if value contains XSS patterns"""
        if not isinstance(value, str):
            return False
        
        value_lower = value.lower()
        
        for pattern in xss_patterns:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True
        
        return False
    
    def _check_json_for_xss(self, data, xss_patterns):
        """Recursively check JSON data for XSS"""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str):
                    if self._contains_xss(value, xss_patterns):
                        return True
                elif isinstance(value, (dict, list)):
                    if self._check_json_for_xss(value, xss_patterns):
                        return True
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    if self._contains_xss(item, xss_patterns):
                        return True
                elif isinstance(item, (dict, list)):
                    if self._check_json_for_xss(item, xss_patterns):
                        return True
        
        return False


def rate_limit(limit=100, window=60, per='ip'):
    """
    Decorator for rate limiting specific endpoints
    
    Args:
        limit: Number of requests allowed
        window: Time window in seconds
        per: Rate limit per ('ip', 'user', 'session')
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Get identifier based on 'per' parameter
            if per == 'ip':
                identifier = request.remote_addr or '127.0.0.1'
            elif per == 'user':
                from flask_jwt_extended import get_jwt_identity, jwt_required
                try:
                    identifier = f"user:{get_jwt_identity()}"
                except:
                    identifier = request.remote_addr or '127.0.0.1'
            else:
                identifier = request.remote_addr or '127.0.0.1'
            
            # Check rate limit
            redis_client = current_app.config.get('redis_client')
            if redis_client:
                key = f"rate_limit:{f.__name__}:{identifier}"
                current_count = redis_client.incr(key)
                
                if current_count == 1:
                    redis_client.expire(key, window)
                
                if current_count > limit:
                    return jsonify({
                        'error': True,
                        'message': f'Rate limit exceeded. Maximum {limit} requests per {window} seconds.',
                        'code': 'RATE_LIMIT_EXCEEDED'
                    }), 429
            
            return f(*args, **kwargs)
        return wrapper
    return decorator


def require_https():
    """Decorator to require HTTPS for sensitive endpoints"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not request.is_secure and not current_app.debug:
                return jsonify({
                    'error': True,
                    'message': 'HTTPS required for this endpoint',
                    'code': 'HTTPS_REQUIRED'
                }), 400
            return f(*args, **kwargs)
        return wrapper
    return decorator


def validate_content_type(content_type='application/json'):
    """Decorator to validate request content type"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if request.content_type != content_type:
                return jsonify({
                    'error': True,
                    'message': f'Content-Type must be {content_type}',
                    'code': 'INVALID_CONTENT_TYPE'
                }), 400
            return f(*args, **kwargs)
        return wrapper
    return decorator


def csrf_protect():
    """Basic CSRF protection decorator"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Skip CSRF for GET requests
            if request.method == 'GET':
                return f(*args, **kwargs)
            
            # Check for CSRF token in headers
            csrf_token = request.headers.get('X-CSRF-Token')
            if not csrf_token:
                return jsonify({
                    'error': True,
                    'message': 'CSRF token required',
                    'code': 'CSRF_TOKEN_MISSING'
                }), 400
            
            # Validate CSRF token (implement your validation logic)
            # This is a simplified version
            if not _validate_csrf_token(csrf_token):
                return jsonify({
                    'error': True,
                    'message': 'Invalid CSRF token',
                    'code': 'INVALID_CSRF_TOKEN'
                }), 400
            
            return f(*args, **kwargs)
        return wrapper
    return decorator


def _validate_csrf_token(token):
    """Validate CSRF token (implement based on your token generation logic)"""
    # This is a placeholder - implement actual validation
    return True


# Security utility functions
def generate_secure_token(length=32):
    """Generate cryptographically secure random token"""
    import secrets
    return secrets.token_urlsafe(length)


def hash_password(password):
    """Hash password using secure algorithm"""
    import bcrypt
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())


def verify_password(password, hashed):
    """Verify password against hash"""
    import bcrypt
    return bcrypt.checkpw(password.encode('utf-8'), hashed)


def secure_filename(filename):
    """Generate secure filename"""
    import re
    import os
    
    # Remove path components
    filename = os.path.basename(filename)
    
    # Remove or replace dangerous characters
    filename = re.sub(r'[^\w\s\-.]', '', filename)
    filename = re.sub(r'[\s\-]+', '-', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    return filename.lower()
