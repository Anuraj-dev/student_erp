"""
Enhanced Email Service - Task 10 Implementation
Professional email notification system with templates, retry mechanism, and bulk sending
For ERP Student Management System - Government of Rajasthan
"""

from flask import current_app, render_template_string
from flask_mail import Message, Mail
from threading import Thread, Lock
import os
import time
import queue
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

# Global variables for email service
_retry_queue = queue.Queue()
_failed_emails = []
_email_stats = {'sent': 0, 'failed': 0, 'retries': 0}
_stats_lock = Lock()
_initialized = False

def initialize_email_service():
    """Initialize email service with retry mechanism"""
    global _initialized
    if not _initialized:
        _start_retry_worker()
        _initialized = True

def _start_retry_worker():
    """Start background thread for retry mechanism"""
    def retry_worker():
        while True:
            try:
                email_data = _retry_queue.get(timeout=60)
                if email_data is None:  # Shutdown signal
                    break
                _retry_send_email(email_data)
            except queue.Empty:
                continue
            except Exception as e:
                current_app.logger.error(f"Email retry worker error: {e}")
    
    retry_thread = Thread(target=retry_worker, daemon=True)
    retry_thread.start()

def _retry_send_email(email_data: Dict[str, Any]):
    """Retry sending failed email with exponential backoff"""
    max_attempts = current_app.config.get('EMAIL_RETRY_ATTEMPTS', 3)
    retry_delay = current_app.config.get('EMAIL_RETRY_DELAY', 60)
    
    attempts = email_data.get('attempts', 0)
    
    if attempts < max_attempts:
        # Wait before retry (exponential backoff)
        time.sleep(retry_delay * (attempts + 1))
        
        success = send_email_internal(
            email_data['to'],
            email_data['subject'],
            email_data['template'],
            email_data.get('attachments'),
            **email_data.get('kwargs', {})
        )
        
        if success:
            current_app.logger.info(f"Email retry successful after {attempts + 1} attempts")
            with _stats_lock:
                _email_stats['retries'] += 1
        else:
            email_data['attempts'] = attempts + 1
            if email_data['attempts'] < max_attempts:
                _retry_queue.put(email_data)
            else:
                _failed_emails.append(email_data)
                current_app.logger.error(f"Email failed permanently after {max_attempts} attempts")

def send_async_email(app, msg, mail):
    """Send email asynchronously with error handling"""
    with app.app_context():
        try:
            mail.send(msg)
            current_app.logger.info(f"Email sent successfully to: {msg.recipients}")
            with _stats_lock:
                _email_stats['sent'] += 1
        except Exception as e:
            current_app.logger.error(f"Failed to send email: {e}")
            with _stats_lock:
                _email_stats['failed'] += 1
            raise

def send_email_internal(to, subject, template, attachments=None, **kwargs):
    """Internal method for sending email"""
    try:
        app = current_app._get_current_object()
        mail = Mail(app)
        
        msg = Message(
            subject=f"[{current_app.config.get('COLLEGE_NAME', 'Government Technical College')}] {subject}",
            sender=current_app.config.get('MAIL_DEFAULT_SENDER'),
            recipients=[to] if isinstance(to, str) else to
        )
        
        # Render template with provided variables
        msg.html = render_template_string(template, **kwargs)
        
        # Add attachments if provided
        if attachments:
            for attachment in attachments:
                if os.path.exists(attachment['file_path']):
                    with open(attachment['file_path'], 'rb') as f:
                        msg.attach(
                            attachment['filename'],
                            attachment['content_type'],
                            f.read()
                        )
        
        # Send sync for critical operations or async for others
        if current_app.config.get('MAIL_ASYNC', True):
            thr = Thread(target=send_async_email, args=[app, msg, mail])
            thr.start()
        else:
            mail.send(msg)
            with _stats_lock:
                _email_stats['sent'] += 1
        
        return True
        
    except Exception as e:
        current_app.logger.error(f"Email sending failed: {e}")
        with _stats_lock:
            _email_stats['failed'] += 1
        return False

