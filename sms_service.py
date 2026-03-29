import os
import logging
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# SMS Configuration
SMS_PROVIDER = os.getenv("SMS_PROVIDER", "twilio")  # Options: twilio, msg91, nexmo
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE", "+1234567890")

# MSG91 Configuration
MSG91_AUTH_KEY = os.getenv("MSG91_AUTH_KEY")
MSG91_ROUTE = os.getenv("MSG91_ROUTE", "4")

# Nexmo Configuration
NEXMO_API_KEY = os.getenv("NEXMO_API_KEY")
NEXMO_API_SECRET = os.getenv("NEXMO_API_SECRET")
NEXMO_FROM = os.getenv("NEXMO_FROM", "DentalClinic")


def send_sms_twilio(to_phone, message):
    """Send SMS using Twilio."""
    try:
        from twilio.rest import Client
        
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=message,
            from_=TWILIO_PHONE,
            to=to_phone
        )
        logger.info(f"SMS sent via Twilio to {to_phone}: {message.sid}")
        return True
    except Exception as e:
        logger.error(f"Twilio SMS error: {e}")
        return False


def send_sms_msg91(to_phone, message):
    """Send SMS using MSG91."""
    try:
        url = "https://api.msg91.com/api/sendhttp"
        params = {
            "authkey": MSG91_AUTH_KEY,
            "mobiles": to_phone,
            "message": message,
            "route": MSG91_ROUTE,
            "sender": "DentalClinic"
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            logger.info(f"SMS sent via MSG91 to {to_phone}")
            return True
        else:
            logger.error(f"MSG91 error: {response.text}")
            return False
    except Exception as e:
        logger.error(f"MSG91 SMS error: {e}")
        return False


def send_sms_nexmo(to_phone, message):
    """Send SMS using Vonage (Nexmo)."""
    try:
        url = "https://rest.nexmo.com/sms/json"
        params = {
            "api_key": NEXMO_API_KEY,
            "api_secret": NEXMO_API_SECRET,
            "to": to_phone,
            "from": NEXMO_FROM,
            "text": message
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            logger.info(f"SMS sent via Nexmo to {to_phone}")
            return True
        else:
            logger.error(f"Nexmo error: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Nexmo SMS error: {e}")
        return False


def send_appointment_sms(to_phone, patient_name, appointment_date, appointment_time, confirmation_id=None):
    """Send appointment confirmation SMS."""
    try:
        # Format phone number (add country code if not present)
        if not to_phone.startswith('+'):
            to_phone = '+91' + to_phone[-10:]  # Assuming India, adjust as needed
        
        confirmation_text = f" | ID: {confirmation_id}" if confirmation_id else ""
        message = f"Hi {patient_name}, your appointment is confirmed for {appointment_date} at {appointment_time}{confirmation_text}. Thank you!"
        
        if SMS_PROVIDER == "twilio":
            return send_sms_twilio(to_phone, message)
        elif SMS_PROVIDER == "msg91":
            return send_sms_msg91(to_phone.lstrip('+'), message)
        elif SMS_PROVIDER == "nexmo":
            return send_sms_nexmo(to_phone, message)
        else:
            logger.warning(f"Unknown SMS provider: {SMS_PROVIDER}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending appointment SMS: {e}")
        return False
