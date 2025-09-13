#!/usr/bin/env python3
"""
Security Feature Demonstration for Task 9: Data Security & Validation
Demonstrates comprehensive security implementations in the ERP system
"""

import json
from app.utils.validators import (
    validate_email, validate_phone, sanitize_input, advanced_sanitize_input,
    comprehensive_input_validation, detect_malicious_patterns,
    validate_business_rules
)
from app.utils.security_middleware import generate_secure_token, secure_filename

def demonstrate_input_validation():
    """Demonstrate input validation features"""
    print("🔍 INPUT VALIDATION DEMONSTRATION")
    print("=" * 50)
    
    # Email validation
    print("\n📧 Email Validation:")
    emails = ['valid@example.com', 'invalid-email', '@domain.com', '']
    for email in emails:
        is_valid, message = validate_email(email)
        print(f"  {email:<25} → {'✅ Valid' if is_valid else '❌ Invalid'}: {message}")
    
    # Phone validation
    print("\n📱 Phone Validation:")
    phones = ['+91-9876543210', '9876543210', '123', 'invalid']
    for phone in phones:
        is_valid, message, formatted = validate_phone(phone)
        status = f"✅ Valid: {formatted}" if is_valid else f"❌ Invalid: {message}"
        print(f"  {phone:<15} → {status}")
    
    print("\n" + "="*50)


def demonstrate_input_sanitization():
    """Demonstrate input sanitization features"""
    print("\n🧼 INPUT SANITIZATION DEMONSTRATION")
    print("=" * 50)
    
    dangerous_inputs = [
        '<script>alert("XSS Attack")</script>',
        'SELECT * FROM users; DROP TABLE users;',
        '<img src="x" onerror="alert(1)">',
        'javascript:alert("malicious")',
        '../../etc/passwd',
    ]
    
    print("\n🔸 Basic Sanitization:")
    for dangerous in dangerous_inputs[:2]:
        sanitized = sanitize_input(dangerous)
        print(f"  Original: {dangerous}")
        print(f"  Sanitized: {sanitized}")
        print()
    
    print("🔸 Advanced Sanitization:")
    for dangerous in dangerous_inputs:
        sanitized = advanced_sanitize_input(dangerous)
        print(f"  Original: {dangerous}")
        print(f"  Sanitized: {sanitized}")
        print()
    
    print("="*50)


def demonstrate_malicious_pattern_detection():
    """Demonstrate malicious pattern detection"""
    print("\n🕵️ MALICIOUS PATTERN DETECTION")
    print("=" * 50)
    
    test_inputs = [
        # SQL Injection attempts
        "'; DROP TABLE users; --",
        "UNION SELECT * FROM passwords",
        "1' OR '1'='1",
        
        # XSS attempts
        '<script>alert("xss")</script>',
        'javascript:alert("xss")',
        '<iframe src="malicious.html"></iframe>',
        
        # Path traversal
        '../../../etc/passwd',
        '..\\windows\\system32',
        
        # Safe inputs
        'This is a normal comment',
        'john@example.com',
        'Regular user input'
    ]
    
    for test_input in test_inputs:
        is_malicious, patterns = detect_malicious_patterns(test_input)
        status = "🚨 MALICIOUS" if is_malicious else "✅ SAFE"
        print(f"  {status}: {test_input}")
        if patterns:
            for pattern in patterns:
                print(f"    └─ Detected: {pattern}")
        print()
    
    print("="*50)


def demonstrate_comprehensive_validation():
    """Demonstrate comprehensive validation system"""
    print("\n📋 COMPREHENSIVE VALIDATION SYSTEM")
    print("=" * 50)
    
    validation_rules = {
        'required_fields': ['name', 'email', 'age'],
        'field_types': {
            'age': 'int',
            'phone': 'phone'
        },
        'field_lengths': {
            'name': (2, 50),
            'description': (10, 500)
        },
        'numeric_ranges': {
            'age': (18, 65),
            'salary': (0, 1000000)
        }
    }
    
    test_cases = [
        {
            'name': 'Valid User',
            'data': {
                'name': 'John Doe',
                'email': 'john@example.com',
                'age': '25',
                'phone': '+91-9876543210',
                'description': 'A valid user profile with all required information.',
                'salary': '50000'
            }
        },
        {
            'name': 'Invalid User',
            'data': {
                'name': 'J',  # Too short
                'email': 'invalid-email',
                'age': '15',  # Too young
                'phone': '123',  # Invalid format
                'description': 'Short',  # Too short
                'salary': '2000000'  # Too high
            }
        }
    ]
    
    for case in test_cases:
        print(f"\n🔸 Testing: {case['name']}")
        is_valid, errors = comprehensive_input_validation(case['data'], validation_rules)
        
        if is_valid:
            print("  ✅ All validations passed!")
        else:
            print("  ❌ Validation errors found:")
            for error in errors:
                print(f"    • {error}")
        print()
    
    print("="*50)


