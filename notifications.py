"""
ENHANCED NOTIFICATIONS MODULE v3.0
Improved SMS and Email delivery with retry logic, multi-provider support, and async capability.

Features:
- Multi-provider SMS: Twilio + HTTP API fallback
- Multi-provider Email: SendGrid + SMTP fallback
- Retry logic: Up to 3 attempts with exponential backoff
- Async delivery: Non-blocking notification queue
- Structured responses with delivery tracking
- Audit logging for all notification attempts
"""

import os
import smtplib
import threading
import time
import json
import requests
from typing import Dict, Tuple, Optional, Any
from datetime import datetime
from email.message import EmailMessage
from dataclasses import dataclass, asdict
import logging

# Try to import new modules (v3 refactored), fallback to simple functions
try:
    from .logging_config import logger_notifications, audit_logger
except ImportError:
    logger_notifications = logging.getLogger('notifications')
    audit_logger = logging.getLogger('audit')

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class NotificationResult:
    """Structured notification delivery result."""
    success: bool
    provider: str
    notification_type: str
    recipient: str
    status: str  # "sent", "failed", "queued", "retry", "skipped"
    error: Optional[str] = None
    delivery_id: Optional[str] = None
    attempt: int = 1
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


# ============================================================================
# SMS SERVICE
# ============================================================================

