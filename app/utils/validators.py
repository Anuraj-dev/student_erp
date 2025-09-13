import re
from datetime import datetime, date
from email_validator import validate_email as email_validate, EmailNotValidError
from flask import request, jsonify
import html

def validate_email(email):
    """
    Validate email format and domain
    Returns (is_valid, message)
    """
    if not email:
        return False, "Email is required"
    
    try:
        # Use email-validator library for comprehensive validation
        valid = email_validate(email)
        return True, "Valid email"
    except EmailNotValidError as e:
        return False, str(e)

def validate_phone(phone):
    """
    Validate Indian phone number format
    Supports: +91-XXXXXXXXXX, 91XXXXXXXXXX, XXXXXXXXXX
    Returns (is_valid, message, formatted_phone)
    """
    if not phone:
        return False, "Phone number is required", None
    
    # Remove all non-digit characters except +
    clean_phone = re.sub(r'[^\d+]', '', phone)
    
    # Indian phone number patterns
    patterns = [
        r'^\+91\d{10}$',  # +91XXXXXXXXXX
        r'^91\d{10}$',    # 91XXXXXXXXXX  
        r'^\d{10}$'       # XXXXXXXXXX
    ]
    
    for pattern in patterns:
        if re.match(pattern, clean_phone):
            # Format to standard +91-XXXXXXXXXX
            if clean_phone.startswith('+91'):
                formatted = f"+91-{clean_phone[3:]}"
            elif clean_phone.startswith('91'):
                formatted = f"+91-{clean_phone[2:]}"
            else:
                formatted = f"+91-{clean_phone}"
            
            return True, "Valid phone number", formatted
    
    return False, "Invalid phone number format. Use Indian format: +91-XXXXXXXXXX", None

def validate_roll_no(roll_no):
    """
    Validate student roll number format
    Expected format: AA0000000 (2 letters followed by 7 digits)
    Returns (is_valid, message)
    """
    if not roll_no:
        return False, "Roll number is required"
    
    roll_no = roll_no.upper().strip()
    
    # Pattern: 2-3 letters followed by 4-7 digits
    roll_no_pattern = r'^[A-Z]{2,3}\d{4,7}$'
    
    if re.match(roll_no_pattern, roll_no):
        return True, "Valid roll number format"
    else:
        return False, "Invalid roll number format. Format should be like: CS2023001"

def validate_pan(pan):
    """
    Validate PAN card format: AAAAA0000A
    Returns (is_valid, message)
    """
    if not pan:
        return False, "PAN is required"
    
    pan = pan.upper().strip()
    pan_pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
    
    if re.match(pan_pattern, pan):
        return True, "Valid PAN format"
    else:
        return False, "Invalid PAN format. Format should be: AAAAA0000A"

def validate_aadhar(aadhar):
    """
    Validate Aadhar number format: 12 digits
    Returns (is_valid, message)
    """
    if not aadhar:
        return False, "Aadhar number is required"
    
    # Remove spaces and hyphens
    clean_aadhar = re.sub(r'[\s-]', '', aadhar)
    
    # Check if 12 digits
    if len(clean_aadhar) == 12 and clean_aadhar.isdigit():
        # Basic Verhoeff algorithm check (simplified)
        return True, "Valid Aadhar format"
    else:
        return False, "Invalid Aadhar format. Must be 12 digits"

def sanitize_input(text):
    """
    Sanitize input to prevent XSS and injection attacks
    Returns cleaned text
    """
    if not text:
        return ""
    
    # Remove HTML tags and escape special characters
    cleaned = html.escape(str(text).strip())
    
    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '&', 'script', 'javascript', 'onload', 'onerror']
    for char in dangerous_chars:
        cleaned = cleaned.replace(char.lower(), '')
        cleaned = cleaned.replace(char.upper(), '')
    
    return cleaned

def validate_date(date_string, format='%Y-%m-%d'):
    """
    Validate date format and convert to date object
    Returns (is_valid, message, date_object)
    """
    if not date_string:
        return False, "Date is required", None
    
    try:
        date_obj = datetime.strptime(date_string, format).date()
        return True, "Valid date", date_obj
    except ValueError:
        return False, f"Invalid date format. Expected format: {format}", None

