# app.py - Complete Backend Implementation
import os
import json
import csv
import uuid
import logging
import traceback 
import re
import statistics
import smtplib
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, List
from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
from collections import Counter
from dotenv import load_dotenv
from io import BytesIO
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from email_capture_handler import EmailCaptureHandler
from voice_data_cleaner import VoiceToTextCleaner, DataValidationReport

# Load environment variables
load_dotenv()

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
JSON_FILE = os.path.join(DATA_DIR, "appointments.json")
CSV_FILE = os.path.join(DATA_DIR, "appointments.csv")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(FRONTEND_DIR, exist_ok=True)
os.makedirs(os.path.join(FRONTEND_DIR, "dashboard"), exist_ok=True)

# Initialize data files
if not os.path.exists(JSON_FILE):
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False)

if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "appointment_id", "timestamp", "confirmation_id", "patient_name",
            "patient_phone", "patient_email", "patient_address", "service",
            "date", "time", "duration_minutes", "end_time", "backend_saved",
            "lang", "emotion_data", "conversation_steps", "total_duration_seconds"
        ])

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("dentalvoice-backend")

# Flask app
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)

# Services Catalogue
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
    {"id": "consultation", "name": "General Consultation", "duration_minutes": 15, "price": 300, "category": "general"}
]

EMOTION_MODEL_VERSION = "v1.0"

# ==================== HELPER FUNCTIONS ====================
def clean_text(s: str) -> str:
    """Clean and normalize text input."""
    if not s:
        return ""
    s = str(s).strip()
    s = re.sub(r'[,\u2019\u2018\u201c\u201d]+', ' ', s)
    s = re.sub(r'(\d{1,2})(st|nd|rd|th)\b', r'\1', s, flags=re.IGNORECASE)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def extract_phone(phone: str) -> str:
    """Extract valid phone number."""
    if not phone:
        return None
    digits = ''.join(filter(str.isdigit, str(phone)))
    if len(digits) >= 10:
        phone_num = digits[-10:]
        if phone_num[0] in '6789':
            return phone_num
    return None

def validate_email(email: str) -> str:
    """
    Validate and clean email using EmailCaptureHandler.
    Implements CRITICAL EMAIL CAPTURE RULES:
    - NEVER process an email until you hear a domain
    - Auto-replace: "at" -> "@", "dot" -> ".", remove spaces
    """
    if not email:
        return 'Not provided'
    
    e = str(email).strip().lower()
    
    skip_words = ['skip', 'not provided', 'none', 'na', 'नहीं', 'ಇಲ್ಲ', 'లేదు', 'स्किप']
    if any(word in e for word in skip_words):
        return 'Not provided'
    
    # Use EmailCaptureHandler for robust processing
    result = EmailCaptureHandler.process_email_input(e)
    
    # If valid email was captured, return it
    if result.is_valid and result.email:
        return result.email
    
    # If fragment was detected, log and return 'Not provided' for now
    # (The caller should handle asking for clarification)
    if result.is_fragment:
        logger.info(f"Email fragment detected: {result.fragment_type}. Message: {result.message}")
        return 'Not provided'
    
    # Default fallback
    return 'Not provided'


def validate_and_clean_email(email: str, report: DataValidationReport = None) -> Tuple[str, Optional[str]]:
    """
    Validate and clean email with detailed error reporting.
    
    Uses VoiceToTextCleaner to detect and fix common voice-to-text errors.
    Returns (cleaned_email, error_message) where error_message is None if valid.
    """
    report = report or DataValidationReport()
    
    if not email or email == 'Not provided':
        return 'Not provided', None
    
    # Try VoiceToTextCleaner first (catches concatenated emails, malformed formats)
    is_valid, cleaned, error = VoiceToTextCleaner.validate_email_strict(email)
    
    if is_valid:
        if cleaned != email and cleaned != 'Not provided':
            report.add_fixed('email', email, cleaned)
            logger.info(f"✓ Email cleaned: {email} -> {cleaned}")
        return cleaned, None
    
    # If VoiceToTextCleaner failed, try EmailCaptureHandler as fallback
    if error:
        logger.warning(f"Email validation warning: {error}")
        report.add_warning('email', error, email)
        
        # Try EmailCaptureHandler as fallback
        try:
            result = EmailCaptureHandler.process_email_input(email.lower().strip())
            if result.is_valid and result.email:
                return result.email, None
        except Exception as e:
            logger.debug(f"EmailCaptureHandler fallback also failed: {e}")
    
    # If all validation fails, provide error
    err_msg = error or "Email format invalid"
    report.add_error('email', err_msg, email)
    return None, err_msg


def validate_and_clean_address(address: str, report: DataValidationReport = None) -> Tuple[str, Optional[str]]:
    """
    Validate and clean address with detailed error reporting.
    
    Uses VoiceToTextCleaner to fix common voice-to-text errors.
    Returns (cleaned_address, error_message) where error_message is None if valid.
    """
    report = report or DataValidationReport()
    
    if not address:
        return 'Not provided', None
    
    is_valid, cleaned, error = VoiceToTextCleaner.validate_address_strict(address)
    
    if is_valid:
        if cleaned != address:
            report.add_fixed('address', address, cleaned)
            logger.info(f"✓ Address cleaned: {address} -> {cleaned}")
        return cleaned, None
    
    # Validation failed
    err_msg = error or "Address format invalid"
    report.add_error('address', err_msg, address)
    return None, err_msg


