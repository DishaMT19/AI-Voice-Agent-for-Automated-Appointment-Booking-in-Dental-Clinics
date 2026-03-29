import os
import json
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import logging

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment variables
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASS = os.getenv('SMTP_PASS', '')
EMAIL_FROM = os.getenv('EMAIL_FROM', SMTP_USER)

# Twilio Configuration (for SMS)
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_FROM = os.getenv('TWILIO_FROM', '')

class NotificationAgent:
    """Manual appointment notification agent - triggered only by dashboard"""
    
    def __init__(self):
        self.clinic_name = "Smile Dental Clinic"
        self.clinic_address = "123 Dental Street, City, State 12345"
        self.clinic_phone = "(123) 456-7890"
        self.clinic_email = "info@smiledental.com"
    
    def generate_pdf(self, appointment_data, output_path):
        """Generate professional PDF confirmation"""
        try:
            doc = SimpleDocTemplate(output_path, pagesize=letter)
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                fontSize=24,
                textColor=colors.HexColor('#2E5AAC'),
                spaceAfter=30
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor('#2E5AAC'),
                spaceAfter=12
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=11,
                spaceAfter=6
            )
            
            # Create story (content)
            story = []
            
            # Header
            story.append(Paragraph(self.clinic_name, title_style))
            story.append(Paragraph(self.clinic_address, normal_style))
            story.append(Paragraph(f"Phone: {self.clinic_phone} | Email: {self.clinic_email}", normal_style))
            story.append(Spacer(1, 20))
            
            # Confirmation title
            story.append(Paragraph("APPOINTMENT CONFIRMATION", heading_style))
            story.append(Spacer(1, 10))
            
            # Appointment details table
            appointment_details = [
                ["Appointment ID:", appointment_data['appointment_id']],
                ["Patient Name:", appointment_data['patient_name']],
                ["Service:", appointment_data['service_name']],
                ["Date:", appointment_data['appointment_date']],
                ["Time:", appointment_data['appointment_time']],
                ["Confirmation Date:", datetime.now().strftime("%B %d, %Y")],
                ["Confirmation Time:", datetime.now().strftime("%I:%M %p")]
            ]
            
            table = Table(appointment_details, colWidths=[2*inch, 4*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F4FD')),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2E5AAC')),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (0, -1), 11),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            
            story.append(table)
            story.append(Spacer(1, 20))
            
            # Instructions
            story.append(Paragraph("Important Instructions:", heading_style))
            instructions = [
                "1. Please arrive 15 minutes before your scheduled appointment time.",
                "2. Bring your ID and insurance card (if applicable).",
                "3. If you need to reschedule or cancel, please call us at least 24 hours in advance.",
                "4. For emergency dental care, call our emergency line: (123) 456-7891"
            ]
            
            for instruction in instructions:
                story.append(Paragraph(instruction, normal_style))
            
            story.append(Spacer(1, 20))
            
            # Footer
            footer_text = f"This is an automated confirmation. For any questions, please contact {self.clinic_name}."
            story.append(Paragraph(footer_text, ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.grey,
                alignment=1  # Center aligned
            )))
            
            # Build PDF
            doc.build(story)
            return True
            
        except Exception as e:
            logger.error(f"PDF generation error: {str(e)}")
            return False
    
    def send_email(self, appointment_data, pdf_path=None):
        """Send email notification with optional PDF attachment"""
        try:
            if not SMTP_HOST or not SMTP_USER:
                return {"success": False, "error": "Email configuration not set"}
            
            # Create email message
            msg = MIMEMultipart()
            msg['Subject'] = f"Appointment Confirmation – {appointment_data['appointment_id']}"
            msg['From'] = EMAIL_FROM
            msg['To'] = appointment_data['email_address']
            
            # Email body
            body = f"""Dear {appointment_data['patient_name']},

This message confirms your appointment at {self.clinic_name}.

Appointment Details:
• Appointment ID: {appointment_data['appointment_id']}
• Service: {appointment_data['service_name']}
• Date: {appointment_data['appointment_date']}
• Time: {appointment_data['appointment_time']}

Please find the attached PDF confirmation for your records.

Regards,
{self.clinic_name}
{self.clinic_address}
Phone: {self.clinic_phone}
Email: {self.clinic_email}
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach PDF if generated
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as f:
                    pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
                    pdf_attachment.add_header(
                        'Content-Disposition', 
                        'attachment', 
                        filename=f"Appointment_Confirmation_{appointment_data['appointment_id']}.pdf"
                    )
                    msg.attach(pdf_attachment)
            
            # Send email
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
            
            return {"success": True, "message": "Email sent successfully"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_sms(self, appointment_data):
        """Send SMS notification"""
        try:
            if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
                return {"success": False, "error": "SMS configuration not set"}
            
            from twilio.rest import Client
            
            # Format phone number
            phone_number = appointment_data['phone_number']
            if not phone_number.startswith('+'):
                phone_number = f"+91{phone_number}"  # Default to India
            
            # Create SMS message
            message_body = f"""Hello {appointment_data['patient_name']},