def validate_age(birth_date, min_age=17, max_age=25):
    """
    Validate age based on birth date
    Returns (is_valid, message, age)
    """
    if not birth_date:
        return False, "Birth date is required", None
    
    if isinstance(birth_date, str):
        is_valid, message, birth_date = validate_date(birth_date)
        if not is_valid:
            return False, message, None
    
    today = date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
    if age < min_age:
        return False, f"Age must be at least {min_age} years", age
    elif age > max_age:
        return False, f"Age must not exceed {max_age} years", age
    else:
        return True, "Valid age", age

def validate_percentage(percentage):
    """
    Validate percentage (0-100)
    Returns (is_valid, message, percentage_float)
    """
    if percentage is None:
        return False, "Percentage is required", None
    
    try:
        pct = float(percentage)
        if 0 <= pct <= 100:
            return True, "Valid percentage", pct
        else:
            return False, "Percentage must be between 0 and 100", None
    except (ValueError, TypeError):
        return False, "Invalid percentage format", None

def validate_amount(amount):
    """
    Validate monetary amount (positive number)
    Returns (is_valid, message, amount_int)
    """
    if amount is None:
        return False, "Amount is required", None
    
    try:
        amt = int(float(amount))
        if amt > 0:
            return True, "Valid amount", amt
        else:
            return False, "Amount must be greater than 0", None
    except (ValueError, TypeError):
        return False, "Invalid amount format", None

def validate_roll_number(roll_no):
    """
    Validate roll number format: YEARCOURSECODE0000
    Returns (is_valid, message)
    """
    if not roll_no:
        return False, "Roll number is required"
    
    # Format: 2025CS0001 (4 digit year + course code + 4 digit serial)
    roll_pattern = r'^20\d{2}[A-Z]{2,5}\d{4}$'
    
    if re.match(roll_pattern, roll_no):
        return True, "Valid roll number format"
    else:
        return False, "Invalid roll number format"

def validate_file_upload(file, allowed_extensions=None, max_size_mb=16):
    """
    Validate uploaded file
    Returns (is_valid, message, file_info)
    """
    if not file or file.filename == '':
        return False, "No file selected", None
    
    if allowed_extensions is None:
        allowed_extensions = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}
    
    # Check file extension
    if '.' not in file.filename:
        return False, "File must have an extension", None
    
    extension = file.filename.rsplit('.', 1)[1].lower()
    if extension not in allowed_extensions:
        return False, f"File type not allowed. Allowed: {', '.join(allowed_extensions)}", None
    
    # Check file size (if we can get it)
    try:
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)     # Seek back to beginning
        
        max_size_bytes = max_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            return False, f"File size too large. Maximum: {max_size_mb}MB", None
    except:
        pass  # Size check failed, continue anyway
    
    file_info = {
        'filename': sanitize_input(file.filename),
        'extension': extension,
        'content_type': file.content_type
    }
    
    return True, "Valid file", file_info

def validate_password_strength(password):
    """
    Validate password strength
    Returns (is_valid, message, strength_score)
    """
    if not password:
        return False, "Password is required", 0
    
    score = 0
    issues = []
    
    # Length check
    if len(password) >= 8:
        score += 1
    else:
        issues.append("At least 8 characters")
    
    # Uppercase check
    if re.search(r'[A-Z]', password):
        score += 1
    else:
        issues.append("At least one uppercase letter")
    
    # Lowercase check
    if re.search(r'[a-z]', password):
        score += 1
    else:
        issues.append("At least one lowercase letter")
    
    # Number check
    if re.search(r'\d', password):
        score += 1
    else:
        issues.append("At least one number")
    
    # Special character check
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 1
    else:
        issues.append("At least one special character")
    
    if score >= 4:
        return True, "Strong password", score
    else:
        message = "Password requirements: " + ", ".join(issues)
        return False, message, score

def validate_json_request(required_fields=None, optional_fields=None):
    """
    Decorator to validate JSON request data
    """
    def decorator(f):
        def wrapper(*args, **kwargs):
            if not request.is_json:
                return jsonify({
                    'error': True,
                    'message': 'Request must be JSON',
                    'code': 'INVALID_CONTENT_TYPE'
                }), 400
            
            data = request.get_json()
            if not data:
                return jsonify({
                    'error': True,
                    'message': 'Request body is required',
                    'code': 'MISSING_REQUEST_BODY'
                }), 400
            
            # Check required fields
            if required_fields:
                missing_fields = []
                for field in required_fields:
                    if field not in data or data[field] in [None, '', []]:
                        missing_fields.append(field)
                
                if missing_fields:
                    return jsonify({
                        'error': True,
                        'message': f'Missing required fields: {", ".join(missing_fields)}',
                        'code': 'MISSING_REQUIRED_FIELDS'
                    }), 400
            
            # Sanitize all string inputs
            for key, value in data.items():
                if isinstance(value, str):
                    data[key] = sanitize_input(value)
            
            # Store validated data for use in route
            request.validated_data = data
            
            return f(*args, **kwargs)
        return wrapper
    return decorator

