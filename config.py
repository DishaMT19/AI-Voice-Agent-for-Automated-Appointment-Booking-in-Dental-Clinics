# backend/config.py - Centralized configuration with environment variable support
"""
Unified configuration management for the DentalVoice AI backend.
All secrets, paths, and settings are centralized here.
Supports environment variable overrides for deployment flexibility.
"""

import os
import logging
from pathlib import Path

# ============================================================================
# PATHS & DIRECTORIES
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR
DATA_DIR = BASE_DIR / "data"
FRONTEND_DIR = BASE_DIR / "frontend"
LOGS_DIR = BASE_DIR / "logs"
VOICE_DIR = BASE_DIR / "voice"
APPOINTMENTS_DIR = DATA_DIR / "appointments"

# Ensure all directories exist
for dir_path in [DATA_DIR, LOGS_DIR, VOICE_DIR, APPOINTMENTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# ============================================================================
# FILE PATHS (DATA PERSISTENCE)
# ============================================================================

JSON_FILE = DATA_DIR / "appointments.json"
CSV_FILE = DATA_DIR / "appointments.csv"
CONVERSATIONS_FILE = DATA_DIR / "conversations.jsonl"
AUDIT_LOG = LOGS_DIR / "audit.log"

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
LOG_FILE = LOGS_DIR / "dentalvoice.log"
ERROR_LOG_FILE = LOGS_DIR / "errors.log"

# ============================================================================
# NOTIFICATION CONFIGURATION
# ============================================================================

NOTIFICATIONS_BACKGROUND = os.getenv("NOTIFICATIONS_BACKGROUND", "false").lower() in ("1", "true", "yes")
NOTIFICATIONS_RETRY_COUNT = int(os.getenv("NOTIFICATIONS_RETRY_COUNT", "3"))
NOTIFICATIONS_RETRY_DELAY = int(os.getenv("NOTIFICATIONS_RETRY_DELAY", "1"))
NOTIFICATIONS_TIMEOUT = int(os.getenv("NOTIFICATIONS_TIMEOUT", "10"))

# SMS Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_FROM")
SMS_API_URL = os.getenv("SMS_API_URL")
SMS_API_KEY = os.getenv("SMS_API_KEY")

# Email Configuration
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "0")) if os.getenv("SMTP_PORT") else None
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
EMAIL_FROM = os.getenv("EMAIL_FROM") or SMTP_USER
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")

# ============================================================================
# SPEECH RECOGNITION CONFIGURATION
# ============================================================================

STT_CONFIDENCE_THRESHOLD = float(os.getenv("STT_CONFIDENCE_THRESHOLD", "0.5"))
STT_SILENCE_DURATION = float(os.getenv("STT_SILENCE_DURATION", "1.5"))
STT_RETRY_COUNT = int(os.getenv("STT_RETRY_COUNT", "3"))
AUDIO_SAMPLE_RATE = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
AUDIO_CHUNK_SIZE = int(os.getenv("AUDIO_CHUNK_SIZE", "1024"))

# ============================================================================
# NLP & ENTITY EXTRACTION
# ============================================================================

SUPPORTED_LANGUAGES = ["en", "hi", "kn", "te", "ta", "ml", "mr"]
DEFAULT_LANGUAGE = "en"
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M"

# ============================================================================
# EMOTION DETECTION
# ============================================================================

EMOTION_MODEL_VERSION = "v2.0"
EMOTION_CONFIDENCE_THRESHOLD = float(os.getenv("EMOTION_CONFIDENCE_THRESHOLD", "0.6"))

# ============================================================================
# APPOINTMENT SETTINGS
# ============================================================================

APPOINTMENT_MIN_BUFFER_MINUTES = int(os.getenv("APPOINTMENT_MIN_BUFFER_MINUTES", "30"))
APPOINTMENT_MAX_DURATION_MINUTES = int(os.getenv("APPOINTMENT_MAX_DURATION_MINUTES", "120"))
APPOINTMENT_TIMEZONE = os.getenv("APPOINTMENT_TIMEZONE", "Asia/Kolkata")

# ============================================================================
# VALIDATION SETTINGS
# ============================================================================

PHONE_LENGTH = 10
EMAIL_REGEX_PATTERN = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
PHONE_REGEX_PATTERN = r'^\d{10}$'

# ============================================================================
# API SETTINGS
# ============================================================================

FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", "8000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "true").lower() in ("1", "true", "yes")
FLASK_WORKERS = int(os.getenv("FLASK_WORKERS", "4"))

# ============================================================================
# SERVICES CATALOGUE
# ============================================================================

