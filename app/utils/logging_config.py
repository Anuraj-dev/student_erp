import os
import logging
from logging.handlers import RotatingFileHandler, SMTPHandler
from datetime import datetime
import json

def setup_logging(app):
    """Setup comprehensive logging for the application"""
    
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    # Configure log format
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        'logs/student_erp.log', 
        maxBytes=10240000,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Error file handler
    error_file_handler = RotatingFileHandler(
        'logs/errors.log',
        maxBytes=10240000,
        backupCount=5
    )
    error_file_handler.setFormatter(formatter)
    error_file_handler.setLevel(logging.ERROR)
    
    # Security audit handler
    security_handler = RotatingFileHandler(
        'logs/security.log',
        maxBytes=10240000,
        backupCount=10
    )
    security_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] SECURITY: %(message)s'
    ))
    security_handler.setLevel(logging.WARNING)
    
    # Email handler for critical errors (if SMTP is configured)
    if app.config.get('MAIL_SERVER'):
        mail_handler = SMTPHandler(
            mailhost=(app.config['MAIL_SERVER'], app.config.get('MAIL_PORT', 587)),
            fromaddr=app.config.get('MAIL_DEFAULT_SENDER'),
            toaddrs=app.config.get('ADMIN_EMAIL', []),
            subject='ERP System Critical Error',
            credentials=(
                app.config.get('MAIL_USERNAME'),
                app.config.get('MAIL_PASSWORD')
            ),
            secure=() if app.config.get('MAIL_USE_TLS') else None
        )
        mail_handler.setLevel(logging.CRITICAL)
        mail_handler.setFormatter(logging.Formatter(
            'Time: %(asctime)s\n'
            'Level: %(levelname)s\n'
            'Module: %(module)s\n'
            'Message: %(message)s\n'
        ))
        app.logger.addHandler(mail_handler)
    
    # Add handlers to app logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_file_handler)
    
    # Create security logger
    security_logger = logging.getLogger('security')
    security_logger.addHandler(security_handler)
    security_logger.setLevel(logging.WARNING)
    
    # Set log level based on environment
    if app.config.get('DEBUG'):
        app.logger.setLevel(logging.DEBUG)
    else:
        app.logger.setLevel(logging.INFO)
    
    app.logger.info('ERP System logging initialized')

def log_security_event(event_type, user_id=None, ip_address=None, user_agent=None, details=None):
    """Log security-related events"""
    security_logger = logging.getLogger('security')
    
    event_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'event_type': event_type,
        'user_id': user_id,
        'ip_address': ip_address,
        'user_agent': user_agent,
        'details': details or {}
    }
    
    security_logger.warning(json.dumps(event_data))

def log_user_activity(user_id, user_type, action, resource=None, details=None, ip_address=None):
    """Log user activities for audit trail"""
    activity_logger = logging.getLogger('activity')
    
    # Setup activity logger if not exists
    if not activity_logger.handlers:
        activity_handler = RotatingFileHandler(
            'logs/user_activity.log',
            maxBytes=10240000,
            backupCount=20
        )
        activity_handler.setFormatter(logging.Formatter(
            '[%(asctime)s] ACTIVITY: %(message)s'
        ))
        activity_logger.addHandler(activity_handler)
        activity_logger.setLevel(logging.INFO)
    
    activity_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'user_type': user_type,
        'action': action,
        'resource': resource,
        'ip_address': ip_address,
        'details': details or {}
    }
    
    activity_logger.info(json.dumps(activity_data))

class AuditLog:
    """Audit logging utility class"""
    
    @staticmethod
    def log_login_attempt(user_id, user_type, success=True, ip_address=None, user_agent=None):
        """Log login attempts"""
        event_type = 'LOGIN_SUCCESS' if success else 'LOGIN_FAILED'
        log_security_event(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={'user_type': user_type}
        )
        
        log_user_activity(
            user_id=user_id,
            user_type=user_type,
            action='login',
            details={'success': success},
            ip_address=ip_address
        )
    
    @staticmethod
    def log_logout(user_id, user_type, ip_address=None):
        """Log logout events"""
        log_user_activity(
            user_id=user_id,
            user_type=user_type,
            action='logout',
            ip_address=ip_address
        )
    
    @staticmethod
    def log_password_change(user_id, user_type, ip_address=None):
        """Log password change events"""
        log_security_event(
            event_type='PASSWORD_CHANGE',
            user_id=user_id,
            ip_address=ip_address,
            details={'user_type': user_type}
        )
        
        log_user_activity(
            user_id=user_id,
            user_type=user_type,
            action='password_change',
            ip_address=ip_address
        )
    
    @staticmethod
    def log_profile_update(user_id, user_type, fields_changed, ip_address=None):
        """Log profile update events"""
        log_user_activity(
            user_id=user_id,
            user_type=user_type,
            action='profile_update',
            details={'fields_changed': fields_changed},
            ip_address=ip_address
        )
    
    @staticmethod
    def log_permission_denied(user_id, user_type, resource, action, ip_address=None):
        """Log unauthorized access attempts"""
        log_security_event(
            event_type='PERMISSION_DENIED',
            user_id=user_id,
            ip_address=ip_address,
            details={
                'user_type': user_type,
                'resource': resource,
                'action': action
            }
        )
    
    @staticmethod
    def log_data_access(user_id, user_type, resource, action, record_id=None, ip_address=None):
        """Log data access events"""
        log_user_activity(
            user_id=user_id,
            user_type=user_type,
            action=action,
            resource=resource,
            details={'record_id': record_id} if record_id else None,
            ip_address=ip_address
        )
    
    @staticmethod
    def log_critical_action(user_id, user_type, action, details=None, ip_address=None):
        """Log critical system actions"""
        log_security_event(
            event_type='CRITICAL_ACTION',
            user_id=user_id,
            ip_address=ip_address,
            details={
                'user_type': user_type,
                'action': action,
                'details': details or {}
            }
        )
        
        log_user_activity(
            user_id=user_id,
            user_type=user_type,
            action=action,
            details=details,
            ip_address=ip_address
        )