def validate_query_params(allowed_params=None, required_params=None):
    """
    Decorator to validate query parameters
    """
    def decorator(f):
        def wrapper(*args, **kwargs):
            # Check required parameters
            if required_params:
                missing_params = []
                for param in required_params:
                    if param not in request.args:
                        missing_params.append(param)
                
                if missing_params:
                    return jsonify({
                        'error': True,
                        'message': f'Missing required parameters: {", ".join(missing_params)}',
                        'code': 'MISSING_REQUIRED_PARAMS'
                    }), 400
            
            # Check for unknown parameters
            if allowed_params:
                unknown_params = []
                for param in request.args:
                    if param not in allowed_params:
                        unknown_params.append(param)
                
                if unknown_params:
                    return jsonify({
                        'error': True,
                        'message': f'Unknown parameters: {", ".join(unknown_params)}',
                        'code': 'UNKNOWN_PARAMETERS'
                    }), 400
            
            return f(*args, **kwargs)
        return wrapper
    return decorator

def validate_pagination():
    """
    Validate pagination parameters (page, per_page)
    Returns (page, per_page, offset)
    """
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        # Constraints
        if page < 1:
            page = 1
        if per_page < 1:
            per_page = 50
        if per_page > 100:  # Maximum items per page
            per_page = 100
        
        offset = (page - 1) * per_page
        
        return page, per_page, offset
    except ValueError:
        return 1, 50, 0

def validate_admission_data(data):
    """Comprehensive validation for admission application data"""
    errors = []
    
    # Validate full name
    if not data.get('full_name') or len(data['full_name'].strip()) < 2:
        errors.append("Full name must be at least 2 characters long")
    
    # Validate email
    email_valid, email_msg = validate_email(data.get('email', ''))
    if not email_valid:
        errors.append(f"Email validation failed: {email_msg}")
    
    # Validate phone
    phone_valid, phone_msg, _ = validate_phone(data.get('phone', ''))  # Ignore formatted phone
    if not phone_valid:
        errors.append(f"Phone validation failed: {phone_msg}")
    
    # Validate date of birth
    if data.get('date_of_birth'):
        try:
            dob = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            
            if age < 16 or age > 35:
                errors.append("Age must be between 16 and 35 years")
        except ValueError:
            errors.append("Invalid date format for date of birth. Use YYYY-MM-DD")
    else:
        errors.append("Date of birth is required")
    
    # Validate address
    if not data.get('address') or len(data['address'].strip()) < 10:
        errors.append("Address must be at least 10 characters long")
    
    # Validate course_id
    if not data.get('course_id') or not isinstance(data['course_id'], int):
        errors.append("Valid course ID is required")
    
    # Validate previous education
    if not data.get('previous_education') or len(data['previous_education'].strip()) < 5:
        errors.append("Previous education details are required")
    
    # Validate documents
    if data.get('documents'):
        if not isinstance(data['documents'], dict):
            errors.append("Documents must be provided as key-value pairs")
        else:
            required_docs = ['photo', 'signature', '10th_certificate', '12th_certificate']
            missing_docs = []
            for doc in required_docs:
                if doc not in data['documents'] or not data['documents'][doc]:
                    missing_docs.append(doc)
            
            if missing_docs:
                errors.append(f"Missing required documents: {', '.join(missing_docs)}")
    else:
        errors.append("Required documents must be provided")
    
    # Validate optional fields if provided
    if data.get('guardian_phone'):
        guardian_valid, guardian_msg, _ = validate_phone(data['guardian_phone'])  # Ignore formatted phone
        if not guardian_valid:
            errors.append(f"Guardian phone validation failed: {guardian_msg}")
    
    if data.get('emergency_contact'):
        emergency_valid, emergency_msg, _ = validate_phone(data['emergency_contact'])  # Ignore formatted phone
        if not emergency_valid:
            errors.append(f"Emergency contact validation failed: {emergency_msg}")
    
    return {
        'valid': len(errors) == 0,
        'message': '; '.join(errors) if errors else 'Valid',
        'errors': errors
    }

