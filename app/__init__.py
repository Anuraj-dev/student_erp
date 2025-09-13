from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_socketio import SocketIO
import redis
import os

# Initialize extensions
db = SQLAlchemy()
jwt = JWTManager()
mail = Mail()
socketio = SocketIO()

def create_app(config_name=None):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    from app.config import config
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    
    # Configure CORS with security considerations
    CORS(app, 
         origins=os.environ.get('ALLOWED_ORIGINS', '*').split(','),
         supports_credentials=True,
         allow_headers=['Content-Type', 'Authorization', 'X-CSRF-Token'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
    
    jwt.init_app(app)
    mail.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode='threading')
    
    # Initialize security middleware
    from app.utils.security_middleware import SecurityMiddleware
    security = SecurityMiddleware()
    security.init_app(app)
    
    # Setup logging
    from app.utils.logging_config import setup_logging, create_admin_logs, setup_performance_logging
    setup_logging(app)
    create_admin_logs()
    setup_performance_logging(app)
    
    # Initialize Redis for token blacklist and rate limiting
    try:
        redis_client = redis.Redis(
            host=app.config.get('REDIS_HOST', 'localhost'),
            port=app.config.get('REDIS_PORT', 6379),
            db=app.config.get('REDIS_DB', 0),
            decode_responses=True
        )
        # Test connection
        redis_client.ping()
        app.config['redis_client'] = redis_client
        app.logger.info("Redis connected successfully")
    except Exception as e:
        app.logger.warning(f"Redis connection failed: {e} - Token blacklisting and rate limiting disabled")
        app.config['redis_client'] = None
    
    # JWT token blacklist check
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        try:
            jti = jwt_payload['jti']
            if app.config.get('redis_client'):
                return app.config['redis_client'].get(f"blacklist:{jti}") is not None
            return False
        except Exception:
            return False
    
    # JWT error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {"message": "Token has expired", "error": "token_expired"}, 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {"message": "Invalid token", "error": "invalid_token"}, 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return {"message": "Authorization token required", "error": "authorization_required"}, 401
    
    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return {"message": "Token has been revoked", "error": "token_revoked"}, 401
    
    # Initialize API Documentation
    from app.documentation import doc_bp
    
    # Register API documentation blueprint
    app.register_blueprint(doc_bp, url_prefix='/api/v1')
    
    # Import and register documentation modules
    from app.documentation import auth_docs, student_docs, fee_docs, admission_docs, hostel_docs, library_docs, dashboard_docs
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.student import student_bp
    from app.routes.admission import admission_bp
    from app.routes.fee import fee_bp
    from app.routes.hostel import hostel_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.library import library
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(student_bp, url_prefix='/api/student')
    app.register_blueprint(admission_bp, url_prefix='/api/admission')
    app.register_blueprint(fee_bp, url_prefix='/api/fee')
    app.register_blueprint(hostel_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(library, url_prefix='/api/library')
    
    # Create tables
    with app.app_context():
        try:
            db.create_all()
            app.logger.info("Database tables created successfully")
        except Exception as e:
            app.logger.error(f"Database initialization failed: {e}")
    
    app.logger.info("ERP System initialized successfully")
    return app