def create_admin_logs():
    """Create admin-specific log files"""
    admin_logs = ['admin_actions.log', 'system_changes.log', 'bulk_operations.log']
    
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    for log_file in admin_logs:
        log_path = os.path.join('logs', log_file)
        if not os.path.exists(log_path):
            with open(log_path, 'w') as f:
                f.write(f"# {log_file} initialized at {datetime.utcnow().isoformat()}\n")

def setup_performance_logging(app):
    """Setup performance monitoring logs"""
    performance_handler = RotatingFileHandler(
        'logs/performance.log',
        maxBytes=10240000,
        backupCount=5
    )
    performance_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] PERFORMANCE: %(message)s'
    ))
    
    performance_logger = logging.getLogger('performance')
    performance_logger.addHandler(performance_handler)
    performance_logger.setLevel(logging.INFO)

# Performance monitoring decorator
import time
import functools

def log_performance(func):
    """Decorator to log function performance"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Log slow operations (>1 second)
        if execution_time > 1.0:
            performance_logger = logging.getLogger('performance')
            performance_logger.warning(json.dumps({
                'function': func.__name__,
                'module': func.__module__,
                'execution_time': execution_time,
                'timestamp': datetime.utcnow().isoformat()
            }))
        
        return result
    return wrapper

# Error tracking utilities
def track_error(error_type, error_message, user_id=None, additional_data=None):
    """Track application errors"""
    error_logger = logging.getLogger('errors')
    
    # Setup error logger if not exists
    if not error_logger.handlers:
        error_handler = RotatingFileHandler(
            'logs/application_errors.log',
            maxBytes=10240000,
            backupCount=5
        )
        error_handler.setFormatter(logging.Formatter(
            '[%(asctime)s] ERROR: %(message)s'
        ))
        error_logger.addHandler(error_handler)
        error_logger.setLevel(logging.ERROR)
    
    error_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'error_type': error_type,
        'error_message': str(error_message),
        'user_id': user_id,
        'additional_data': additional_data or {}
    }
    
    error_logger.error(json.dumps(error_data))

# Database query logging
def log_database_query(query, execution_time, user_id=None, result_count=None):
    """Log database queries for monitoring"""
    db_logger = logging.getLogger('database')
    
    if not db_logger.handlers:
        db_handler = RotatingFileHandler(
            'logs/database_queries.log',
            maxBytes=10240000,
            backupCount=10
        )
        db_handler.setFormatter(logging.Formatter(
            '[%(asctime)s] DB_QUERY: %(message)s'
        ))
        db_logger.addHandler(db_handler)
        db_logger.setLevel(logging.INFO)
    
    query_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'query': str(query),
        'execution_time': execution_time,
        'user_id': user_id,
        'result_count': result_count
    }
    
    # Log slow queries (>0.5 seconds)
    if execution_time > 0.5:
        db_logger.warning(json.dumps(query_data))
    else:
        db_logger.info(json.dumps(query_data))

def log_admin_action(admin_id, action, resource=None, resource_id=None, details=None, ip_address=None):
    """Log admin actions for compliance and audit purposes"""
    admin_logger = logging.getLogger('admin_actions')
    
    # Setup admin action logger if not exists
    if not admin_logger.handlers:
        admin_handler = RotatingFileHandler(
            'logs/admin_actions.log',
            maxBytes=10240000,
            backupCount=20
        )
        admin_handler.setFormatter(logging.Formatter(
            '[%(asctime)s] ADMIN_ACTION: %(message)s'
        ))
        admin_logger.addHandler(admin_handler)
        admin_logger.setLevel(logging.INFO)
    
    action_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'admin_id': admin_id,
        'action': action,
        'resource': resource,
        'resource_id': resource_id,
        'ip_address': ip_address,
        'details': details or {}
    }
    
    admin_logger.info(json.dumps(action_data))
    
    # Also log to security logger for critical admin actions
    critical_actions = ['delete_user', 'bulk_delete', 'system_config_change', 'data_export', 'privilege_change']
    if action in critical_actions:
        log_security_event(
            event_type='ADMIN_CRITICAL_ACTION',
            user_id=admin_id,
            ip_address=ip_address,
            details=action_data
        )