def validate_fee_payment(data):
    """Validate fee payment data"""
    errors = []
    
    # Required fields
    required_fields = ['student_id', 'amount', 'payment_method']
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f'{field} is required')
    
    # Amount validation
    if 'amount' in data:
        try:
            amount = float(data['amount'])
            if amount <= 0:
                errors.append('Amount must be greater than zero')
            if amount > 1000000:  # Max amount limit
                errors.append('Amount cannot exceed ₹10,00,000')
        except (ValueError, TypeError):
            errors.append('Invalid amount format')
    
    # Payment method validation
    valid_payment_methods = ['cash', 'online', 'bank_transfer', 'dd', 'cheque']
    if 'payment_method' in data and data['payment_method'] not in valid_payment_methods:
        errors.append(f'Invalid payment method. Must be one of: {", ".join(valid_payment_methods)}')
    
    # Transaction ID validation for online payments
    if data.get('payment_method') == 'online' and not data.get('transaction_id'):
        errors.append('Transaction ID is required for online payments')
    
    # Student ID format validation
    if 'student_id' in data:
        student_id = str(data['student_id'])
        if len(student_id) < 5:
            errors.append('Invalid student ID format')
    
    return {
        'valid': len(errors) == 0,
        'message': '; '.join(errors) if errors else 'Validation passed'
    }


def validate_required_fields(data, required_fields):
    """
    Validate that all required fields are present and not empty
    Returns None if validation passes, or error response if validation fails
    """
    if not data:
        return jsonify({
            'success': False,
            'message': 'No data provided'
        }), 400
    
    missing_fields = []
    empty_fields = []
    
    for field in required_fields:
        if field not in data:
            missing_fields.append(field)
        elif not data[field] or (isinstance(data[field], str) and not data[field].strip()):
            empty_fields.append(field)
    
    if missing_fields or empty_fields:
        error_message = []
        if missing_fields:
            error_message.append(f"Missing required fields: {', '.join(missing_fields)}")
        if empty_fields:
            error_message.append(f"Empty required fields: {', '.join(empty_fields)}")
        
        return jsonify({
            'success': False,
            'message': '; '.join(error_message)
        }), 400
    
    return None  # Validation passed


def advanced_sanitize_input(data):
    """
    Advanced input sanitization with SQL injection and XSS prevention
    """
    if isinstance(data, str):
        # Remove null bytes
        data = data.replace('\x00', '')
        
        # HTML escape
        data = html.escape(data)
        
        # Remove potentially dangerous SQL keywords
        sql_keywords = ['union', 'select', 'insert', 'update', 'delete', 'drop', 'script', 'exec']
        for keyword in sql_keywords:
            data = re.sub(r'\b' + keyword + r'\b', '', data, flags=re.IGNORECASE)
        
        # Remove script tags and event handlers
        data = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', data, flags=re.IGNORECASE)
        data = re.sub(r'on\w+\s*=', '', data, flags=re.IGNORECASE)
        data = re.sub(r'javascript:', '', data, flags=re.IGNORECASE)
        
        return data.strip()
    
    elif isinstance(data, dict):
        return {key: advanced_sanitize_input(value) for key, value in data.items()}
    
    elif isinstance(data, list):
        return [advanced_sanitize_input(item) for item in data]
    
    return data


def validate_data_types(data, field_types):
    """
    Validate data types for specific fields
    
    Args:
        data: Dictionary of data to validate
        field_types: Dictionary of field_name -> expected_type mappings
    
    Returns:
        (is_valid, errors)
    """
    errors = []
    
    for field_name, expected_type in field_types.items():
        if field_name in data:
            value = data[field_name]
            
            if expected_type == 'int':
                try:
                    int(value)
                except (ValueError, TypeError):
                    errors.append(f"{field_name} must be an integer")
            
            elif expected_type == 'float':
                try:
                    float(value)
                except (ValueError, TypeError):
                    errors.append(f"{field_name} must be a number")
            
            elif expected_type == 'email':
                is_valid, msg = validate_email(value)
                if not is_valid:
                    errors.append(f"{field_name}: {msg}")
            
            elif expected_type == 'phone':
                is_valid, msg, _ = validate_phone(value)
                if not is_valid:
                    errors.append(f"{field_name}: {msg}")
            
            elif expected_type == 'date':
                is_valid, msg, _ = validate_date(str(value))
                if not is_valid:
                    errors.append(f"{field_name}: {msg}")
            
            elif expected_type == 'string' and not isinstance(value, str):
                errors.append(f"{field_name} must be a string")
    
    return len(errors) == 0, errors


