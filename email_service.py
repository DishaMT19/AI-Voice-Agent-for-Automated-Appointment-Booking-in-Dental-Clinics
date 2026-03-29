import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os
import logging
from datetime import datetime

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Email configuration - Use environment variables for security
EMAIL_USER = os.getenv("EMAIL_USER", "your_email@gmail.com")
EMAIL_PASS = os.getenv("EMAIL_PASSWORD", "your_app_password")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

def send_confirmation_email(to_email, patient_name, appointment_date, appointment_time, confirmation_id=None):
    """Send appointment confirmation email to patient."""
    try:
        if not EMAIL_USER or EMAIL_USER == "your_email@gmail.com":
            logger.warning("Email not configured. Skipping email send.")
            return False
            
        # Email content
        subject = "Appointment Confirmation"
        confirmation_text = f" | Confirmation ID: {confirmation_id}" if confirmation_id else ""
        body = f"""
Hello {patient_name},

Your appointment has been successfully booked!{confirmation_text}

📅 Date: {appointment_date}
⏰ Time: {appointment_time}

Thank you for choosing our clinic.
We look forward to seeing you soon!

Best regards,
Dental Clinic Team
        """

        # Create email
        msg = MIMEMultipart()
        msg["From"] = EMAIL_USER
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Connect to SMTP server
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()

        logger.info(f"Confirmation email sent successfully to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Error sending email to {to_email}: {e}")
        return False


def send_appointment_confirmation_email(patient_email, patient_name, appointment_details, confirmation_id, language='en'):
    """
    Send comprehensive appointment confirmation email with full details.
    
    Args:
        patient_email: Patient's email address
        patient_name: Patient's name
        appointment_details: Dictionary with appointment information
            - service: Service name
            - date: Appointment date (YYYY-MM-DD format)
            - time: Appointment time (HH:MM format)
            - doctor_name: Doctor's name (optional)
            - duration: Duration in minutes (optional)
            - estimated_price: Price estimate (optional)
        confirmation_id: Unique confirmation ID
        language: Language code ('en' or 'hi')
    
    Returns:
        Boolean indicating success
    """
    try:
        # Check if email is configured
        if not EMAIL_USER or EMAIL_USER == "your_email@gmail.com":
            logger.warning("Email not configured. Skipping appointment confirmation email.")
            return False
        
        # Validate email
        if not patient_email or '@' not in patient_email:
            logger.warning(f"Invalid patient email: {patient_email}")
            return False
        
        # Extract appointment details
        service = appointment_details.get('service', 'Dental Service')
        date_str = appointment_details.get('date', '')
        time_str = appointment_details.get('time', '')
        doctor_name = appointment_details.get('doctor_name', 'Dr. Smile')
        duration = appointment_details.get('duration_minutes', 30)
        price = appointment_details.get('estimated_price', 'Contact clinic')
        
        # Format date for display
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            date_display = date_obj.strftime('%B %d, %Y')
        except:
            date_display = date_str
        
        # Format time for display (convert 24-hour to 12-hour)
        try:
            time_obj = datetime.strptime(time_str, '%H:%M')
            time_display = time_obj.strftime('%I:%M %p')
        except:
            time_display = time_str
        
        # Email subject and body based on language
        if language.lower() == 'hi':
            subject = "नियुक्ति पुष्टि - स्माइल डेंटल क्लिनिक"
            body = f"""
नमस्ते {patient_name},

आपकी दंत नियुक्ति सफलतापूर्वक बुक हो गई है!

पुष्टि ID: {confirmation_id}

🦷 सेवा: {service}
👨‍⚕️ डॉक्टर: {doctor_name}
📅 तारीख: {date_display}
⏰ समय: {time_display}
⏱️ अवधि: {duration} मिनट
💰 अनुमानित कीमत: ₹{price}

कृपया समय पर आएं। यदि आपको रद्द करना है तो कम से कम 24 घंटे पहले सूचित करें।

धन्यवाद,
स्माइल डेंटल क्लिनिक टीम
            """
        else:  # English
            subject = "Appointment Confirmation - Smile Dental Clinic"
            body = f"""
Hello {patient_name},

Your dental appointment has been successfully booked!

Confirmation ID: {confirmation_id}

🦷 Service: {service}
👨‍⚕️ Doctor: {doctor_name}
📅 Date: {date_display}
⏰ Time: {time_display}
⏱️ Duration: {duration} minutes
💰 Estimated Price: ₹{price}

Please arrive on time. If you need to cancel, please notify us at least 24 hours in advance.

Thank you,
Smile Dental Clinic Team
            """
        
        # Create email message
        msg = MIMEMultipart('alternative')
        msg['From'] = EMAIL_USER
        msg['To'] = patient_email
        msg['Subject'] = subject
        
        # Attach plain text message
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Create HTML version for better formatting
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9; border-radius: 8px;">
                    <h2 style="color: #2c5f8d; text-align: center;">{'Appointment Confirmation' if language.lower() != 'hi' else 'नियुक्ति पुष्टि'}</h2>
                    
                    <p>{"Hello" if language.lower() != 'hi' else "नमस्ते"} <strong>{patient_name}</strong>,</p>
                    
                    <p style="color: #27ae60; font-weight: bold;">
                        {"Your dental appointment has been successfully booked!" if language.lower() != 'hi' else "आपकी दंत नियुक्ति सफलतापूर्वक बुक हो गई है!"}
                    </p>
                    
                    <div style="background-color: white; padding: 20px; border-left: 4px solid #2c5f8d; margin: 20px 0;">
                        <p><strong>{"Confirmation ID:" if language.lower() != 'hi' else "पुष्टि ID:"}</strong> {confirmation_id}</p>
                        <p><strong>{"Service:" if language.lower() != 'hi' else "सेवा:"}</strong> {service}</p>
                        <p><strong>{"Doctor:" if language.lower() != 'hi' else "डॉक्टर:"}</strong> {doctor_name}</p>
                        <p><strong>{"Date:" if language.lower() != 'hi' else "तारीख:"}</strong> {date_display}</p>
                        <p><strong>{"Time:" if language.lower() != 'hi' else "समय:"}</strong> {time_display}</p>
                        <p><strong>{"Duration:" if language.lower() != 'hi' else "अवधि:"}</strong> {duration} {"minutes" if language.lower() != 'hi' else "मिनट"}</p>
                        <p><strong>{"Estimated Price:" if language.lower() != 'hi' else "अनुमानित कीमत:"}</strong> ₹{price}</p>
                    </div>
                    
                    <p style="color: #555; font-size: 14px;">
                        {"Please arrive on time. If you need to cancel, please notify us at least 24 hours in advance." if language.lower() != 'hi' else "कृपया समय पर आएं। यदि आपको रद्द करना है तो कम से कम 24 घंटे पहले सूचित करें।"}
                    </p>
                    
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    
                    <p style="color: #666; font-size: 12px; text-align: center;">
                        {"Thank you, Smile Dental Clinic Team" if language.lower() != 'hi' else "धन्यवाद, स्माइल डेंटल क्लिनिक टीम"}
                    </p>
                </div>
            </body>
        </html>
        """
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        # Send email
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Appointment confirmation email sent to {patient_email} with confirmation ID {confirmation_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending appointment confirmation email to {patient_email}: {str(e)}")
        return False

