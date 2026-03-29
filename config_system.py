"""
VoiceAgent Backend Configuration System
Loads all settings from environment variables with sensible defaults
"""

import os
import json
from pathlib import Path

# ============================================================
# PATHS & DIRECTORIES
# ============================================================
BASE_DIR = Path(__file__).parent.absolute()
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
LOG_DIR = Path(os.getenv("LOG_DIR", str(BASE_DIR / "logs")))
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", str(BASE_DIR / "frontend")))
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", str(BASE_DIR / "uploads")))
PDF_DIR = Path(os.getenv("PDF_DIR", str(BASE_DIR / "generated_pdfs")))

# Create directories if they don't exist
for directory in [DATA_DIR, LOG_DIR, FRONTEND_DIR, UPLOADS_DIR, PDF_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ============================================================
# SERVER CONFIGURATION
# ============================================================
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")

# ============================================================
# EMAIL CONFIGURATION
# ============================================================
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER") or os.getenv("EMAIL_USER")
SMTP_PASS = os.getenv("SMTP_PASS") or os.getenv("EMAIL_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)

# SendGrid API (alternative)
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")

# Email settings
EMAIL_ENABLED = bool(SMTP_USER and SMTP_PASS) or bool(SENDGRID_API_KEY)
EMAIL_PROVIDER = "sendgrid" if SENDGRID_API_KEY else "smtp" if SMTP_USER else None

# ============================================================
# SMS CONFIGURATION
# ============================================================
SMS_PROVIDER = os.getenv("SMS_PROVIDER", "").lower()

# Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_FROM") or os.getenv("TWILIO_PHONE")
TWILIO_ENABLED = bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_FROM)

# MSG91
MSG91_AUTH_KEY = os.getenv("MSG91_AUTH_KEY")
MSG91_ROUTE = os.getenv("MSG91_ROUTE", "4")
MSG91_ENABLED = bool(MSG91_AUTH_KEY)

# Generic SMS API
SMS_API_URL = os.getenv("SMS_API_URL")
SMS_API_KEY = os.getenv("SMS_API_KEY")
GENERIC_SMS_ENABLED = bool(SMS_API_URL)

# SMS settings
SMS_ENABLED = TWILIO_ENABLED or MSG91_ENABLED or GENERIC_SMS_ENABLED
if not SMS_PROVIDER and TWILIO_ENABLED:
    SMS_PROVIDER = "twilio"
elif not SMS_PROVIDER and MSG91_ENABLED:
    SMS_PROVIDER = "msg91"
elif not SMS_PROVIDER and GENERIC_SMS_ENABLED:
    SMS_PROVIDER = "generic"

# ============================================================
# NOTIFICATIONS CONFIGURATION
# ============================================================
NOTIFICATIONS_BACKGROUND = os.getenv("NOTIFICATIONS_BACKGROUND", "false").lower() in ("true", "1", "yes")
NOTIFICATIONS_MAX_RETRIES = int(os.getenv("NOTIFICATIONS_MAX_RETRIES", "3"))
NOTIFICATIONS_RETRY_DELAY = int(os.getenv("NOTIFICATIONS_RETRY_DELAY", "2"))

# ============================================================
# PDF CONFIGURATION
# ============================================================
PDF_ENABLED = os.getenv("PDF_GENERATION_ENABLED", "True").lower() in ("true", "1", "yes")

# ============================================================
# VOICE CONFIGURATION
# ============================================================
SUPPORTED_LANGUAGES = os.getenv("SUPPORTED_LANGUAGES", "en,hi,kn,te,ta,ml").split(",")
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")
VOICE_TIMEOUT = int(os.getenv("VOICE_TIMEOUT", "30"))
VOICE_SAMPLING_RATE = int(os.getenv("VOICE_SAMPLING_RATE", "16000"))

# ============================================================
# EMOTION DETECTION CONFIGURATION
# ============================================================
EMOTION_DETECTION_ENABLED = os.getenv("EMOTION_DETECTION_ENABLED", "True").lower() in ("true", "1", "yes")
EMOTION_MODEL_PATH = os.getenv("EMOTION_MODEL_PATH", str(BASE_DIR / "emotion_model.h5"))

# ============================================================
# DATABASE CONFIGURATION
# ============================================================
STORAGE_TYPE = os.getenv("STORAGE_TYPE", "json").lower()
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "dentalvoice")
USE_MONGODB = os.getenv("USE_MONGODB", "false").lower() in ("true", "1", "yes")

# ============================================================
# LOGGING CONFIGURATION
# ============================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", str(LOG_DIR / "dentalvoice.log"))
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", "10485760"))  # 10MB
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))