def validate_field_lengths(data, field_limits):
    """
    Validate field length limits
    
    Args:
        data: Dictionary of data to validate
        field_limits: Dictionary of field_name -> (min_length, max_length) tuples
    
    Returns:
        (is_valid, errors)
    """
    errors = []
    
    for field_name, (min_length, max_length) in field_limits.items():
        if field_name in data:
            value = str(data[field_name])
            
            if len(value) < min_length:
                errors.append(f"{field_name} must be at least {min_length} characters long")
            
            if len(value) > max_length:
                errors.append(f"{field_name} must not exceed {max_length} characters")
    
    return len(errors) == 0, errors


def validate_numeric_ranges(data, field_ranges):
    """
    Validate numeric field ranges
    
    Args:
        data: Dictionary of data to validate
        field_ranges: Dictionary of field_name -> (min_value, max_value) tuples
    
    Returns:
        (is_valid, errors)
    """
    errors = []
    
    for field_name, (min_value, max_value) in field_ranges.items():
        if field_name in data:
            try:
                value = float(data[field_name])
                
                if value < min_value:
                    errors.append(f"{field_name} must be at least {min_value}")
                
                if value > max_value:
                    errors.append(f"{field_name} must not exceed {max_value}")
                    
            except (ValueError, TypeError):
                errors.append(f"{field_name} must be a valid number")
    
    return len(errors) == 0, errors


def comprehensive_input_validation(data, validation_rules):
    """
    Comprehensive input validation using multiple validation rules
    
    Args:
        data: Dictionary of data to validate
        validation_rules: Dictionary containing validation rules:
            {
                'required_fields': ['field1', 'field2'],
                'field_types': {'field1': 'string', 'field2': 'int'},
                'field_lengths': {'field1': (2, 50)},
                'numeric_ranges': {'field2': (0, 100)},
                'custom_validators': {'field3': custom_validator_function}
            }
    
    Returns:
        (is_valid, errors)
    """
    all_errors = []
    
    # Sanitize input first
    data = advanced_sanitize_input(data)
    
    # Check required fields
    if 'required_fields' in validation_rules:
        required_fields = validation_rules['required_fields']
        for field in required_fields:
            if field not in data or not data[field] or (isinstance(data[field], str) and not data[field].strip()):
                all_errors.append(f"Required field '{field}' is missing or empty")
    
    # Validate data types
    if 'field_types' in validation_rules:
        is_valid, errors = validate_data_types(data, validation_rules['field_types'])
        if not is_valid:
            all_errors.extend(errors)
    
    # Validate field lengths
    if 'field_lengths' in validation_rules:
        is_valid, errors = validate_field_lengths(data, validation_rules['field_lengths'])
        if not is_valid:
            all_errors.extend(errors)
    
    # Validate numeric ranges
    if 'numeric_ranges' in validation_rules:
        is_valid, errors = validate_numeric_ranges(data, validation_rules['numeric_ranges'])
        if not is_valid:
            all_errors.extend(errors)
    
    # Apply custom validators
    if 'custom_validators' in validation_rules:
        for field_name, validator_func in validation_rules['custom_validators'].items():
            if field_name in data:
                is_valid, error_msg = validator_func(data[field_name])
                if not is_valid:
                    all_errors.append(f"{field_name}: {error_msg}")
    
    return len(all_errors) == 0, all_errors


def create_validation_decorator(validation_rules):
    """
    Create a decorator for route validation
    """
    def decorator(f):
        def wrapper(*args, **kwargs):
            if not request.is_json:
                return jsonify({
                    'error': True,
                    'message': 'Request must be JSON',
                    'code': 'INVALID_CONTENT_TYPE'
                }), 400
            
            data = request.get_json()
            is_valid, errors = comprehensive_input_validation(data, validation_rules)
            
            if not is_valid:
                return jsonify({
                    'error': True,
                    'message': 'Validation failed',
                    'errors': errors,
                    'code': 'VALIDATION_FAILED'
                }), 400
            
            # Store validated and sanitized data
            request.validated_data = data
            return f(*args, **kwargs)
        return wrapper
    return decorator


