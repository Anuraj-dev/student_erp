# 🎓 ERP Student Management System

**Government of Rajasthan | Educational Management Platform**

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-orange.svg)](https://www.sqlalchemy.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A comprehensive Enterprise Resource Planning (ERP) system designed specifically for educational institutions under the Government of Rajasthan. This backend system provides robust APIs and services for managing all aspects of student lifecycle from admission to graduation.

## 🏛️ Government of Rajasthan Integration

This system is designed to comply with Government of Rajasthan standards and includes:

- 🏢 Official government branding and themes
- 📄 Government-compliant document generation
- 🔐 Security standards meeting government requirements
- 📊 Reporting formats as per educational department guidelines

## ✨ Features

### 🔐 Core System Features

- **Authentication & Authorization**: JWT-based secure login with role-based access control
- **Student Management**: Complete student lifecycle management from admission to graduation
- **Academic Management**: Course structure, subjects, departments, and academic calendar
- **Fee Management**: Automated fee calculation, payment processing, and receipt generation
- **Hostel Management**: Room allocation, occupancy tracking, and management
- **Library Management**: Book issue/return system with fine calculation
- **Examination System**: Exam scheduling, result management, and transcript generation

### 🤖 Automated Services

- **PDF Generation**: Professional government-themed documents with QR verification
- **Email Notifications**: Automated email system with HTML templates
- **Real-time Dashboard**: Live analytics and reporting with WebSocket integration
- **Security Middleware**: Input validation, SQL injection prevention, and audit logging

### 📄 Document Generation

- 🧾 **Fee Receipts**: Professional receipts with QR codes
- 📜 **Admission Letters**: Official admission documents
- 🆔 **Student ID Cards**: Photo ID cards with QR verification
- 📋 **Academic Transcripts**: Secure academic records

## 🏗️ Architecture

```
student_erp/
├── app/                          # Main application package
│   ├── models/                   # Database models (SQLAlchemy)
│   ├── routes/                   # API endpoints (Flask Blueprints)
│   ├── utils/                    # Utility services (PDF, Email, Security)
│   ├── templates/               # Email templates
│   └── static/                  # Static files and generated documents
├── tests/                       # Comprehensive test suite
├── logs/                        # Application logs
├── instance/                    # Database and instance files
└── migrations/                  # Database migrations
```

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- pip package manager
- SQLite (for development)
- Redis (for production - optional)

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/erp-student-management.git
   cd erp-student-management
   ```

2. **Create virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database**

   ```bash
   python run.py
   ```

6. **Access the application**
   ```
   http://localhost:5000
   ```

## 🧪 Testing

We provide comprehensive testing suite covering all backend functionality:

### Run All Tests

```bash
# Using test suite manager
python tests/test_suite.py --run-all

# Using shell script
./tests/run_tests.sh

# Using pytest
pytest
```

### Run Specific Tests

```bash
# Test specific component
python tests/test_models.py
python tests/test_auth.py
python tests/test_automated_services.py

# Main backend verification
python tests/test_comprehensive_backend.py

# Simple functionality test
python tests/simple_backend_test.py
```

### Test Coverage

- ✅ **100%** Backend task coverage (Tasks 1-10)
- ✅ **Authentication & Security** testing
- ✅ **Database Models** validation
- ✅ **API Endpoints** verification
- ✅ **PDF & Email Services** testing
- ✅ **Integration** testing

## 📊 API Documentation

### Authentication

```http
POST /api/auth/login
POST /api/auth/logout
POST /api/auth/refresh
```

### Student Management

```http
GET    /api/students
POST   /api/students
PUT    /api/students/<id>
DELETE /api/students/<id>
```

### Admission Management

```http
POST /api/admission/apply
GET  /api/admission/applications
PUT  /api/admission/process/<id>
```

### Fee Management

```http
POST /api/fee/generate-demand
POST /api/fee/pay
GET  /api/fee/receipt/<id>
```

### Dashboard & Analytics

```http
GET /api/dashboard/summary
GET /api/dashboard/charts/enrollment
GET /api/dashboard/real-time/stats
```

_For complete API documentation, see the [API Documentation](docs/api.md)_

## 🔧 Configuration

### Environment Variables

```bash
FLASK_ENV=development
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
SQLALCHEMY_DATABASE_URI=sqlite:///student_erp.db
MAIL_SERVER=smtp.gmail.com
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

### Database Configuration

The system uses SQLAlchemy ORM with support for:

- SQLite (development)
- PostgreSQL (recommended for production)
- MySQL (alternative for production)

## 🏃‍♂️ Development

### Project Structure

- **Models**: SQLAlchemy models in `app/models/`
- **Routes**: Flask blueprints in `app/routes/`
- **Services**: Utility services in `app/utils/`
- **Tests**: Comprehensive test suite in `tests/`

### Adding New Features

1. Create model in `app/models/`
2. Create routes in `app/routes/`
3. Add tests in `tests/`
4. Update documentation

### Code Style

- Follow PEP 8 guidelines
- Use type hints where applicable
- Maintain test coverage above 90%

## 🔐 Security

### Implemented Security Measures

- 🔑 JWT authentication with role-based access control
- 🛡️ Input validation and sanitization
- 🚫 SQL injection prevention
- 🔒 XSS protection
- 📝 Comprehensive audit logging
- 🔐 Password hashing (Werkzeug)
- 🌐 CORS configuration
- ⏱️ Rate limiting (Redis-based)

### Security Best Practices

- Regular security audits
- Dependency vulnerability scanning
- Secure coding practices
- Regular password policy enforcement

## 📈 Monitoring & Logging

### Logging Categories

- **System Logs**: Application startup and configuration
- **Security Logs**: Authentication attempts and security events
- **Admin Logs**: Administrative actions and changes
- **Performance Logs**: Response times and system performance
- **Error Logs**: Application errors and exceptions

### Log Files

```
logs/
├── student_erp.log          # Main application log
├── security.log             # Security-related events
├── admin_actions.log        # Administrative activities
├── errors.log               # Error tracking
└── performance.log          # Performance monitoring
```

## 🚀 Deployment

### Production Deployment

1. Set up production database (PostgreSQL recommended)
2. Configure environment variables
3. Set up reverse proxy (Nginx)
4. Use WSGI server (Gunicorn)
5. Set up SSL certificates
6. Configure monitoring and logging

### Docker Deployment

```bash
# Build image
docker build -t erp-student-management .

# Run container
docker run -d -p 5000:5000 erp-student-management
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Write tests for new features
- Follow existing code style
- Update documentation
- Ensure all tests pass

## 📞 Support

### Technical Support

- **Email**: support@rajasthan.gov.in
- **Documentation**: [Wiki Pages](wiki/)
- **Issues**: [GitHub Issues](issues/)

### Government Contact

- **Department**: Education Department, Government of Rajasthan
- **Portal**: [Rajasthan Education Portal](https://education.rajasthan.gov.in)

## 📋 Changelog

### Version 1.0.0 (Current)

- ✅ Complete backend implementation (Tasks 1-10)
- ✅ Authentication and authorization system
- ✅ Student management functionality
- ✅ Fee management with PDF receipts
- ✅ Automated email notifications
- ✅ Comprehensive testing suite
- ✅ Security implementations
- ✅ API documentation

### Upcoming Features

- [ ] Frontend React/Vue.js interface
- [ ] Mobile application
- [ ] Advanced reporting dashboard
- [ ] Integration with government databases

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🏛️ Government Compliance

This system is developed in compliance with:

- Government of Rajasthan IT policies
- Educational department guidelines
- Data protection regulations
- Security standards for government applications

---

**Developed with ❤️ for Government of Rajasthan Education Department**

_For technical queries, please contact the development team or raise an issue in this repository._