SERVICES = [
    {"id": "cleaning", "name": "Teeth Cleaning", "duration_minutes": 30, "price": 800, "category": "preventive"},
    {"id": "checkup", "name": "Dental Checkup", "duration_minutes": 20, "price": 500, "category": "preventive"},
    {"id": "filling", "name": "Tooth Filling", "duration_minutes": 45, "price": 1500, "category": "restorative"},
    {"id": "root_canal", "name": "Root Canal Treatment", "duration_minutes": 90, "price": 4000, "category": "restorative"},
    {"id": "extraction", "name": "Tooth Extraction", "duration_minutes": 30, "price": 1200, "category": "surgical"},
    {"id": "braces_consult", "name": "Braces Consultation", "duration_minutes": 30, "price": 800, "category": "orthodontic"},
    {"id": "whitening", "name": "Teeth Whitening", "duration_minutes": 60, "price": 3500, "category": "cosmetic"},
    {"id": "implant_consult", "name": "Implant Consultation", "duration_minutes": 30, "price": 1000, "category": "surgical"},
    {"id": "emergency", "name": "Emergency Care", "duration_minutes": 30, "price": 2000, "category": "emergency"},
    {"id": "consultation", "name": "General Consultation", "duration_minutes": 15, "price": 300, "category": "general"},
    {"id": "crown", "name": "Dental Crown", "duration_minutes": 60, "price": 5000, "category": "restorative"},
    {"id": "bridge", "name": "Dental Bridge", "duration_minutes": 75, "price": 8000, "category": "restorative"},
    {"id": "dentures", "name": "Dentures", "duration_minutes": 90, "price": 10000, "category": "prosthodontic"},
    {"id": "gum_treatment", "name": "Gum Treatment", "duration_minutes": 45, "price": 2500, "category": "periodontal"},
    {"id": "xray", "name": "Dental X-Ray", "duration_minutes": 15, "price": 400, "category": "diagnostic"}
]

# ============================================================================
# LANGUAGE KEYWORDS (for multi-language support)
# ============================================================================

RELATIVE_DATE_KEYWORDS = {
    "today": ["today", "now", "अभी", "ಈಗ", "ఇప్పుడు", "இன்று", "ഇന്ന്", "आज"],
    "tomorrow": ["tomorrow", "tom", "कल", "ನಾಳೆ", "రేపు", "நாளை", "നാളെ", "कल"],
    "day_after": ["day after", "परसों", "ಮರುದಿನ", "పరశ్వ", "மறுநாள்", "പരസ്യം"],
}

MORNING_KEYWORDS = ["morning", "सुबह", "ಬೆಳಿಗ್ಗೆ", "ఉదయం", "காலை", "രാവിലെ", "सुबह"]
AFTERNOON_KEYWORDS = ["afternoon", "दोपहर", "ಮಧ್ಯಾಹ್ನ", "మధ్యాహ్నం", "மதியம్", "ഉച്ചയ്ക്ക്", "दोपहर"]
EVENING_KEYWORDS = ["evening", "शाम", "ಸಂಜೆ", "సాయంత్రం", "மாலை", "സന്ധ്യ", "शाम"]
NIGHT_KEYWORDS = ["night", "रात", "ರಾತ್ರಿ", "రాత్రి", "இரவு", "രാത്രി", "रात"]

# ============================================================================
# VALIDATION RULES
# ============================================================================

SKIP_WORDS = [
    "skip", "not provided", "none", "na", "नहीं", "ಇಲ್ಲ", "లేదు",
    "स्किप", "स्कैप", "skip it", "no"
]

DOMAIN_REPLACEMENTS = {
    "जीमेल": "gmail",
    "जिमेल": "gmail",
    "ಜಿಮೇಲ್": "gmail",
    "జిమెయిల్": "gmail",
    " at ": "@",
    " dot ": ".",
    " dot": ".",
    "dot ": ".",
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_logger(name: str) -> logging.Logger:
    """Get or create a logger with consistent formatting."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(LOG_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, LOG_LEVEL))
    return logger

def validate_config() -> tuple[bool, list[str]]:
    """Validate configuration on startup."""
    errors = []
    
    # Check required directories
    for dir_path in [DATA_DIR, LOGS_DIR]:
        if not dir_path.exists():
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Failed to create {dir_path}: {e}")
    
    # Warn about optional configurations
    if not TWILIO_ACCOUNT_SID:
        print("[WARNING] Twilio SMS not configured. SMS notifications will be skipped.")
    if not SMTP_HOST:
        print("[WARNING] SMTP not configured. Email notifications will be skipped.")
    
    return len(errors) == 0, errors

# Run validation on import
if __name__ != "__main__":
    success, errors = validate_config()
    if not success:
        for error in errors:
            print(f"[ERROR] {error}")