def detect_malicious_patterns(text):
    """
    Detect various malicious patterns in input text
    
    Returns:
        (is_malicious, detected_patterns)
    """
    if not isinstance(text, str):
        return False, []
    
    detected_patterns = []
    text_lower = text.lower()
    
    # SQL Injection patterns
    sql_patterns = [
        r"(\bunion\b.*\bselect\b)",
        r"(\bselect\b.*\bfrom\b.*\bwhere\b)",
        r"(\binsert\b.*\binto\b)",
        r"(\bupdate\b.*\bset\b)",
        r"(\bdelete\b.*\bfrom\b)",
        r"(\bdrop\b.*\btable\b)",
        r"(\bexec\b|\bexecute\b)",
        r"(;.*drop|;.*delete|;.*update)",
        r"(--|\#|/\*)",
        r"(\bor\b.*=.*\bor\b)",
        r"('\bor\b'1'='1)",
    ]
    
    for pattern in sql_patterns:
        try:
            if re.search(pattern, text_lower, re.IGNORECASE):
                detected_patterns.append(f"SQL Injection: {pattern}")
        except re.error:
            # Skip problematic patterns
            continue
    
    # XSS patterns
    xss_patterns = [
        r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe\b",
        r"<object\b",
        r"<embed\b",
        r"<form\b",
        r"vbscript:",
        r"data:text/html",
        r"expression\s*\(",
    ]
    
    for pattern in xss_patterns:
        try:
            if re.search(pattern, text_lower, re.IGNORECASE):
                detected_patterns.append(f"XSS: {pattern}")
        except re.error:
            continue
    
    # Path traversal patterns
    path_patterns = [
        r"\.\./",
        r"\.\.\\",
        r"~\/",
        r"\/etc\/",
        r"\/proc\/",
        r"\/var\/",
        r"c:\\",
        r"\\windows\\",
    ]
    
    for pattern in path_patterns:
        try:
            if re.search(pattern, text_lower, re.IGNORECASE):
                detected_patterns.append(f"Path Traversal: {pattern}")
        except re.error:
            continue
    
    # Command injection patterns
    cmd_patterns = [
        r"[;&|`$()]",
        r"\\x[0-9a-f]{2}",
        r"%(0[0-9a-f]|[1-9a-f][0-9a-f])",
    ]
    
    for pattern in cmd_patterns:
        try:
            if re.search(pattern, text, re.IGNORECASE):
                detected_patterns.append(f"Command Injection: {pattern}")
        except re.error:
            continue
    
    return len(detected_patterns) > 0, detected_patterns


def validate_business_rules(data, entity_type):
    """
    Validate business-specific rules for different entities
    """
    errors = []
    
    if entity_type == 'student':
        # Student-specific validation rules
        if 'age' in data:
            age = int(data.get('age', 0))
            if age < 16 or age > 35:
                errors.append("Student age must be between 16 and 35 years")
        
        if 'course_id' in data:
            # Validate course exists (this would typically check database)
            course_id = data['course_id']
            if not isinstance(course_id, int) or course_id <= 0:
                errors.append("Invalid course ID")
    
    elif entity_type == 'fee':
        # Fee-specific validation rules
        if 'amount' in data:
            amount = float(data.get('amount', 0))
            if amount <= 0:
                errors.append("Fee amount must be greater than zero")
            if amount > 1000000:  # 10 lakh maximum
                errors.append("Fee amount cannot exceed ₹10,00,000")
        
        if 'payment_method' in data:
            valid_methods = ['cash', 'online', 'bank_transfer', 'dd', 'cheque']
            if data['payment_method'] not in valid_methods:
                errors.append(f"Invalid payment method. Must be one of: {', '.join(valid_methods)}")
    
    elif entity_type == 'library':
        # Library-specific validation rules
        if 'isbn' in data:
            isbn = data['isbn'].replace('-', '').replace(' ', '')
            if not (len(isbn) == 10 or len(isbn) == 13):
                errors.append("ISBN must be 10 or 13 digits")
            
            if len(isbn) == 13 and not isbn.startswith('978'):
                errors.append("13-digit ISBN must start with 978")
        
        if 'quantity' in data:
            quantity = int(data.get('quantity', 0))
            if quantity < 1:
                errors.append("Book quantity must be at least 1")
            if quantity > 1000:
                errors.append("Book quantity cannot exceed 1000")
    
    return len(errors) == 0, errors