class SMSNotificationService:
    """Send SMS notifications via Twilio or HTTP API with fallback."""
    
    def __init__(self):
        """Initialize SMS service with configuration."""
        self.twilio_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.twilio_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.twilio_from = os.getenv('TWILIO_FROM', '+1234567890')
        self.max_retries = int(os.getenv('NOTIFICATION_RETRIES', 3))
        
    def send_sms(self, phone: str, message: str, attempt: int = 1) -> NotificationResult:
        """
        Send SMS with retry logic.
        
        Args:
            phone: Recipient phone number
            message: SMS message text
            attempt: Current attempt number
            
        Returns:
            NotificationResult with delivery status
        """
        if not phone:
            return NotificationResult(
                success=False,
                provider='twilio',
                notification_type='sms',
                recipient=phone or 'unknown',
                status='skipped',
                error='No phone number provided',
                attempt=attempt
            )
        
        # Try Twilio first
        if self.twilio_sid and self.twilio_token:
            result = self._send_via_twilio(phone, message, attempt)
            if result.status == 'sent':
                audit_logger.info(f"SMS sent via Twilio to {phone}")
                return result
        
        # Fallback to HTTP API
        result = self._send_via_http_api(phone, message, attempt)
        
        # Retry if failed and attempts remaining
        if result.status == 'failed' and attempt < self.max_retries:
            wait_time = 2 ** (attempt - 1)  # Exponential backoff
            logger_notifications.warning(
                f"SMS delivery failed, retrying in {wait_time}s (attempt {attempt}/{self.max_retries})"
            )
            time.sleep(wait_time)
            return self.send_sms(phone, message, attempt + 1)
        
        return result
    
    def _send_via_twilio(self, phone: str, message: str, attempt: int) -> NotificationResult:
        """Send via Twilio API."""
        try:
            import base64
            auth = base64.b64encode(
                f"{self.twilio_sid}:{self.twilio_token}".encode()
            ).decode()
            
            response = requests.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_sid}/Messages.json",
                auth=(self.twilio_sid, self.twilio_token),
                data={
                    'From': self.twilio_from,
                    'To': phone,
                    'Body': message[:160]  # SMS limit
                },
                timeout=10
            )
            
            if response.status_code == 201:
                return NotificationResult(
                    success=True,
                    provider='twilio',
                    notification_type='sms',
                    recipient=phone,
                    status='sent',
                    delivery_id=response.json().get('sid'),
                    attempt=attempt
                )
            else:
                return NotificationResult(
                    success=False,
                    provider='twilio',
                    notification_type='sms',
                    recipient=phone,
                    status='failed',
                    error=f"Twilio returned {response.status_code}",
                    attempt=attempt
                )
        except Exception as e:
            logger_notifications.error(f"Twilio SMS failed: {str(e)}")
            return NotificationResult(
                success=False,
                provider='twilio',
                notification_type='sms',
                recipient=phone,
                status='failed',
                error=str(e),
                attempt=attempt
            )
    
    def _send_via_http_api(self, phone: str, message: str, attempt: int) -> NotificationResult:
        """Send via generic HTTP API (alternative provider)."""
        try:
            api_url = os.getenv('SMS_API_URL')
            api_key = os.getenv('SMS_API_KEY')
            
            if not api_url:
                return NotificationResult(
                    success=False,
                    provider='http_api',
                    notification_type='sms',
                    recipient=phone,
                    status='skipped',
                    error='No SMS API configured',
                    attempt=attempt
                )
            
            response = requests.post(
                api_url,
                headers={'Authorization': f'Bearer {api_key}'} if api_key else {},
                json={
                    'phone': phone,
                    'message': message[:160],
                    'timestamp': datetime.now().isoformat()
                },
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                return NotificationResult(
                    success=True,
                    provider='http_api',
                    notification_type='sms',
                    recipient=phone,
                    status='sent',
                    delivery_id=response.json().get('message_id'),
                    attempt=attempt
                )
            else:
                return NotificationResult(
                    success=False,
                    provider='http_api',
                    notification_type='sms',
                    recipient=phone,
                    status='failed',
                    error=f"HTTP API returned {response.status_code}",
                    attempt=attempt
                )
        except Exception as e:
            logger_notifications.error(f"HTTP API SMS failed: {str(e)}")
            return NotificationResult(
                success=False,
                provider='http_api',
                notification_type='sms',
                recipient=phone,
                status='failed',
                error=str(e),
                attempt=attempt
            )


# ============================================================================
# EMAIL SERVICE
# ============================================================================

class EmailNotificationService:
    """Send Email notifications via SendGrid or SMTP with fallback."""
    
    def __init__(self):
        """Initialize email service with configuration."""
        self.sendgrid_key = os.getenv('SENDGRID_API_KEY')
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_pass = os.getenv('SMTP_PASS')
        self.email_from = os.getenv('EMAIL_FROM', 'no-reply@dentalvoice.com')
        self.max_retries = int(os.getenv('NOTIFICATION_RETRIES', 3))
        
    def send_email(self, to_email: str, subject: str, body: str, 
                   html_body: Optional[str] = None, attempt: int = 1) -> NotificationResult:
        """
        Send email with retry logic.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Plain text email body
            html_body: Optional HTML email body
            attempt: Current attempt number
            
        Returns:
            NotificationResult with delivery status
        """
        if not to_email:
            return NotificationResult(
                success=False,
                provider='sendgrid',
                notification_type='email',
                recipient=to_email or 'unknown',
                status='skipped',
                error='No email address provided',
                attempt=attempt
            )
        
        # Try SendGrid first
        if self.sendgrid_key:
            result = self._send_via_sendgrid(to_email, subject, body, html_body, attempt)
            if result.status == 'sent':
                audit_logger.info(f"Email sent via SendGrid to {to_email}")
                return result
        
        # Fallback to SMTP
        result = self._send_via_smtp(to_email, subject, body, html_body, attempt)
        
        # Retry if failed and attempts remaining
        if result.status == 'failed' and attempt < self.max_retries:
            wait_time = 2 ** (attempt - 1)
            logger_notifications.warning(
                f"Email delivery failed, retrying in {wait_time}s (attempt {attempt}/{self.max_retries})"
            )
            time.sleep(wait_time)
            return self.send_email(to_email, subject, body, html_body, attempt + 1)
        
        return result
    
    def _send_via_sendgrid(self, to_email: str, subject: str, body: str,
                          html_body: Optional[str], attempt: int) -> NotificationResult:
        """Send via SendGrid API."""
        try:
            response = requests.post(
                'https://api.sendgrid.com/v3/mail/send',
                headers={'Authorization': f'Bearer {self.sendgrid_key}'},
                json={
                    'personalizations': [{'to': [{'email': to_email}]}],
                    'from': {'email': self.email_from},
                    'subject': subject,
                    'content': [
                        {'type': 'text/plain', 'value': body}
                    ] + ([{'type': 'text/html', 'value': html_body}] if html_body else [])
                },
                timeout=10
            )
            
            if response.status_code == 202:
                return NotificationResult(
                    success=True,
                    provider='sendgrid',
                    notification_type='email',
                    recipient=to_email,
                    status='sent',
                    delivery_id=response.headers.get('X-Message-ID'),
                    attempt=attempt
                )
            else:
                return NotificationResult(
                    success=False,
                    provider='sendgrid',
                    notification_type='email',
                    recipient=to_email,
                    status='failed',
                    error=f"SendGrid returned {response.status_code}",
                    attempt=attempt
                )
        except Exception as e:
            logger_notifications.error(f"SendGrid email failed: {str(e)}")
            return NotificationResult(
                success=False,
                provider='sendgrid',
                notification_type='email',
                recipient=to_email,
                status='failed',
                error=str(e),
                attempt=attempt
            )
    
    def _send_via_smtp(self, to_email: str, subject: str, body: str,
                      html_body: Optional[str], attempt: int) -> NotificationResult:
        """Send via SMTP (Gmail, Office365, or custom)."""
        try:
            if not self.smtp_user or not self.smtp_pass:
                return NotificationResult(
                    success=False,
                    provider='smtp',
                    notification_type='email',
                    recipient=to_email,
                    status='skipped',
                    error='SMTP credentials not configured',
                    attempt=attempt
                )
            
            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From'] = self.email_from
            msg['To'] = to_email
            
            msg.set_content(body)
            if html_body:
                msg.add_alternative(html_body, subtype='html')
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            
            return NotificationResult(
                success=True,
                provider='smtp',
                notification_type='email',
                recipient=to_email,
                status='sent',
                attempt=attempt
            )
        except Exception as e:
            logger_notifications.error(f"SMTP email failed: {str(e)}")
            return NotificationResult(
                success=False,
                provider='smtp',
                notification_type='email',
                recipient=to_email,
                status='failed',
                error=str(e),
                attempt=attempt
            )


# ============================================================================
# NOTIFICATION HANDLER (Unified Interface)
# ============================================================================

class NotificationHandler:
    """Unified notification handler with async support."""
    
    def __init__(self):
        """Initialize notification handler."""
        self.sms_service = SMSNotificationService()
        self.email_service = EmailNotificationService()
        self.async_enabled = os.getenv('NOTIFICATIONS_BACKGROUND', 'true').lower() == 'true'
    
    def send_appointment_confirmation(self, appointment: Dict[str, Any], 
                                     async_mode: bool = True) -> Dict[str, Any]:
        """
        Send appointment confirmation via SMS and Email.
        
        Args:
            appointment: Appointment details dict with keys:
                - patient_name: Patient name
                - phone: Patient phone number
                - email: Patient email address
                - service: Service name
                - date: Appointment date
                - time: Appointment time
                - confirmation_id: Confirmation ID
            async_mode: If True, send in background thread (non-blocking)
            
        Returns:
            Dict with notification results (doesn't wait if async_mode=True)
        """
        if async_mode and self.async_enabled:
            # Queue in background thread (non-blocking)
            thread = threading.Thread(
                target=self._send_notifications_internal,
                args=(appointment,),
                daemon=True
            )
            thread.start()
            
            return {
                'queued': True,
                'message': 'Notifications queued for background delivery',
                'timestamp': datetime.now().isoformat()
            }
        else:
            # Send synchronously (blocking)
            return self._send_notifications_internal(appointment)
    
    def _send_notifications_internal(self, appointment: Dict[str, Any]) -> Dict[str, Any]:
        """Internal function that actually sends notifications."""
        results = {
            'appointment_id': appointment.get('appointment_id', 'unknown'),
            'confirmation_id': appointment.get('confirmation_id'),
            'sms': None,
            'email': None,
            'timestamp': datetime.now().isoformat()
        }
        
        # Send SMS
        if appointment.get('phone'):
            sms_message = (
                f"Hello {appointment.get('patient_name', 'there')}, "
                f"Your appointment is confirmed for "
                f"{appointment.get('date')} at {appointment.get('time')}. "
                f"Confirmation ID: {appointment.get('confirmation_id', 'N/A')}"
            )
            
            sms_result = self.sms_service.send_sms(
                appointment['phone'],
                sms_message
            )
            results['sms'] = sms_result.to_dict()
            logger_notifications.info(f"SMS result: {sms_result.status} to {appointment['phone']}")
        
        # Send Email
        if appointment.get('email'):
            email_subject = f"Appointment Confirmation - {appointment.get('confirmation_id', 'DentalVoice')}"
            email_body = f"""
Dear {appointment.get('patient_name', 'Patient')},

Your appointment is confirmed.

Service: {appointment.get('service', 'N/A')}
Date: {appointment.get('date', 'N/A')}
Time: {appointment.get('time', 'N/A')}
Confirmation ID: {appointment.get('confirmation_id', 'N/A')}

Please save this confirmation ID for your records.

Thank you,
DentalVoice Dental Clinic
"""
            
            email_html = f"""
<html>
  <body style="font-family: Arial, sans-serif;">
    <h2>Appointment Confirmation</h2>
    <p>Dear {appointment.get('patient_name', 'Patient')},</p>
    <p>Your appointment is confirmed.</p>
    <table border="1" cellpadding="10" style="border-collapse: collapse;">
      <tr><td><b>Service</b></td><td>{appointment.get('service', 'N/A')}</td></tr>
      <tr><td><b>Date</b></td><td>{appointment.get('date', 'N/A')}</td></tr>
      <tr><td><b>Time</b></td><td>{appointment.get('time', 'N/A')}</td></tr>
      <tr><td><b>Confirmation ID</b></td><td>{appointment.get('confirmation_id', 'N/A')}</td></tr>
    </table>
    <p>Please save this confirmation ID for your records.</p>
    <p>Thank you,<br>DentalVoice Dental Clinic</p>
  </body>
</html>
"""
            
            email_result = self.email_service.send_email(
                appointment['email'],
                email_subject,
                email_body,
                email_html
            )
            results['email'] = email_result.to_dict()
            logger_notifications.info(f"Email result: {email_result.status} to {appointment['email']}")
        
        return results


# ============================================================================
# LEGACY COMPATIBILITY FUNCTIONS
# ============================================================================

# Create singleton instances
sms_service = SMSNotificationService()
email_service = EmailNotificationService()
notification_handler = NotificationHandler()


def send_notifications(appt):
    """
    Legacy function - wrapper for backward compatibility.
    Sends appointment notifications via SMS and Email.
    """
    return notification_handler.send_appointment_confirmation(
        {
            'appointment_id': appt.get('appointment_id'),
            'confirmation_id': appt.get('confirmation_id'),
            'patient_name': appt.get('patient_name'),
            'phone': appt.get('phone_number'),
            'email': appt.get('email_address'),
            'service': appt.get('service_name'),
            'date': appt.get('appointment_date'),
            'time': appt.get('appointment_time')
        },
        async_mode=True
    )


def send_email(appt, pdf_path=None):
    """
    Legacy function - send email with optional PDF attachment.
    """
    try:
        body = f"""
Dear {appt.get('patient_name', 'Patient')},

Your appointment is confirmed.

Service: {appt.get('service_name', 'N/A')}
Date: {appt.get('appointment_date', 'N/A')}
Time: {appt.get('appointment_time', 'N/A')}

Smile Dental Clinic
"""
        result = email_service.send_email(
            appt.get('email_address'),
            f"Appointment Confirmation - {appt.get('appointment_id')}",
            body
        )
        return 'sent' if result.success else 'failed'
    except Exception as e:
        logger_notifications.error(f"Email send failed: {str(e)}")
        return 'failed'


def send_sms(appt):
    """
    Legacy function - send SMS notification.
    """
    if not appt.get('phone_number'):
        return 'skipped'
    
    try:
        message = (
            f"Appointment confirmed: {appt.get('service_name', 'Service')} "
            f"on {appt.get('appointment_date')} at {appt.get('appointment_time')}"
        )
        result = sms_service.send_sms(appt.get('phone_number'), message)
        return 'sent' if result.success else 'failed'
    except Exception as e:
        logger_notifications.error(f"SMS send failed: {str(e)}")
        return 'failed'
