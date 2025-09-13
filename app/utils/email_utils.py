from flask import current_app
from flask_mail import Message
from app import mail
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(to_email, subject, body, html_body=None):
    """
    Send email using Flask-Mail or SMTP fallback
    
    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        body (str): Plain text body
        html_body (str, optional): HTML body
    """
    try:
        # Try Flask-Mail first
        if current_app.config.get('MAIL_SERVER'):
            msg = Message(
                subject=subject,
                recipients=[to_email],
                body=body,
                html=html_body,
                sender=current_app.config.get('MAIL_DEFAULT_SENDER')
            )
            mail.send(msg)
            current_app.logger.info(f"Email sent to {to_email}: {subject}")
            return True
        else:
            # Fallback: Log email instead of sending
            current_app.logger.info(f"EMAIL TO: {to_email}")
            current_app.logger.info(f"SUBJECT: {subject}")
            current_app.logger.info(f"BODY: {body}")
            return True
            
    except Exception as e:
        current_app.logger.error(f"Failed to send email to {to_email}: {str(e)}")
        # For development, we'll just log the email content
        current_app.logger.info(f"EMAIL TO: {to_email}")
        current_app.logger.info(f"SUBJECT: {subject}")
        current_app.logger.info(f"BODY: {body}")
        return False

def send_bulk_email(recipients, subject, body, html_body=None):
    """
    Send bulk emails
    
    Args:
        recipients (list): List of email addresses
        subject (str): Email subject
        body (str): Plain text body
        html_body (str, optional): HTML body
    
    Returns:
        dict: Results with success/failure counts
    """
    results = {'success': 0, 'failed': 0, 'failed_emails': []}
    
    for email in recipients:
        try:
            if send_email(email, subject, body, html_body):
                results['success'] += 1
            else:
                results['failed'] += 1
                results['failed_emails'].append(email)
        except Exception as e:
            current_app.logger.error(f"Bulk email failed for {email}: {str(e)}")
            results['failed'] += 1
            results['failed_emails'].append(email)
    
    return results

def send_notification_email(user_type, user_email, notification_type, context):
    """
    Send templated notification emails
    
    Args:
        user_type (str): 'student', 'staff', 'admin'
        user_email (str): Recipient email
        notification_type (str): Type of notification
        context (dict): Template context variables
    """
    templates = {
        'admission_confirmation': {
            'subject': 'Application Received - {application_id}',
            'body': '''Dear {full_name},

Your admission application has been received successfully.

Application ID: {application_id}
Course: {course_name}
Submitted on: {application_date}

We will review your application and get back to you soon.

Best regards,
Admissions Office'''
        },
        'admission_approved': {
            'subject': 'Application Approved - Welcome!',
            'body': '''Dear {full_name},

Congratulations! Your application has been approved.

Roll Number: {roll_number}
Course: {course_name}
Admission Date: {admission_date}

Please complete your enrollment within 7 days.

Best regards,
Admissions Office'''
        },
        'admission_declined': {
            'subject': 'Application Status Update',
            'body': '''Dear {full_name},

Thank you for your interest. Unfortunately, your application could not be approved at this time.

Reason: {reason}

You are welcome to apply again in the future.

Best regards,
Admissions Office'''
        },
        'fee_reminder': {
            'subject': 'Fee Payment Reminder',
            'body': '''Dear {full_name},

This is a reminder about your pending fee payment.

Amount Due: ₹{amount}
Due Date: {due_date}

Please pay your fees to avoid late charges.

Best regards,
Accounts Office'''
        }
    }
    
    if notification_type not in templates:
        current_app.logger.error(f"Unknown notification type: {notification_type}")
        return False
    
    template = templates[notification_type]
    
    try:
        subject = template['subject'].format(**context)
        body = template['body'].format(**context)
        
        return send_email(user_email, subject, body)
    
    except KeyError as e:
        current_app.logger.error(f"Missing context variable for {notification_type}: {e}")
        return False
    except Exception as e:
        current_app.logger.error(f"Error sending notification email: {e}")
        return False