def send_email(to, subject, template, attachments=None, retry_on_failure=True, **kwargs):
    """
    Enhanced send email with retry mechanism and statistics tracking
    Args:
        to: recipient email or list of emails
        subject: email subject
        template: email template string
        attachments: list of attachment dictionaries
        retry_on_failure: whether to retry on failure
        **kwargs: template variables
    """
    initialize_email_service()
    
    success = send_email_internal(to, subject, template, attachments, **kwargs)
    
    # If failed and retry is enabled, add to retry queue
    if not success and retry_on_failure:
        email_data = {
            'to': to,
            'subject': subject,
            'template': template,
            'attachments': attachments,
            'kwargs': kwargs,
            'attempts': 0,
            'timestamp': datetime.now()
        }
        _retry_queue.put(email_data)
    
    return success

def send_bulk_emails(email_list: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Send multiple emails in batches with rate limiting
    Args:
        email_list: List of email dictionaries with keys: to, subject, template, kwargs
    Returns:
        Dict with sent/failed counts
    """
    batch_size = current_app.config.get('EMAIL_BATCH_SIZE', 50)
    results = {'sent': 0, 'failed': 0}
    
    for i in range(0, len(email_list), batch_size):
        batch = email_list[i:i + batch_size]
        
        for email_data in batch:
            success = send_email(
                email_data['to'],
                email_data['subject'],
                email_data['template'],
                email_data.get('attachments'),
                **email_data.get('kwargs', {})
            )
            
            if success:
                results['sent'] += 1
            else:
                results['failed'] += 1
        
        # Rate limiting - pause between batches
        if i + batch_size < len(email_list):
            time.sleep(2)  # 2-second pause between batches
    
    return results

def get_email_statistics() -> Dict[str, Any]:
    """Get email service statistics"""
    with _stats_lock:
        return {
            'emails_sent': _email_stats['sent'],
            'emails_failed': _email_stats['failed'],
            'successful_retries': _email_stats['retries'],
            'pending_retries': _retry_queue.qsize(),
            'permanently_failed': len(_failed_emails)
        }

def get_failed_emails() -> List[Dict[str, Any]]:
    """Get list of permanently failed emails"""
    return _failed_emails.copy()

def send_admission_confirmation(applicant_email, applicant_name, application_id):
    """Send admission application confirmation email"""
    subject = "Application Submitted Successfully"
    
    template = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
            .header { background-color: #2c3e50; color: white; padding: 20px; text-align: center; }
            .content { padding: 20px; }
            .footer { background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; }
            .application-id { background-color: #e8f4fd; padding: 10px; border-radius: 5px; margin: 15px 0; }
        </style>
    </head>
    <body>
        <div class="header">
            <h2>{{ college_name }}</h2>
            <p>Directorate of Technical Education, Rajasthan</p>
        </div>
        
        <div class="content">
            <h3>Dear {{ applicant_name }},</h3>
            
            <p>Your admission application has been submitted successfully!</p>
            
            <div class="application-id">
                <strong>Application ID:</strong> {{ application_id }}
            </div>
            
            <p><strong>Important Information:</strong></p>
            <ul>
                <li>Your application is currently under review</li>
                <li>You will receive updates via email</li>
                <li>Keep your Application ID safe for future reference</li>
                <li>You can track your application status using your Application ID</li>
            </ul>
            
            <p><strong>Required Documents:</strong></p>
            <ul>
                <li>10th Mark Sheet</li>
                <li>12th Mark Sheet</li>
                <li>Transfer Certificate</li>
                <li>Aadhar Card</li>
                <li>Passport Size Photos</li>
                <li>Caste Certificate (if applicable)</li>
            </ul>
            
            <p>If you have any questions, please contact our admission office.</p>
            
            <p>Best regards,<br>
            Admission Office<br>
            {{ college_name }}</p>
        </div>
        
        <div class="footer">
            <p>This is an automated email. Please do not reply to this email.</p>
            <p>{{ college_address }} | {{ college_phone }} | {{ college_email }}</p>
        </div>
    </body>
    </html>
    """
    
    return send_email(
        to=applicant_email,
        subject=subject,
        template=template,
        applicant_name=applicant_name,
        application_id=application_id,
        college_name=current_app.config.get('COLLEGE_NAME', 'Government Technical College'),
        college_address=current_app.config.get('COLLEGE_ADDRESS', ''),
        college_phone=current_app.config.get('COLLEGE_PHONE', ''),
        college_email=current_app.config.get('COLLEGE_EMAIL', '')
    )

def send_admission_status_update(applicant_email, applicant_name, application_id, status, remarks=None):
    """Send admission status update email"""
    status_messages = {
        'approved': {
            'subject': 'Admission Approved - Congratulations!',
            'message': 'Congratulations! Your admission application has been approved.',
            'color': '#28a745'
        },
        'declined': {
            'subject': 'Admission Application Status Update',
            'message': 'We regret to inform you that your admission application has been declined.',
            'color': '#dc3545'
        },
        'documents_pending': {
            'subject': 'Documents Required - Action Needed',
            'message': 'Additional documents are required to process your application.',
            'color': '#ffc107'
        }
    }
    
    status_info = status_messages.get(status, {
        'subject': 'Admission Application Status Update',
        'message': f'Your application status has been updated to: {status}',
        'color': '#007bff'
    })
    
    template = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
            .header { background-color: #2c3e50; color: white; padding: 20px; text-align: center; }
            .content { padding: 20px; }
            .status-box { background-color: {{ status_color }}; color: white; padding: 15px; border-radius: 5px; margin: 15px 0; text-align: center; }
            .footer { background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h2>{{ college_name }}</h2>
            <p>Admission Status Update</p>
        </div>
        
        <div class="content">
            <h3>Dear {{ applicant_name }},</h3>
            
            <div class="status-box">
                <h4>{{ status_message }}</h4>
                <p>Application ID: {{ application_id }}</p>
            </div>
            
            {% if remarks %}
            <p><strong>Additional Information:</strong></p>
            <p>{{ remarks }}</p>
            {% endif %}
            
            {% if status == 'approved' %}
            <p><strong>Next Steps:</strong></p>
            <ul>
                <li>You will receive your admission letter shortly</li>
                <li>Complete the fee payment process</li>
                <li>Submit original documents for verification</li>
                <li>Complete hostel allocation (if required)</li>
            </ul>
            {% elif status == 'documents_pending' %}
            <p><strong>Action Required:</strong></p>
            <ul>
                <li>Submit the required documents at the earliest</li>
                <li>Contact the admission office for clarifications</li>
                <li>Keep checking your email for updates</li>
            </ul>
            {% endif %}
            
            <p>For any queries, please contact our admission office with your Application ID.</p>
            
            <p>Best regards,<br>
            Admission Office<br>
            {{ college_name }}</p>
        </div>
        
        <div class="footer">
            <p>This is an automated email. Please do not reply to this email.</p>
        </div>
    </body>
    </html>
    """
    
    return send_email(
        to=applicant_email,
        subject=status_info['subject'],
        template=template,
        applicant_name=applicant_name,
        application_id=application_id,
        status=status,
        status_message=status_info['message'],
        status_color=status_info['color'],
        remarks=remarks,
        college_name=current_app.config.get('COLLEGE_NAME', 'Government Technical College')
    )

def send_fee_reminder(student_email, student_name, fee_details, due_date):
    """Send fee payment reminder email"""
    subject = "Fee Payment Reminder"
    
    template = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
            .header { background-color: #2c3e50; color: white; padding: 20px; text-align: center; }
            .content { padding: 20px; }
            .fee-details { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }
            .urgent { color: #dc3545; font-weight: bold; }
            .footer { background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h2>{{ college_name }}</h2>
            <p>Fee Payment Reminder</p>
        </div>
        
        <div class="content">
            <h3>Dear {{ student_name }},</h3>
            
            <p>This is a reminder that your fee payment is due.</p>
            
            <div class="fee-details">
                <h4>Fee Details:</h4>
                {% for fee in fee_details %}
                <p><strong>{{ fee.description }}:</strong> ₹{{ fee.amount }}</p>
                {% endfor %}
                <hr>
                <p><strong>Total Amount:</strong> ₹{{ total_amount }}</p>
                <p class="urgent">Due Date: {{ due_date }}</p>
            </div>
            
            <p><strong>Payment Methods:</strong></p>
            <ul>
                <li>Online Payment Portal</li>
                <li>Bank Transfer</li>
                <li>Demand Draft</li>
                <li>Cash Payment at College Office</li>
            </ul>
            
            <p><strong>Important:</strong> Late payment may result in additional charges.</p>
            
            <p>For payment assistance, please contact the accounts office.</p>
            
            <p>Best regards,<br>
            Accounts Office<br>
            {{ college_name }}</p>
        </div>
        
        <div class="footer">
            <p>This is an automated email. Please do not reply to this email.</p>
        </div>
    </body>
    </html>
    """
    
    total_amount = sum(fee.get('amount', 0) for fee in fee_details)
    
    return send_email(
        to=student_email,
        subject=subject,
        template=template,
        student_name=student_name,
        fee_details=fee_details,
        total_amount=total_amount,
        due_date=due_date.strftime('%d %B %Y') if hasattr(due_date, 'strftime') else str(due_date),
        college_name=current_app.config.get('COLLEGE_NAME', 'Government Technical College')
    )

def send_payment_receipt(student_email, student_name, payment_details):
    """Send payment receipt email"""
    subject = f"Payment Receipt - {payment_details.get('receipt_number', 'N/A')}"
    
    template = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
            .header { background-color: #28a745; color: white; padding: 20px; text-align: center; }
            .content { padding: 20px; }
            .receipt-details { background-color: #e8f5e8; padding: 15px; border-radius: 5px; margin: 15px 0; border: 2px solid #28a745; }
            .footer { background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h2>{{ college_name }}</h2>
            <p>Payment Receipt</p>
        </div>
        
        <div class="content">
            <h3>Dear {{ student_name }},</h3>
            
            <p>Thank you for your payment. Your transaction has been processed successfully.</p>
            
            <div class="receipt-details">
                <h4>Payment Details:</h4>
                <p><strong>Receipt Number:</strong> {{ receipt_number }}</p>
                <p><strong>Transaction ID:</strong> {{ transaction_id }}</p>
                <p><strong>Payment Date:</strong> {{ payment_date }}</p>
                <p><strong>Payment Method:</strong> {{ payment_method }}</p>
                <p><strong>Amount Paid:</strong> ₹{{ amount_paid }}</p>
                <p><strong>Fee Type:</strong> {{ fee_type }}</p>
                <p><strong>Semester:</strong> {{ semester }}</p>
            </div>
            
            <p><strong>Important:</strong> Please keep this receipt for your records.</p>
            
            <p>If you have any questions about this payment, please contact our accounts office.</p>
            
            <p>Best regards,<br>
            Accounts Office<br>
            {{ college_name }}</p>
        </div>
        
        <div class="footer">
            <p>This is an automated email. Please do not reply to this email.</p>
        </div>
    </body>
    </html>
    """
    
    return send_email(
        to=student_email,
        subject=subject,
        template=template,
        student_name=student_name,
        receipt_number=payment_details.get('receipt_number', 'N/A'),
        transaction_id=payment_details.get('transaction_id', 'N/A'),
        payment_date=payment_details.get('payment_date', 'N/A'),
        payment_method=payment_details.get('payment_method', 'N/A'),
        amount_paid=payment_details.get('amount', 'N/A'),
        fee_type=payment_details.get('fee_type', 'N/A'),
        semester=payment_details.get('semester', 'N/A'),
        college_name=current_app.config.get('COLLEGE_NAME', 'Government Technical College')
    )

def send_staff_notification(staff_email, staff_name, subject, message, action_required=False):
    """Send notification to staff members"""
    template = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
            .header { background-color: #007bff; color: white; padding: 20px; text-align: center; }
            .content { padding: 20px; }
            .message-box { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }
            .action-required { background-color: #fff3cd; border: 1px solid #ffeaa7; }
            .footer { background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h2>{{ college_name }} - ERP System</h2>
            <p>Staff Notification</p>
        </div>
        
        <div class="content">
            <h3>Dear {{ staff_name }},</h3>
            
            <div class="message-box {% if action_required %}action-required{% endif %}">
                {% if action_required %}
                <p><strong>⚠️ Action Required</strong></p>
                {% endif %}
                <p>{{ message }}</p>
            </div>
            
            <p>Please log in to the ERP system to view details and take necessary action.</p>
            
            <p>Best regards,<br>
            ERP System<br>
            {{ college_name }}</p>
        </div>
        
        <div class="footer">
            <p>This is an automated email from the ERP system.</p>
        </div>
    </body>
    </html>
    """
    
    return send_email(
        to=staff_email,
        subject=subject,
        template=template,
        staff_name=staff_name,
        message=message,
        action_required=action_required,
        college_name=current_app.config.get('COLLEGE_NAME', 'Government Technical College')
    )

def send_welcome_email(student_email: str, student_name: str, roll_no: str, 
                      course_name: str, login_password: str) -> bool:
    """Send welcome email with login credentials"""
    subject = f"Welcome to Government Technical College - {roll_no}"
    
    template = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
            .header { background-color: #FF6B35; color: white; padding: 20px; text-align: center; }
            .content { padding: 20px; }
            .welcome-box { background-color: #4A90E2; color: white; padding: 20px; border-radius: 10px; margin: 15px 0; text-align: center; }
            .credentials { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #4A90E2; }
            .important-dates { background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 15px 0; }
            .footer { background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h2>{{ college_name }}</h2>
            <p>Directorate of Technical Education, Rajasthan</p>
        </div>
        
        <div class="content">
            <div class="welcome-box">
                <h2>Welcome, {{ student_name }}!</h2>
                <p>You are now part of the Government Technical Education family</p>
            </div>
            
            <p>Dear {{ student_name }},</p>
            
            <p>Congratulations on your successful admission to <strong>{{ course_name }}</strong>! We are excited to have you as part of our institution.</p>
            
            <div class="credentials">
                <h4>🔐 Your Login Credentials:</h4>
                <p><strong>Roll Number:</strong> {{ roll_no }}</p>
                <p><strong>Password:</strong> {{ login_password }}</p>
                <p><strong>Login URL:</strong> <a href="{{ login_url }}">{{ login_url }}</a></p>
                <p><em>Please change your password after first login for security.</em></p>
            </div>
            
            <div class="important-dates">
                <h4>📅 Important Dates:</h4>
                <ul>
                    <li><strong>Orientation Program:</strong> {{ orientation_date }}</li>
                    <li><strong>Classes Begin:</strong> {{ semester_start }}</li>
                    <li><strong>Fee Payment Due:</strong> {{ fee_due_date }}</li>
                </ul>
            </div>
            
            <p><strong>What's Next?</strong></p>
            <ul>
                <li>Complete document verification at the admission office</li>
                <li>Pay semester fees before the due date</li>
                <li>Apply for hostel accommodation (if required)</li>
                <li>Attend the orientation program</li>
                <li>Collect your ID card and library card</li>
            </ul>
            
            <p><strong>Need Help?</strong><br>
            Contact our support team at: {{ support_email }}</p>
            
            <p>We look forward to supporting you throughout your academic journey!</p>
            
            <p>Best regards,<br>
            Admission Office<br>
            {{ college_name }}</p>
        </div>
        
        <div class="footer">
            <p>Government of Rajasthan | Directorate of Technical Education</p>
            <p>This is an automated email. Please do not reply to this email.</p>
        </div>
    </body>
    </html>
    """
    
    return send_email(
        to=student_email,
        subject=subject,
        template=template,
        student_name=student_name,
        roll_no=roll_no,
        course_name=course_name,
        login_password=login_password,
        college_name=current_app.config.get('COLLEGE_NAME', 'Government Technical College'),
        login_url=f"{current_app.config.get('BASE_URL', '')}/login",
        support_email=current_app.config.get('SUPPORT_EMAIL', 'support@dtegov.raj.in'),
        orientation_date='10th July 2025',
        semester_start='15th July 2025',
        fee_due_date='30th July 2025'
    )

def send_hostel_allocation(student_email: str, student_name: str, roll_no: str,
                          hostel_name: str, room_number: str) -> bool:
    """Send hostel allocation notification"""
    subject = f"Hostel Allocation Confirmation - {hostel_name}, Room {room_number}"
    
    template = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
            .header { background-color: #4A90E2; color: white; padding: 20px; text-align: center; }
            .content { padding: 20px; }
            .allocation-box { background-color: #28a745; color: white; padding: 20px; border-radius: 10px; margin: 15px 0; text-align: center; }
            .details { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }
            .footer { background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h2>{{ college_name }}</h2>
            <p>Hostel Allocation Notification</p>
        </div>
        
        <div class="content">
            <h3>Dear {{ student_name }},</h3>
            
            <div class="allocation-box">
                <h3>🏠 Hostel Allocated Successfully!</h3>
                <p><strong>{{ hostel_name }} - Room {{ room_number }}</strong></p>
            </div>
            
            <div class="details">
                <h4>Allocation Details:</h4>
                <p><strong>Student Name:</strong> {{ student_name }}</p>
                <p><strong>Roll Number:</strong> {{ roll_no }}</p>
                <p><strong>Hostel:</strong> {{ hostel_name }}</p>
                <p><strong>Room Number:</strong> {{ room_number }}</p>
                <p><strong>Allocation Date:</strong> {{ allocation_date }}</p>
                <p><strong>Check-in Date:</strong> {{ check_in_date }}</p>
            </div>
            
            <p><strong>Important Instructions:</strong></p>
            <ul>
                <li>Report to the hostel warden before {{ check_in_date }}</li>
                <li>Carry original ID documents and this email</li>
                <li>Complete hostel fee payment before check-in</li>
                <li>Bring required bedding and personal items</li>
                <li>Follow hostel rules and regulations</li>
            </ul>
            
            <p><strong>Contact Information:</strong><br>
            Hostel Warden: {{ warden_contact }}<br>
            Hostel Office: Available 9 AM - 6 PM</p>
            
            <p>Welcome to hostel life! We hope you have a comfortable stay.</p>
            
            <p>Best regards,<br>
            Hostel Administration<br>
            {{ college_name }}</p>
        </div>
        
        <div class="footer">
            <p>This is an automated email. Please do not reply to this email.</p>
        </div>
    </body>
    </html>
    """
    
    return send_email(
        to=student_email,
        subject=subject,
        template=template,
        student_name=student_name,
        roll_no=roll_no,
        hostel_name=hostel_name,
        room_number=room_number,
        college_name=current_app.config.get('COLLEGE_NAME', 'Government Technical College'),
        allocation_date=datetime.now().strftime('%d-%m-%Y'),
        check_in_date=(datetime.now() + timedelta(days=7)).strftime('%d-%m-%Y'),
        warden_contact='+91-141-XXXXXXX'
    )

def send_examination_notification(student_email: str, student_name: str, roll_no: str,
                                exam_schedule: List[Dict]) -> bool:
    """Send examination schedule notification"""
    subject = f"Examination Schedule - {roll_no}"
    
    template = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
            .header { background-color: #dc3545; color: white; padding: 20px; text-align: center; }
            .content { padding: 20px; }
            .exam-schedule { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }
            .exam-item { padding: 10px; border-bottom: 1px solid #dee2e6; }
            .instructions { background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 15px 0; }
            .footer { background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h2>{{ college_name }}</h2>
            <p>Examination Schedule</p>
        </div>
        
        <div class="content">
            <h3>Dear {{ student_name }},</h3>
            
            <p>Your examination schedule has been finalized. Please find the details below:</p>
            
            <div class="exam-schedule">
                <h4>📋 Examination Schedule for {{ roll_no }}:</h4>
                {% for exam in exam_schedule %}
                <div class="exam-item">
                    <strong>{{ exam.subject }}</strong><br>
                    Date: {{ exam.date }} | Time: {{ exam.time }}<br>
                    Duration: {{ exam.duration }}
                </div>
                {% endfor %}
            </div>
            
            <div class="instructions">
                <h4>⚠️ Important Instructions:</h4>
                <ul>
                    <li>Report to exam center {{ reporting_time }} before exam time</li>
                    <li>Carry valid ID card and hall ticket</li>
                    <li>Mobile phones are strictly prohibited</li>
                    <li>Use only blue/black pen for writing</li>
                    <li>Read exam instructions carefully</li>
                </ul>
                <p><strong>Exam Center:</strong> {{ exam_center }}</p>
                <p><strong>Detailed Instructions:</strong> <a href="{{ instructions_url }}">Click here</a></p>
            </div>
            
            <p>Best of luck for your examinations!</p>
            
            <p>Best regards,<br>
            Examination Controller<br>
            {{ college_name }}</p>
        </div>
        
        <div class="footer">
            <p>This is an automated email. Please do not reply to this email.</p>
        </div>
    </body>
    </html>
    """
    
    return send_email(
        to=student_email,
        subject=subject,
        template=template,
        student_name=student_name,
        roll_no=roll_no,
        exam_schedule=exam_schedule,
        college_name=current_app.config.get('COLLEGE_NAME', 'Government Technical College'),
        exam_center='Main Campus',
        reporting_time='30 minutes',
        instructions_url=f"{current_app.config.get('BASE_URL', '')}/exam/instructions"
    )

def send_fee_receipt_with_pdf(student_email: str, student_name: str, roll_no: str,
                             amount_paid: float, transaction_id: str, receipt_pdf_path: str) -> bool:
    """Send fee payment receipt email with PDF attachment"""
    subject = f"Fee Payment Receipt - ₹{amount_paid:,.2f} ({transaction_id})"
    
    template = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
            .header { background-color: #28a745; color: white; padding: 20px; text-align: center; }
            .content { padding: 20px; }
            .receipt-details { background-color: #e8f5e8; padding: 15px; border-radius: 5px; margin: 15px 0; border: 2px solid #28a745; }
            .attachment-note { background-color: #cce5ff; padding: 15px; border-radius: 5px; margin: 15px 0; }
            .footer { background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h2>{{ college_name }}</h2>
            <p>Payment Receipt Confirmation</p>
        </div>
        
        <div class="content">
            <h3>Dear {{ student_name }},</h3>
            
            <p>Thank you for your payment! Your transaction has been processed successfully.</p>
            
            <div class="receipt-details">
                <h4>💳 Payment Details:</h4>
                <p><strong>Student Name:</strong> {{ student_name }}</p>
                <p><strong>Roll Number:</strong> {{ roll_no }}</p>
                <p><strong>Amount Paid:</strong> ₹{{ amount_paid }}</p>
                <p><strong>Transaction ID:</strong> {{ transaction_id }}</p>
                <p><strong>Payment Date:</strong> {{ payment_date }}</p>
            </div>
            
            <div class="attachment-note">
                <h4>📎 Official Receipt:</h4>
                <p>Your official payment receipt is attached to this email in PDF format.</p>
                <p>Please save this receipt for your records and future reference.</p>
            </div>
            
            <p><strong>Important Notes:</strong></p>
            <ul>
                <li>This receipt is valid for all official purposes</li>
                <li>Keep this receipt safe for future reference</li>
                <li>Contact accounts office for any queries</li>
            </ul>
            
            <p>Thank you for choosing Government Technical College!</p>
            
            <p>Best regards,<br>
            Accounts Office<br>
            {{ college_name }}</p>
        </div>
        
        <div class="footer">
            <p>Government of Rajasthan | Directorate of Technical Education</p>
        </div>
    </body>
    </html>
    """
    
    attachments = [{
        'file_path': receipt_pdf_path,
        'filename': f'Fee_Receipt_{transaction_id}.pdf',
        'content_type': 'application/pdf'
    }] if os.path.exists(receipt_pdf_path) else None
    
    return send_email(
        to=student_email,
        subject=subject,
        template=template,
        attachments=attachments,
        student_name=student_name,
        roll_no=roll_no,
        amount_paid=f"{amount_paid:,.2f}",
        transaction_id=transaction_id,
        payment_date=datetime.now().strftime('%d-%m-%Y %H:%M'),
        college_name=current_app.config.get('COLLEGE_NAME', 'Government Technical College')
    )

# Enhanced utility functions for common email operations
def send_system_alert(admin_email: str, alert_type: str, message: str, 
                     system_details: Dict[str, Any]) -> bool:
    """Send system alerts to administrators"""
    subject = f"System Alert: {alert_type}"
    
    template = """
    <html>
    <head>
        <style>
            body { font-family: monospace; line-height: 1.6; color: #333; }
            .header { background-color: #dc3545; color: white; padding: 20px; text-align: center; }
            .alert-box { background-color: #f8d7da; padding: 15px; border-radius: 5px; margin: 15px 0; border: 1px solid #f5c6cb; }
            .system-info { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }
        </style>
    </head>
    <body>
        <div class="header">
            <h2>🚨 SYSTEM ALERT</h2>
            <p>ERP System Monitoring</p>
        </div>
        
        <div class="alert-box">
            <h4>Alert Type: {{ alert_type }}</h4>
            <p>{{ message }}</p>
            <p><strong>Timestamp:</strong> {{ timestamp }}</p>
        </div>
        
        <div class="system-info">
            <h4>System Details:</h4>
            {% for key, value in system_details.items() %}
            <p><strong>{{ key }}:</strong> {{ value }}</p>
            {% endfor %}
        </div>
        
        <p>Please investigate and take appropriate action.</p>
    </body>
    </html>
    """
    
    return send_email(
        to=admin_email,
        subject=subject,
        template=template,
        retry_on_failure=False,  # System alerts should be immediate
        alert_type=alert_type,
        message=message,
        system_details=system_details,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

# Function aliases for backward compatibility and testing
def send_status_update(applicant_email, applicant_name, application_id, status, remarks=None):
    """Alias for send_admission_status_update"""
    return send_admission_status_update(applicant_email, applicant_name, application_id, status, remarks)

def send_receipt(student_email, student_name, payment_details):
    """Alias for send_payment_receipt"""
    return send_payment_receipt(student_email, student_name, payment_details)