Your appointment (ID: {appointment_data['appointment_id']}) for {appointment_data['service_name']} on {appointment_data['appointment_date']} at {appointment_data['appointment_time']} is confirmed.
– {self.clinic_name}"""
            
            # Send SMS via Twilio
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            message = client.messages.create(
                body=message_body,
                from_=TWILIO_FROM,
                to=phone_number
            )
            
            return {"success": True, "message_sid": message.sid}
            
        except ImportError:
            return {"success": False, "error": "Twilio library not installed"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_notification(self, appointment_data):
        """Main method to send all notifications - called only by dashboard"""
        results = {
            "appointment_id": appointment_data['appointment_id'],
            "email_status": "pending",
            "sms_status": "pending",
            "pdf_generated": False,
            "dashboard_status": "Processing",
            "details": {}
        }
        
        try:
            # Generate PDF
            pdf_filename = f"Appointment_Confirmation_{appointment_data['appointment_id']}.pdf"
            pdf_path = os.path.join('/tmp', pdf_filename)
            
            pdf_success = self.generate_pdf(appointment_data, pdf_path)
            results['pdf_generated'] = pdf_success
            
            # Send Email
            email_result = self.send_email(appointment_data, pdf_path if pdf_success else None)
            results['email_status'] = "sent" if email_result['success'] else "failed"
            results['details']['email'] = email_result
            
            # Send SMS
            sms_result = self.send_sms(appointment_data)
            results['sms_status'] = "sent" if sms_result['success'] else "failed"
            results['details']['sms'] = sms_result
            
            # Update dashboard status
            if results['email_status'] == 'sent' or results['sms_status'] == 'sent':
                results['dashboard_status'] = "Confirmation Sent"
            else:
                results['dashboard_status'] = "Failed"
            
            # Clean up temporary PDF
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
                
        except Exception as e:
            logger.error(f"Notification error: {str(e)}")
            results['dashboard_status'] = "Failed"
            results['error'] = str(e)
        
        return results

# Initialize notification agent
notification_agent = NotificationAgent()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Manual Notification Agent",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/send-notification', methods=['POST'])
def send_notification():
    """API endpoint to send notifications - triggered manually from dashboard"""
    try:
        # Get appointment data from request
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "No appointment data provided"
            }), 400
        
        # Validate required fields
        required_fields = ['appointment_id', 'patient_name', 'phone_number', 
                          'email_address', 'service_name', 'appointment_date', 'appointment_time']
        
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                "success": False,
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400
        
        # Log the manual trigger
        logger.info(f"Manual notification triggered for appointment: {data['appointment_id']}")
        
        # Send notifications
        result = notification_agent.send_notification(data)
        
        # Return structured response
        response = {
            "success": result['dashboard_status'] != "Failed",
            "appointment_id": result['appointment_id'],
            "email_status": result['email_status'],
            "sms_status": result['sms_status'],
            "pdf_generated": result['pdf_generated'],
            "dashboard_status": result['dashboard_status'],
            "timestamp": datetime.now().isoformat()
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Notification API error: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/test-email', methods=['POST'])
def test_email_config():
    """Test email configuration"""
    try:
        data = request.get_json() or {}
        test_email = data.get('email', SMTP_USER)
        
        if not test_email:
            return jsonify({"success": False, "error": "No email provided"}), 400
        
        # Create simple test email
        msg = MIMEMultipart()
        msg['Subject'] = "Test Email - Notification System"
        msg['From'] = EMAIL_FROM
        msg['To'] = test_email
        
        body = "This is a test email from the DentalVoice Notification System."
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        
        return jsonify({"success": True, "message": f"Test email sent to {test_email}"})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    # Check configuration
    if not SMTP_USER or not SMTP_PASS:
        logger.warning("Email configuration incomplete. Email notifications will not work.")
    
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        logger.warning("SMS configuration incomplete. SMS notifications will not work.")
    
    logger.info("Starting Manual Notification Agent on port 8001")
    logger.info(f"Email configured: {'Yes' if SMTP_USER else 'No'}")
    logger.info(f"SMS configured: {'Yes' if TWILIO_ACCOUNT_SID else 'No'}")
    
    app.run(host='0.0.0.0', port=8001, debug=True)