# ============================================================
# CLINIC INFORMATION
# ============================================================
CLINIC_NAME = os.getenv("CLINIC_NAME", "Smile Dental Clinic")
CLINIC_PHONE = os.getenv("CLINIC_PHONE", "+91-9876543210")
CLINIC_EMAIL = os.getenv("CLINIC_EMAIL", "contact@smile-clinic.com")
CLINIC_ADDRESS = os.getenv("CLINIC_ADDRESS", "123 Main Street, City, State")
CLINIC_WEBSITE = os.getenv("CLINIC_WEBSITE", "https://smile-clinic.com")
CLINIC_TIMEZONE = os.getenv("CLINIC_TIMEZONE", "Asia/Kolkata")

# ============================================================
# APPOINTMENT SETTINGS
# ============================================================
APPOINTMENT_MIN_ADVANCE_DAYS = int(os.getenv("APPOINTMENT_MIN_ADVANCE_DAYS", "0"))
APPOINTMENT_MAX_ADVANCE_DAYS = int(os.getenv("APPOINTMENT_MAX_ADVANCE_DAYS", "90"))
APPOINTMENT_MIN_DURATION = int(os.getenv("APPOINTMENT_MIN_DURATION", "15"))
APPOINTMENT_BUFFER_TIME = int(os.getenv("APPOINTMENT_BUFFER_TIME", "0"))

# Business hours (24-hour format)
CLINIC_OPENING_TIME = os.getenv("CLINIC_OPENING_TIME", "09:00")
CLINIC_CLOSING_TIME = os.getenv("CLINIC_CLOSING_TIME", "18:00")

# ============================================================
# SECURITY
# ============================================================
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "dev-secret-key-change-in-production")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "3600"))

# ============================================================
# TESTING
# ============================================================
TEST_MODE = os.getenv("TEST_MODE", "False").lower() in ("true", "1", "yes")
SEND_TEST_EMAILS = os.getenv("SEND_TEST_EMAILS", "False").lower() in ("true", "1", "yes")
SEND_TEST_SMS = os.getenv("SEND_TEST_SMS", "False").lower() in ("true", "1", "yes")

# ============================================================
# DATA FILES
# ============================================================
JSON_FILE = DATA_DIR / "appointments.json"
CSV_FILE = DATA_DIR / "appointments.csv"
SERVICES_FILE = DATA_DIR / "services.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

# ============================================================
# CONFIGURATION SUMMARY
# ============================================================

def get_config_summary():
    """Get a summary of all configuration settings"""
    return {
        "server": {
            "host": FLASK_HOST,
            "port": FLASK_PORT,
            "debug": FLASK_DEBUG
        },
        "email": {
            "enabled": EMAIL_ENABLED,
            "provider": EMAIL_PROVIDER,
            "from": EMAIL_FROM if EMAIL_FROM else "Not configured"
        },
        "sms": {
            "enabled": SMS_ENABLED,
            "provider": SMS_PROVIDER if SMS_PROVIDER else "Not configured"
        },
        "notifications": {
            "background": NOTIFICATIONS_BACKGROUND,
            "max_retries": NOTIFICATIONS_MAX_RETRIES
        },
        "storage": {
            "type": STORAGE_TYPE,
            "data_dir": str(DATA_DIR)
        },
        "voice": {
            "languages": SUPPORTED_LANGUAGES,
            "default": DEFAULT_LANGUAGE
        },
        "clinic": {
            "name": CLINIC_NAME,
            "phone": CLINIC_PHONE,
            "email": CLINIC_EMAIL,
            "timezone": CLINIC_TIMEZONE
        },
        "paths": {
            "data_dir": str(DATA_DIR),
            "log_dir": str(LOG_DIR),
            "frontend_dir": str(FRONTEND_DIR),
            "pdf_dir": str(PDF_DIR)
        }
    }

def get_status_report():
    """Get a detailed status report of all services"""
    report = {
        "timestamp": str(__import__("datetime").datetime.now().isoformat()),
        "services": {
            "email": "✅ Ready" if EMAIL_ENABLED else "⚠️ Not configured",
            "sms": "✅ Ready" if SMS_ENABLED else "⚠️ Not configured",
            "pdf": "✅ Ready" if PDF_ENABLED else "⚠️ Disabled",
            "emotion": "✅ Ready" if EMOTION_DETECTION_ENABLED else "⚠️ Disabled",
            "voice": "✅ Ready"
        },
        "directories": {
            "data": "✅ Ready" if DATA_DIR.exists() else "❌ Missing",
            "logs": "✅ Ready" if LOG_DIR.exists() else "❌ Missing",
            "frontend": "✅ Ready" if FRONTEND_DIR.exists() else "⚠️ Not found",
            "uploads": "✅ Ready" if UPLOADS_DIR.exists() else "❌ Missing"
        }
    }
    return report

if __name__ == "__main__":
    import pprint
    print("=== DENTALVOICE AI CONFIGURATION ===\n")
    print("📋 Configuration Summary:")
    pprint.pprint(get_config_summary())
    print("\n🔍 Service Status Report:")
    pprint.pprint(get_status_report())