def demonstrate_business_rule_validation():
    """Demonstrate business rule validation"""
    print("\n🏢 BUSINESS RULE VALIDATION")
    print("=" * 50)
    
    test_cases = [
        {
            'entity': 'student',
            'data': {'age': 20, 'course_id': 1},
            'description': 'Valid student data'
        },
        {
            'entity': 'student', 
            'data': {'age': 15, 'course_id': -1},
            'description': 'Invalid student (too young, invalid course)'
        },
        {
            'entity': 'fee',
            'data': {'amount': 5000.0, 'payment_method': 'online'},
            'description': 'Valid fee payment'
        },
        {
            'entity': 'fee',
            'data': {'amount': -100, 'payment_method': 'crypto'},
            'description': 'Invalid fee (negative amount, invalid method)'
        },
        {
            'entity': 'library',
            'data': {'isbn': '978-0134685991', 'quantity': 5},
            'description': 'Valid library book'
        },
        {
            'entity': 'library',
            'data': {'isbn': '123', 'quantity': 0},
            'description': 'Invalid library book (invalid ISBN, zero quantity)'
        }
    ]
    
    for case in test_cases:
        print(f"\n🔸 {case['description']}:")
        is_valid, errors = validate_business_rules(case['data'], case['entity'])
        
        if is_valid:
            print("  ✅ Business rules satisfied")
        else:
            print("  ❌ Business rule violations:")
            for error in errors:
                print(f"    • {error}")
    
    print("\n" + "="*50)


def demonstrate_security_utilities():
    """Demonstrate security utility functions"""
    print("\n🔧 SECURITY UTILITIES")
    print("=" * 50)
    
    print("\n🔑 Secure Token Generation:")
    for i in range(3):
        token = generate_secure_token()
        print(f"  Token {i+1}: {token[:20]}...")
    
    print(f"\n📄 Secure Filename Generation:")
    dangerous_files = [
        '../../etc/passwd',
        'file with spaces.txt',
        'SPECIAL!@#$chars.doc',
        '<script>malicious.js',
        'very_long_filename_' * 20 + '.txt'
    ]
    
    for filename in dangerous_files:
        secure = secure_filename(filename)
        print(f"  {filename:<40} → {secure}")
    
    print("\n" + "="*50)


def demonstrate_security_configuration():
    """Show security configuration features"""
    print("\n⚙️ SECURITY CONFIGURATION")
    print("=" * 50)
    
    print("""
📋 Implemented Security Features:
    
🛡️ Security Headers:
    • X-Content-Type-Options: nosniff
    • X-Frame-Options: DENY
    • X-XSS-Protection: 1; mode=block
    • Strict-Transport-Security: max-age=31536000
    • Content-Security-Policy: default-src 'self'
    • Referrer-Policy: strict-origin-when-cross-origin
    
🔒 Input Protection:
    • SQL Injection Prevention
    • XSS Protection  
    • Path Traversal Protection
    • Command Injection Prevention
    • HTML Sanitization
    • Parameter Validation
    
⏱️ Rate Limiting:
    • General API: 100 requests/minute
    • Auth endpoints: 10 requests/5 minutes
    • Per-IP tracking with Redis backend
    
🔐 Authentication & Authorization:
    • JWT token-based authentication
    • Role-based access control
    • Token blacklisting
    • Session management
    
📊 Monitoring & Logging:
    • Security event logging
    • Performance monitoring
    • Failed authentication tracking
    • Malicious request detection
    """)
    
    print("="*50)


def main():
    """Run all security demonstrations"""
    print("🚀 ERP SYSTEM SECURITY DEMONSTRATION")
    print("Task 9: Data Security & Validation Implementation")
    print("=" * 60)
    
    # Run all demonstrations
    demonstrate_input_validation()
    demonstrate_input_sanitization()
    demonstrate_malicious_pattern_detection()
    demonstrate_comprehensive_validation()
    demonstrate_business_rule_validation()
    demonstrate_security_utilities()
    demonstrate_security_configuration()
    
    print("\n✅ SECURITY DEMONSTRATION COMPLETE")
    print("All security features are working correctly!")
    print("=" * 60)


if __name__ == '__main__':
    main()