def validate_and_clean_phone(phone: str, report: DataValidationReport = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Validate and clean phone with detailed error reporting.
    
    Uses VoiceToTextCleaner for strict validation.
    Returns (cleaned_phone, error_message) where error_message is None if valid.
    """
    report = report or DataValidationReport()
    
    if not phone:
        return None, "Phone number is required"
    
    is_valid, cleaned, error = VoiceToTextCleaner.validate_phone_strict(phone)
    
    if is_valid:
        if cleaned != phone:
            report.add_fixed('phone', phone, cleaned)
        return cleaned, None
    
    err_msg = error or "Phone format invalid"
    report.add_error('phone', err_msg, phone)
    return None, err_msg


def validate_and_clean_name(name: str, report: DataValidationReport = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Validate and clean name with detailed error reporting.
    
    Uses VoiceToTextCleaner for strict validation.
    Returns (cleaned_name, error_message) where error_message is None if valid.
    """
    report = report or DataValidationReport()
    
    if not name:
        return None, "Patient name is required"
    
    is_valid, cleaned, error = VoiceToTextCleaner.validate_name_strict(name)
    
    if is_valid:
        if cleaned != name:
            report.add_fixed('name', name, cleaned)
        return cleaned, None
    
    err_msg = error or "Name format invalid"
    report.add_error('name', err_msg, name)
    return None, err_msg

def generate_confirmation_id() -> str:
    """Generate unique confirmation ID."""
    return f"SM{datetime.now().strftime('%y%m%d')}{uuid.uuid4().hex[:4].upper()}"

def parse_date(date_str: str) -> str:
    """Parse date from text with support for multiple formats. Always returns YYYY-MM-DD."""
    today = datetime.now().date()
    current_year = today.year
    
    # Default fallback
    default_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
    
    if not date_str:
        logger.warning("No date provided. Using tomorrow as default.")
        return default_date
    
    ds = clean_text(date_str).lower().strip()
    
    # === Natural language shortcuts ===
    if any(k in ds for k in ['today', 'now', 'अभी', 'ಈಗ', 'ఇప్పుడు']):
        logger.info("Date recognized as 'today'")
        return today.strftime('%Y-%m-%d')
    
    if any(k in ds for k in ['tomorrow', 'tom', 'कल', 'ನಾಳೆ', 'రేపు']):
        logger.info("Date recognized as 'tomorrow'")
        return (today + timedelta(days=1)).strftime('%Y-%m-%d')
    
    # === Month name mappings ===\n    month_names = {\n        'january': 1, 'jan': 1,\n        'february': 2, 'feb': 2,\n        'march': 3, 'mar': 3,\n        'april': 4, 'apr': 4,\n        'may': 5,\n        'june': 6, 'jun': 6,\n        'july': 7, 'jul': 7,\n        'august': 8, 'aug': 8,\n        'september': 9, 'sep': 9, 'sept': 9,\n        'october': 10, 'oct': 10,\n        'november': 11, 'nov': 11,\n        'december': 12, 'dec': 12\n    }\n    \n    # === Remove ordinal suffixes (4th -> 4, 21st -> 21, etc.) ===\n    ds_no_ordinal = re.sub(r'(\\d+)(st|nd|rd|th)\\b', r'\\1', ds)\n    \n    # === Try: DD/MM/YYYY or MM/DD/YYYY format ===\n    date_patterns = [\n        (r'(\\d{1,2})[-/](\\d{1,2})[-/](\\d{2,4})', 'dmy_or_mdy'),  # 04/12/2025 or 12/04/2025\n        (r'(\\d{2,4})[-/](\\d{1,2})[-/](\\d{1,2})', 'ymd'),  # 2025-12-04\n    ]\n    \n    for pattern, fmt_type in date_patterns:\n        match = re.search(pattern, ds_no_ordinal)\n        if match:\n            parts = match.groups()\n            try:\n                if fmt_type == 'ymd':\n                    # YYYY-MM-DD or YYYY-DD-MM\n                    year = int(parts[0])\n                    month = int(parts[1])\n                    day = int(parts[2])\n                    if year < 100:\n                        year += 2000\n                elif fmt_type == 'dmy_or_mdy':\n                    # Ambiguous: could be DD/MM/YYYY or MM/DD/YYYY\n                    # Use logic: if first number > 12, it's DD/MM/YYYY\n                    first = int(parts[0])\n                    second = int(parts[1])\n                    year = int(parts[2])\n                    \n                    if year < 100:\n                        year += 2000 if year < 50 else 1900\n                    \n                    if first > 12:\n                        # Must be DD/MM/YYYY\n                        day, month = first, second\n                    elif second > 12:\n                        # Must be MM/DD/YYYY\n                        month, day = first, second\n                    else:\n                        # Both could be valid, assume DD/MM/YYYY (European format)\n                        day, month = first, second\n                \n                # Validate month and day\n                if 1 <= month <= 12 and 1 <= day <= 31:\n                    parsed_date = datetime(year, month, day).date()\n                    logger.info(f\"Date parsed from numbers: {parsed_date.strftime('%Y-%m-%d')}\")\n                    return parsed_date.strftime('%Y-%m-%d')\n            except:\n                logger.warning(f\"Date parsing failed for pattern: {pattern}\")\n                continue\n    \n    # === Try: \"4th December\" or \"December 4\" format ===\n    # Pattern: \"4th December\" or \"4 December\"\n    month_day_patterns = [\n        (r'(\\d{1,2})\\s+(\\w+)', 'day_month'),  # \"4 December\" or \"4th December\" (after ordinal removal)\n        (r'(\\w+)\\s+(\\d{1,2})', 'month_day'),  # \"December 4\" or \"December 4th\"\n    ]\n    \n    for pattern, fmt_type in month_day_patterns:\n        match = re.search(pattern, ds_no_ordinal)\n        if match:\n            parts = match.groups()\n            try:\n                if fmt_type == 'day_month':\n                    day = int(parts[0])\n                    month_str = parts[1].strip().lower()\n                    month = month_names.get(month_str)\n                elif fmt_type == 'month_day':\n                    month_str = parts[0].strip().lower()\n                    day = int(parts[1])\n                    month = month_names.get(month_str)\n                else:\n                    month = None\n                \n                if month and 1 <= month <= 12 and 1 <= day <= 31:\n                    # Use current year if not specified\n                    parsed_date = datetime(current_year, month, day).date()\n                    \n                    # If date is in the past, use next year\n                    if parsed_date < today:\n                        parsed_date = datetime(current_year + 1, month, day).date()\n                    \n                    logger.info(f\"Date parsed from text: {parsed_date.strftime('%Y-%m-%d')}\")\n                    return parsed_date.strftime('%Y-%m-%d')\n            except:\n                logger.warning(f\"Date parsing failed for text format: {pattern}\")\n                continue\n    \n    # === Try: Single number (day of month) ===\n    if ds_no_ordinal.isdigit():\n        try:\n            day = int(ds_no_ordinal)\n            if 1 <= day <= 31:\n                month = today.month\n                year = today.year\n                \n                # If day is in the past this month, try next month\n                if day < today.day:\n                    month += 1\n                    if month > 12:\n                        month = 1\n                        year += 1\n                \n                parsed_date = datetime(year, month, day).date()\n                logger.info(f\"Date parsed as day of month: {parsed_date.strftime('%Y-%m-%d')}\")\n                return parsed_date.strftime('%Y-%m-%d')\n        except:\n            logger.warning(f\"Failed to parse single number: {ds_no_ordinal}\")\n    \n    # === Fallback: Return tomorrow ===\n    logger.warning(f\"Could not parse date: '{date_str}'. Using tomorrow as default.\")\n    return default_date

def parse_time(time_str: str) -> str:
    """Parse time from text with clinic hours validation (09:00 AM to 08:00 PM)."""
    if not time_str:
        return "09:00 AM"  # Safe default
    
    ts = clean_text(time_str).lower()
    parsed_time = None
    
    # Natural language shortcuts
    if any(k in ts for k in ['morning', 'सुबह', 'ಬೆಳಿಗ್ಗೆ', 'ఉదయం']):
        parsed_time = "09:00 AM"
    elif any(k in ts for k in ['afternoon', 'दोपहर', 'ಮಧ್ಯಾಹ್ನ', 'మధ్యాహ్నం']):
        parsed_time = "02:00 PM"
    elif any(k in ts for k in ['evening', 'शाम', 'ಸಂಜೆ', 'సాయంత్రం']):
        parsed_time = "05:00 PM"
    elif ts.isdigit() and 1 <= int(ts) <= 24:
        hour = int(ts)
        if hour < 12:
            parsed_time = f"{hour}:00 AM"
        elif hour == 12:
            parsed_time = "12:00 PM"
        else:
            parsed_time = f"{hour-12}:00 PM"
    else:
        # Try regex patterns
        patterns = [
            r'(?P<h>\d{1,2}):(?P<m>\d{2})\s*(?P<period>am|pm)?',
            r'(?P<h>\d{1,2})\s*(?P<period>am|pm)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, ts, re.IGNORECASE)
            if match:
                hour = int(match.group('h'))
                minute = int(match.group('m')) if match.group('m') else 0
                period = (match.group('period') or '').upper()
                
                if not period:
                    if 0 <= hour <= 11:
                        period = 'AM'
                    else:
                        period = 'PM'
                        if hour > 12:
                            hour -= 12
                else:
                    if period == 'PM' and hour < 12:
                        hour += 12
                    elif period == 'AM' and hour == 12:
                        hour = 0
                
                display_hour = hour if hour <= 12 else hour - 12
                if display_hour == 0:
                    display_hour = 12
                
                parsed_time = f"{display_hour}:{minute:02d} {period}"
                break
    
    # Validate clinic hours (09:00 AM to 08:00 PM)
    if parsed_time:
        try:
            time_obj = datetime.strptime(parsed_time, "%I:%M %p")
            clinic_start = datetime.strptime("09:00 AM", "%I:%M %p")
            clinic_end = datetime.strptime("08:00 PM", "%I:%M %p")
            
            if time_obj < clinic_start:
                logger.warning(f"Time {parsed_time} before clinic opening. Using 09:00 AM")
                return "09:00 AM"
            elif time_obj > clinic_end:
                logger.warning(f"Time {parsed_time} after clinic closing. Using 08:00 PM")
                return "08:00 PM"
            
            return parsed_time
        except:
            logger.error(f"Error validating time {parsed_time}")
            return "09:00 AM"
    
    return "09:00 AM"  # Safe default

def find_service_by_name(service_name: str) -> dict:
    """Find service by name or keyword with safe default to consultation."""
    # Safe fallback to consultation
    default_service = next((s for s in SERVICES if s['id'] == 'consultation'), SERVICES[9])
    
    if not service_name:
        logger.info("No service name provided. Using default consultation.")
        return default_service
    
    s = service_name.strip().lower()
    
    # Exact match by name or ID
    for svc in SERVICES:
        if svc['name'].lower() == s or svc['id'].lower() == s:
            logger.info(f"Exact service match found: {svc['name']}")
            return svc
    
    # Keyword matching
    keywords = {
        'clean': 'cleaning',
        'check': 'checkup',
        'fill': 'filling',
        'root': 'root_canal',
        'remove': 'extraction',
        'extract': 'extraction',
        'emergency': 'emergency',
        'whiten': 'whitening',
        'implant': 'implant_consult',
        'brace': 'braces_consult',
        'consult': 'consultation',
        'general': 'consultation'
    }
    
    for keyword, service_id in keywords.items():
        if keyword in s:
            for svc in SERVICES:
                if svc['id'] == service_id:
                    logger.info(f"Service match by keyword '{keyword}': {svc['name']}")
                    return svc
    
    # If noise causes wrong match or nothing found, log and return default
    logger.warning(f"Service '{service_name}' not recognized. Using default consultation.")
    return default_service

def generate_appointment_pdf(appointment_data: dict) -> BytesIO:
    """Generate PDF appointment confirmation."""
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=0.5*inch, leftMargin=0.5*inch,
                               topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#3B82F6'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2563EB'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=8,
            leading=14
        )
        
        # Title
        elements.append(Paragraph("APPOINTMENT CONFIRMATION", title_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Clinic info
        clinic_info = """
        <b>Smile Dental Clinic</b><br/>
        Professional Dental Care Services<br/>
        <font size=9>Emergency & General Dentistry</font>
        """
        elements.append(Paragraph(clinic_info, styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Confirmation details
        patient = appointment_data.get('patient', {})
        appt = appointment_data.get('appointment', {})
        
        confirmation_id = appointment_data.get('confirmation_id', 'N/A')
        timestamp = appointment_data.get('timestamp', datetime.now().isoformat())
        
        # Section 1: Confirmation ID
        elements.append(Paragraph("CONFIRMATION DETAILS", heading_style))
        conf_data = [
            ['Confirmation ID:', confirmation_id],
            ['Booking Date:', timestamp.split('T')[0] if 'T' in timestamp else timestamp],
            ['Booking Time:', timestamp.split('T')[1][:5] if 'T' in timestamp else 'N/A'],
        ]
        conf_table = Table(conf_data, colWidths=[2*inch, 4*inch])
        conf_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E0F2FE')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        elements.append(conf_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Section 2: Patient Information
        elements.append(Paragraph("PATIENT INFORMATION", heading_style))
        patient_data = [
            ['Full Name:', patient.get('name', 'N/A')],
            ['Phone Number:', patient.get('phone', 'N/A')],
            ['Email:', patient.get('email', 'Not provided')],
            ['Address:', patient.get('address', 'N/A')],
        ]
        patient_table = Table(patient_data, colWidths=[2*inch, 4*inch])
        patient_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#DCFCE7')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(patient_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Section 3: Appointment Details
        elements.append(Paragraph("APPOINTMENT DETAILS", heading_style))
        appt_data = [
            ['Service:', appt.get('service', 'N/A')],
            ['Date:', appt.get('date', 'N/A')],
            ['Time:', appt.get('time', 'N/A')],
            ['Duration:', f"{appt.get('duration_minutes', 30)} minutes"],
            ['Estimated Cost:', f"₹{appt.get('estimated_price', 0):,.2f}"],
        ]
        appt_table = Table(appt_data, colWidths=[2*inch, 4*inch])
        appt_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#FEF3C7')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        elements.append(appt_table)
        elements.append(Spacer(1, 0.25*inch))
        
        # Important notes
        elements.append(Paragraph("IMPORTANT NOTES", heading_style))
        notes = """
        <b>• Arrival Time:</b> Please arrive 10 minutes before your appointment.<br/>
        <b>• Documents:</b> Bring valid ID and any previous dental records.<br/>
        <b>• Cancellation:</b> Cancel at least 24 hours in advance for free cancellation.<br/>
        <b>• Contact:</b> Call us immediately if you need to reschedule.<br/>
        <b>• Confirmation:</b> Your appointment is confirmed. No further confirmation needed.
        """
        elements.append(Paragraph(notes, normal_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Footer
        footer = "<i>Thank you for choosing Smile Dental Clinic. We look forward to serving you!</i>"
        elements.append(Paragraph(footer, styles['Normal']))
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer
    except Exception as e:
        logger.error(f"PDF generation error: {e}")
        return None

def send_email_with_pdf(recipient_email: str, subject: str, body: str, appointment_data: dict) -> dict:
    """Send email with PDF attachment."""
    try:
        # Get SMTP credentials from environment
        smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_user = os.getenv('EMAIL_FROM') or os.getenv('SMTP_USER') or os.getenv('EMAIL_USER')
        smtp_pass = os.getenv('SMTP_PASS') or os.getenv('EMAIL_PASSWORD') or os.getenv('EMAIL_PASS')
        
        if not smtp_user or not smtp_pass:
            logger.warning("SMTP credentials not configured in .env")
            return {
                'success': False,
                'error': 'Email service not configured',
                'message': 'Please set EMAIL_FROM and SMTP_PASS in .env file'
            }
        
        if not recipient_email or recipient_email == 'Not provided':
            return {
                'success': False,
                'error': 'Invalid recipient email',
                'message': 'Cannot send email without valid recipient address'
            }
        
        # Validate recipient email
        pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, recipient_email):
            return {
                'success': False,
                'error': 'Invalid email format',
                'message': f'Invalid recipient email: {recipient_email}'
            }
        
        # Create email message
        message = MIMEMultipart('alternative')
        message['From'] = smtp_user
        message['To'] = recipient_email
        message['Subject'] = subject
        
        # Email body
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background: linear-gradient(135deg, #3B82F6, #60A5FA); 
                                color: white; padding: 20px; border-radius: 8px; text-align: center;">
                        <h2 style="margin: 0;">Smile Dental Clinic</h2>
                        <p style="margin: 5px 0 0 0;">Appointment Confirmation</p>
                    </div>
                    
                    <div style="padding: 20px; background: #f9fafb; border-radius: 8px; margin-top: 20px;">
                        {body}
                    </div>
                    
                    <div style="margin-top: 20px; padding: 15px; background: #e0f2fe; 
                                border-left: 4px solid #3B82F6; border-radius: 4px;">
                        <p><strong>Confirmation ID:</strong> {appointment_data.get('confirmation_id', 'N/A')}</p>
                        <p><strong>Patient:</strong> {appointment_data.get('patient', {}).get('name', 'N/A')}</p>
                        <p><strong>Service:</strong> {appointment_data.get('appointment', {}).get('service', 'N/A')}</p>
                        <p><strong>Date:</strong> {appointment_data.get('appointment', {}).get('date', 'N/A')}</p>
                        <p><strong>Time:</strong> {appointment_data.get('appointment', {}).get('time', 'N/A')}</p>
                    </div>
                    
                    <div style="margin-top: 20px; text-align: center; color: #666; font-size: 12px;">
                        <p>Thank you for choosing Smile Dental Clinic!</p>
                        <p>For any queries, please contact us directly.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        message.attach(MIMEText(html_body, 'html'))
        
        # Generate and attach PDF
        pdf_buffer = generate_appointment_pdf(appointment_data)
        if pdf_buffer:
            pdf_attachment = MIMEBase('application', 'octet-stream')
            pdf_attachment.set_payload(pdf_buffer.read())
            encoders.encode_base64(pdf_attachment)
            pdf_attachment.add_header(
                'Content-Disposition',
                f'attachment; filename= "appointment_{appointment_data.get("confirmation_id", "confirmation")}.pdf"'
            )
            message.attach(pdf_attachment)
        
        # Send email
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(message)
        
        logger.info(f"Email sent successfully to {recipient_email}")
        return {
            'success': True,
            'message': f'Email sent successfully to {recipient_email}',
            'recipient': recipient_email,
            'confirmation_id': appointment_data.get('confirmation_id', 'N/A')
        }
        
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed")
        return {
            'success': False,
            'error': 'Authentication failed',
            'message': 'SMTP credentials are incorrect'
        }
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {e}")
        return {
            'success': False,
            'error': 'Email service error',
            'message': f'Failed to send email: {str(e)}'
        }
    except Exception as e:
        logger.error(f"Email error: {e}")
        return {
            'success': False,
            'error': 'Unknown error',
            'message': str(e)
        }

def analyze_emotion_stats(emotions):
    """Analyze emotion data."""
    if not emotions:
        return {
            'total': 0, 'happy': 0, 'sad': 0, 'neutral': 0,
            'happy_percent': 0, 'sad_percent': 0, 'neutral_percent': 0,
            'dominant_emotion': 'neutral'
        }
    
    stats = {'total': len(emotions), 'happy': 0, 'sad': 0, 'neutral': 0}
    
    for e in emotions:
        emo = e.get('emotion', 'neutral')
        if emo == 'happy':
            stats['happy'] += 1
        elif emo == 'sad':
            stats['sad'] += 1
        else:
            stats['neutral'] += 1
    
    if stats['total'] > 0:
        stats['happy_percent'] = round((stats['happy'] / stats['total']) * 100, 1)
        stats['sad_percent'] = round((stats['sad'] / stats['total']) * 100, 1)
        stats['neutral_percent'] = round((stats['neutral'] / stats['total']) * 100, 1)
        
        emotion_counts = [('happy', stats['happy']), ('sad', stats['sad']), ('neutral', stats['neutral'])]
        emotion_counts.sort(key=lambda x: x[1], reverse=True)
        stats['dominant_emotion'] = emotion_counts[0][0]
    
    return stats

def load_appointments():
    """Load all appointments with corruption recovery."""
    try:
        if not os.path.exists(JSON_FILE):
            logger.warning(f"JSON file not found, creating new one")
            return []
        
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            
            if not isinstance(data, list):
                logger.warning(f"JSON data not a list, converting")
                return []
            
            logger.info(f"Loaded {len(data)} appointments from JSON")
            return data
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON corruption detected: {e}. Resetting file.")
        try:
            backup_path = JSON_FILE + ".backup"
            if os.path.exists(JSON_FILE):
                os.rename(JSON_FILE, backup_path)
                logger.info(f"Corrupted file backed up")
            
            with open(JSON_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
            
            logger.info(f"JSON file recreated")
            return []
        except Exception as backup_error:
            logger.error(f"Backup/recovery failed: {backup_error}")
            return []
    
    except Exception as e:
        logger.error(f"Load error: {e}")
        return []

def save_appointments(appointments, verify=True):
    """Save appointments to file with robust error handling and verification.
    
    Args:
        appointments: List of appointment dictionaries to save
        verify: If True, verify file was written successfully before returning
    
    Returns:
        Tuple of (success: bool, error_message: str or None)
    """
    import time
    
    try:
        # Ensure appointments is a list
        if not isinstance(appointments, list):
            logger.warning(f"Appointments not a list, converting from {type(appointments)}")
            appointments = [appointments] if appointments else []
        
        # Ensure data directory exists
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # Save to file with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Write to file
                with open(JSON_FILE, "w", encoding="utf-8") as f:
                    json.dump(appointments, f, indent=2, ensure_ascii=False)
                
                # Verify the file was written
                if verify:
                    time.sleep(0.05)  # Brief delay to ensure file I/O completes
                    if not os.path.exists(JSON_FILE) or os.path.getsize(JSON_FILE) == 0:
                        raise IOError("File write verification failed - file is empty or doesn't exist")
                    
                    # Verify we can read it back
                    with open(JSON_FILE, "r", encoding="utf-8") as f:
                        verify_data = json.load(f)
                        if not isinstance(verify_data, list) or len(verify_data) != len(appointments):
                            raise IOError(f"Verification failed - expected {len(appointments)} appointments, got {len(verify_data)}")
                
                logger.info(f"✓ Appointments persisted to disk ({len(appointments)} total, attempt {attempt + 1}/{max_retries})")
                return True, None
            
            except IOError as io_err:
                if attempt < max_retries - 1:
                    logger.warning(f"Write attempt {attempt + 1}/{max_retries} failed: {io_err}. Retrying...")
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                else:
                    raise io_err
    
    except Exception as e:
        error_msg = f"Failed to save appointments after retries: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def check_time_conflict(new_date, new_time, duration_minutes):
    """Check for appointment conflicts."""
    appointments = load_appointments()
    
    try:
        new_start = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %I:%M %p")
        new_end = new_start + timedelta(minutes=duration_minutes)
        
        for appt in appointments:
            appt_date = appt.get('appointment', {}).get('date')
            appt_time = appt.get('appointment', {}).get('time')
            appt_duration = appt.get('appointment', {}).get('duration_minutes', 30)
            
            if appt_date and appt_time:
                try:
                    existing_start = datetime.strptime(f"{appt_date} {appt_time}", "%Y-%m-%d %I:%M %p")
                    existing_end = existing_start + timedelta(minutes=appt_duration)
                    
                    if new_start < existing_end and new_end > existing_start:
                        return {
                            'conflict': True,
                            'existing_patient': appt.get('patient', {}).get('name', 'Another patient'),
                            'existing_time': appt_time,
                            'existing_date': appt_date
                        }
                except:
                    continue
    except:
        pass
    
    return {'conflict': False}

# ==================== ROUTES ====================
@app.route("/")
def index():
    """Serve main frontend."""
    return send_file(os.path.join(FRONTEND_DIR, "index.html"))

@app.route("/dashboard")
def dashboard():
    """Serve dashboard."""
    return send_file(os.path.join(FRONTEND_DIR, "dashboard", "index1.html"))

@app.route("/<path:path>")
def serve_static(path):
    """Serve static files."""
    return send_from_directory(FRONTEND_DIR, path)

@app.route("/health")
def health():
    """Health check."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "services": len(SERVICES)
    })

@app.route("/api/services", methods=["GET"])
def api_services():
    """Get services."""
    return jsonify({
        "services": SERVICES,
        "count": len(SERVICES)
    })

@app.route("/api/appointments", methods=["GET"])
def api_get_appointments():
    """Get all appointments sorted by date DESC (most recent first)."""
    try:
        appointments = load_appointments()
        
        status = request.args.get('status')
        service = request.args.get('service')
        date = request.args.get('date')
        
        filtered = appointments
        
        if status:
            filtered = [a for a in filtered if a.get('status', 'confirmed').lower() == status.lower()]
        
        if service:
            filtered = [a for a in filtered if service.lower() in (a.get('appointment', {}).get('service', '')).lower()]
        
        if date:
            filtered = [a for a in filtered if a.get('appointment', {}).get('date') == date]
        
        # ✅ CRITICAL FIX: Sort by timestamp DESC (newest first)
        sorted_appointments = sorted(filtered, key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Add cache-busting headers
        response = jsonify(sorted_appointments)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
    except Exception as e:
        logger.error(f"Error getting appointments: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/save-appointment", methods=["POST"])
def api_save_appointment():
    """Save new appointment with comprehensive validation and error reporting."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        logger.info(f"Received appointment data with keys: {data.keys()}")
        
        # Create validation report to track all cleaning operations
        report = DataValidationReport()
        
        # Extract data with safe defaults
        patient = data.get('patient', {})
        appointment = data.get('appointment', {})
        emotions = data.get('emotions', [])
        lang = data.get('lang', 'en')
        conversation_history = data.get('conversationHistory', [])
        
        # === VALIDATE AND CLEAN PATIENT INFO ===
        logger.info("\n" + "="*60)
        logger.info("VALIDATING AND CLEANING PATIENT DATA")
        logger.info("="*60)
        
        # Validate name (REQUIRED)
        patient_name, name_error = validate_and_clean_name(
            patient.get('name', ''), report
        )
        if name_error:
            logger.error(f"❌ Name validation failed: {name_error}")
            return jsonify({
                "success": False,
                "error": name_error,
                "field": "name",
                "validation_report": report.to_dict() if report else None
            }), 400
        
        # Validate phone (REQUIRED)
        patient_phone, phone_error = validate_and_clean_phone(
            patient.get('phone', ''), report
        )
        if phone_error:
            logger.error(f"❌ Phone validation failed: {phone_error}")
            return jsonify({
                "success": False,
                "error": phone_error,
                "field": "phone",
                "validation_report": report.to_dict() if report else None
            }), 400
        
        # Validate email (OPTIONAL but cleaned if provided)
        patient_email, email_error = validate_and_clean_email(
            patient.get('email', ''), report
        )
        if email_error:
            logger.warning(f"⚠ Email validation warning: {email_error}")
            # For optional fields, log warning but don't reject
            patient_email = 'Not provided'
        
        # Validate address (OPTIONAL but cleaned if provided)
        patient_address, address_error = validate_and_clean_address(
            patient.get('address', ''), report
        )
        if address_error:
            logger.warning(f"⚠ Address validation warning: {address_error}")
            # For optional fields, log warning but don't reject
            patient_address = 'Not provided'
        
        # Log validation results
        report.log_summary()
        
        # Update patient dictionary with cleaned values
        patient['name'] = patient_name
        patient['phone'] = patient_phone
        patient['email'] = patient_email
        patient['address'] = patient_address
        
        # === VALIDATE APPOINTMENT INFO ===
        parsed_date = parse_date(appointment.get('date', '')) or (datetime.now().date() + timedelta(days=1)).strftime('%Y-%m-%d')
        parsed_time = parse_time(appointment.get('time', '')) or "09:00 AM"
        
        logger.info(f"✓ Parsed date: {parsed_date}, time: {parsed_time}")
        
        # Determine service with safe default
        service_name = appointment.get('service', '')
        service_obj = find_service_by_name(service_name)
        duration_minutes = service_obj.get('duration_minutes', 30)
        
        appointment['service'] = service_obj.get('name')
        appointment['service_id'] = service_obj.get('id')
        appointment['date'] = parsed_date
        appointment['time'] = parsed_time
        appointment['duration_minutes'] = duration_minutes
        appointment['duration'] = f"{duration_minutes} minutes"
        appointment['estimated_price'] = service_obj.get('price', 300)
        appointment['service_category'] = service_obj.get('category', 'general')
        
        logger.info(f"✓ Service selected: {appointment['service']} (ID: {appointment['service_id']})")
        
        # Check for conflicts (log only, don't reject for demo)
        conflict = check_time_conflict(parsed_date, parsed_time, duration_minutes)
        if conflict['conflict']:
            logger.warning(f"⚠ Time conflict with {conflict['existing_patient']} at {conflict['existing_time']} - ALLOWING FOR DEMO")
        
        # Create appointment entry
        appointment_id = str(uuid.uuid4())
        confirmation_id = generate_confirmation_id()
        timestamp = datetime.now().isoformat()
        emotion_stats = analyze_emotion_stats(emotions)
        
        entry = {
            "appointment_id": appointment_id,
            "confirmation_id": confirmation_id,
            "timestamp": timestamp,
            "patient": patient,
            "appointment": appointment,
            "lang": lang,
            "emotions": emotions,
            "emotion_stats": emotion_stats,
            "conversation_history": conversation_history,
            "conversation_steps": len(conversation_history),
            "total_duration_seconds": data.get('totalDuration', 0),
            "backend_saved": False,  # Will be set to True after successful save
            "status": "confirmed",
            "original_date_input": appointment.get('date', ''),
            "original_time_input": appointment.get('time', ''),
            "validation_report": report.to_dict()  # Attach validation report for debugging
        }
        
        # === PERSIST TO DISK - MANDATORY ===
        save_success = False
        save_error = None
        
        try:
            logger.info(f"[SAVE] Loading current appointments from disk...")
            appointments = load_appointments()
            
            # Ensure list type
            if not isinstance(appointments, list):
                logger.warning(f"Appointments list corrupted, initializing fresh")
                appointments = []
            
            # Append new appointment
            appointments.append(entry)
            logger.info(f"[SAVE] Appointment added to list (total: {len(appointments)})")
            
            # Save with verification and retry logic
            logger.info(f"[SAVE] Writing {len(appointments)} appointments to {JSON_FILE}...")
            success, error_msg = save_appointments(appointments, verify=True)
            
            if success:
                entry["backend_saved"] = True
                save_success = True
                logger.info(f"✓ [SAVE SUCCESS] Appointment {confirmation_id} persisted permanently to disk")
            else:
                # If save failed, return error and DO NOT proceed
                error_msg = error_msg or "Unknown save error"
                logger.error(f"✗ [SAVE FAILED] {error_msg}")
                save_error = error_msg
                entry["backend_saved"] = False
                # Re-raise to return error status to client
                return jsonify({
                    "success": False,
                    "error": f"Failed to save appointment to persistent storage: {error_msg}",
                    "field": "backend_save",
                    "confirmation_id": confirmation_id
                }), 500
        
        except Exception as e:
            save_error = str(e)
            logger.error(f"[SAVE EXCEPTION] {e}")
            entry["backend_saved"] = False
            return jsonify({
                "success": False,
                "error": f"Exception while saving appointment: {save_error}",
                "field": "backend_save"
            }), 500
        
        # === CSV SAVE (non-critical) ===
        csv_saved = False
        try:
            if os.path.exists(CSV_FILE):
                with open(CSV_FILE, "a", newline='', encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        appointment_id, timestamp, confirmation_id,
                        patient.get('name'), patient.get('phone'),
                        patient.get('email'), patient.get('address'),
                        appointment.get('service'), appointment.get('date'),
                        appointment.get('time'), duration_minutes,
                        '', save_success, lang, json.dumps(emotions, ensure_ascii=False),
                        len(conversation_history), data.get('totalDuration', 0)
                    ])
                csv_saved = True
                logger.info(f"✓ CSV saved for {confirmation_id}")
        except Exception as e:
            logger.warning(f"CSV save skipped (non-critical): {e}")
        
        # === LOG FINAL RESULT ===
        logger.info(f"\n{'='*60}")
        logger.info(f"✓ APPOINTMENT CONFIRMED: {confirmation_id}")
        logger.info(f"  Patient: {patient['name']}")
        logger.info(f"  Phone: {patient['phone']}")
        logger.info(f"  Email: {patient['email']}")
        logger.info(f"  Address: {patient['address']}")
        logger.info(f"  Service: {appointment['service']}")
        logger.info(f"  Date/Time: {appointment['date']} {appointment['time']}")
        logger.info(f"  PERSISTED TO DISK: {save_success} | CSV Saved: {csv_saved}")
        logger.info(f"  Data Cleaning Report: {len(report.fixed_fields)} fields fixed, {len(report.warnings)} warnings")
        logger.info(f"{'='*60}\n")
        
        # === RETURN SUCCESS RESPONSE ===
        return jsonify({
            "success": True,
            "appointment_id": appointment_id,
            "confirmation_id": confirmation_id,
            "message": "Appointment confirmed and permanently saved",
            "persisted": save_success,
            "validation_report": report.to_dict(),
            "details": {
                "patient_name": patient['name'],
                "patient_phone": patient['phone'],
                "service": appointment['service'],
                "date": appointment['date'],
                "time": appointment['time'],
                "duration_minutes": duration_minutes,
                "confirmation": confirmation_id
            }
        }), 201
        
    except Exception as e:
        logger.error(f"CRITICAL - Unexpected error in save appointment: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": "Unexpected error while saving appointment",
            "message": "Appointment could not be saved due to system error",
            "details": str(e)
        }), 500

@app.route("/api/analytics", methods=["GET"])
def api_analytics():
    """Get analytics."""
    try:
        appointments = load_appointments()
        total = len(appointments)
        
        if total == 0:
            return jsonify({
                "total_appointments": 0,
                "estimated_revenue": 0,
                "service_counts": {},
                "language_distribution": {},
                "emotion_distribution": {},
                "daily_average": 0,
                "peak_hours": {},
                "revenue_by_category": {}
            })
        
        # Calculate metrics
        revenue = 0
        service_counts = Counter()
        lang_counts = Counter()
        emotion_counts = {'happy': 0, 'sad': 0, 'neutral': 0}
        hour_counts = Counter()
        category_revenue = Counter()
        
        for appt in appointments:
            service = appt.get('appointment', {}).get('service', 'Unknown')
            service_counts[service] += 1
            
            price = appt.get('appointment', {}).get('estimated_price', 0) or 0
            revenue += price
            
            lang = appt.get('lang', 'en')
            lang_counts[lang] += 1
            
            stats = appt.get('emotion_stats', {})
            if stats:
                emotion_counts['happy'] += stats.get('happy', 0)
                emotion_counts['sad'] += stats.get('sad', 0)
                emotion_counts['neutral'] += stats.get('neutral', 0)
            
            # Count by hour
            time_str = appt.get('appointment', {}).get('time', '')
            if time_str:
                match = re.search(r'(\d{1,2}):', time_str)
                if match:
                    hour = match.group(1)
                    period = 'AM' if 'AM' in time_str.upper() else 'PM'
                    hour_counts[f"{hour}{period}"] += 1
            
            category = appt.get('appointment', {}).get('service_category', 'general')
            category_revenue[category] += price
        
        # Daily average
        dates = set()
        for appt in appointments:
            date = appt.get('appointment', {}).get('date')
            if date:
                dates.add(date)
        
        daily_avg = total / len(dates) if dates else total
        
        return jsonify({
            "total_appointments": total,
            "estimated_revenue": revenue,
            "service_counts": dict(service_counts),
            "language_distribution": dict(lang_counts),
            "emotion_distribution": emotion_counts,
            "daily_average": round(daily_avg, 1),
            "peak_hours": dict(hour_counts.most_common(5)),
            "revenue_by_category": dict(category_revenue),
            "success_rate": 100
        })
        


    except Exception as e:
        logger.error(f"Analytics error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/dashboard-data", methods=["GET"])
def api_dashboard_data():
    """Get dashboard data."""
    try:
        appointments = load_appointments()
        
        # Recent appointments (last 10)
        recent = sorted(appointments, key=lambda x: x.get('timestamp', ''), reverse=True)[:10]
        
        # Today's count
        today = datetime.now().date().isoformat()
        today_count = sum(1 for a in appointments if a.get('appointment', {}).get('date') == today)
        
        # Language distribution
        lang_dist = {}
        for a in appointments:
            lang = a.get('lang', 'en')
            lang_dist[lang] = lang_dist.get(lang, 0) + 1
        
        # Service distribution
        svc_dist = {}
        for a in appointments:
            service = a.get('appointment', {}).get('service', 'Unknown')
            svc_dist[service] = svc_dist.get(service, 0) + 1
        
        return jsonify({
            "recent_appointments": recent,
            "quick_stats": {
                "total_appointments": len(appointments),
                "appointments_today": today_count,
                "pending_confirmation": 0,
                "cancelled": 0
            },
            "language_distribution": lang_dist,
            "service_distribution": dict(sorted(svc_dist.items(), key=lambda x: x[1], reverse=True)[:10])
        })
        
    except Exception as e:
        logger.error(f"Dashboard data error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/export-csv", methods=["GET"])
def api_export_csv():
    """Export CSV."""
    try:
        if not os.path.exists(CSV_FILE):
            return jsonify({"error": "No data"}), 404
        
        return send_file(
            CSV_FILE,
            as_attachment=True,
            download_name=f"appointments-{datetime.now().strftime('%Y%m%d')}.csv"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/send-email", methods=["POST"])
def api_send_email():
    """Send appointment confirmation email with PDF."""
    try:
        data = request.get_json() or {}
        
        # Extract parameters
        recipient_email = data.get('recipient_email', '').strip()
        subject = data.get('subject', 'Appointment Confirmation - Smile Dental Clinic').strip()
        body = data.get('body', 'Your appointment has been successfully confirmed.').strip()
        confirmation_id = data.get('confirmation_id', '').strip()
        
        # Validate inputs
        if not recipient_email:
            return jsonify({
                'success': False,
                'error': 'Missing recipient email',
                'message': 'recipient_email is required'
            }), 400
        
        if not confirmation_id:
            return jsonify({
                'success': False,
                'error': 'Missing confirmation ID',
                'message': 'confirmation_id is required'
            }), 400
        
        # Find appointment by confirmation ID
        appointments = load_appointments()
        appointment_data = None
        
        for appt in appointments:
            if appt.get('confirmation_id') == confirmation_id:
                appointment_data = appt
                break
        
        if not appointment_data:
            return jsonify({
                'success': False,
                'error': 'Appointment not found',
                'message': f'No appointment found with confirmation ID: {confirmation_id}'
            }), 404
        
        # Send email with PDF
        result = send_email_with_pdf(recipient_email, subject, body, appointment_data)
        
        if result['success']:
            logger.info(f"Email sent for appointment {confirmation_id} to {recipient_email}")
            return jsonify(result), 200
        else:
            logger.warning(f"Email send failed for appointment {confirmation_id}: {result.get('error')}")
            return jsonify(result), 503 if result.get('error') == 'Email service error' else 400
        
    except Exception as e:
        logger.error(f"Email API error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error',
            'message': str(e)
        }), 500

@app.route("/api/clear-all", methods=["POST"])
def api_clear_all():
    """Clear all data (for testing)."""
    try:
        data = request.get_json() or {}
        if not data.get('confirm'):
            return jsonify({"success": False, "error": "Confirmation required"}), 400
        
        # Clear JSON
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        
        # Clear CSV (keep headers)
        with open(CSV_FILE, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "appointment_id", "timestamp", "confirmation_id", "patient_name",
                "patient_phone", "patient_email", "patient_address", "service",
                "date", "time", "duration_minutes", "end_time", "backend_saved",
                "lang", "emotion_data", "conversation_steps", "total_duration_seconds"
            ])
        
        logger.info("All data cleared")
        return jsonify({"success": True, "message": "Data cleared"})
        
    except Exception as e:
        logger.error(f"Clear error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Server error"}), 500

# ==================== START SERVER ====================
if __name__ == "__main__":
    logger.info("Starting DentalVoice AI Server on http://0.0.0.0:8000")
    logger.info(f"Data directory: {DATA_DIR}")
    logger.info(f"Frontend directory: {FRONTEND_DIR}")
    
    app.run(host="0.0.0.0", port=8000, debug=True, threaded=True)
