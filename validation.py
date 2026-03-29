# backend/validation.py - Comprehensive entity validation and normalization
"""
Validation layer for all extracted entities.
Ensures data integrity before storage and notification.
Handles normalization and error reporting.
"""

import re
from typing import Tuple, Optional, Dict, Any
from datetime import datetime, timedelta

from config import (
    PHONE_REGEX_PATTERN, EMAIL_REGEX_PATTERN, DATE_FORMAT, TIME_FORMAT,
    PHONE_LENGTH, SKIP_WORDS, DOMAIN_REPLACEMENTS, SUPPORTED_LANGUAGES,
    MORNING_KEYWORDS, AFTERNOON_KEYWORDS, EVENING_KEYWORDS, NIGHT_KEYWORDS,
    RELATIVE_DATE_KEYWORDS
)
from logging_config import logger_validation, audit_logger, log_operation

# ============================================================================
# VALIDATION RESULTS
# ============================================================================

class ValidationResult:
    """Result object for validation operations."""
    
    def __init__(self, valid: bool, value: Any = None, error: Optional[str] = None, confidence: float = 1.0):
        self.valid = valid
        self.value = value
        self.error = error
        self.confidence = confidence
    
    def __bool__(self):
        return self.valid
    
    def __repr__(self):
        return f"ValidationResult(valid={self.valid}, value={self.value}, error={self.error}, confidence={self.confidence})"

# ============================================================================
# INPUT CLEANING
# ============================================================================

def clean_input_text(text: str) -> str:
    """Normalize input text for processing."""
    if not text:
        return ""
    
    text = str(text).strip()
    # Remove smart quotes and other transcript artifacts
    text = re.sub(r'[,\u2019\u2018\u201c\u201d]+', ' ', text)
    # Remove ordinal suffixes (1st, 2nd, etc.)
    text = re.sub(r'(\d{1,2})(st|nd|rd|th)\b', r'\1', text, flags=re.IGNORECASE)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# ============================================================================
# PHONE VALIDATION
# ============================================================================

@log_operation("phone_validation")
def validate_phone(phone: str) -> ValidationResult:
    """Validate and normalize phone number."""
    if not phone:
        return ValidationResult(False, error="Phone number is required")
    
    # Extract digits
    digits = ''.join(filter(str.isdigit, str(phone)))
    
    # Check length - accept 10-12 digits
    if len(digits) < 10:
        return ValidationResult(False, error=f"Phone too short: {len(digits)} digits (need 10-12)")
    
    if len(digits) > 12:
        return ValidationResult(False, error=f"Phone too long: {len(digits)} digits (need 10-12)")
    
    # Extract last 10 digits for Indian numbers
    if len(digits) >= 10:
        phone_10 = digits[-10:]
        # First digit must be 6-9 for Indian mobile numbers
        if phone_10[0] not in '6789':
            return ValidationResult(False, error=f"Invalid phone: first digit must be 6-9, got {phone_10[0]}")
        
        logger_validation.debug("Phone validated", input=phone, output=phone_10, length=len(digits))
        audit_logger.log_validation("phone", "phone", phone, "valid", None)
        return ValidationResult(True, value=phone_10, confidence=0.95)
    
    return ValidationResult(False, error="Invalid phone format")

# ============================================================================
# EMAIL VALIDATION
# ============================================================================

@log_operation("email_validation")
def validate_email(email: str) -> ValidationResult:
    """Validate and normalize email address."""
    if not email:
        return ValidationResult(True, value="Not provided", confidence=0.5)
    
    email_str = str(email).strip().lower()
    
    # Check for skip words
    for skip_word in SKIP_WORDS:
        if skip_word in email_str:
            logger_validation.debug("Email skip word detected", value=email_str, skip_word=skip_word)
            return ValidationResult(True, value="Not provided", confidence=0.5)
    
    # Apply domain replacements
    for old, new in DOMAIN_REPLACEMENTS.items():
        email_str = email_str.replace(old, new)
    
    # Handle missing @ symbol
    if '@' not in email_str:
        domains = {
            'gmail': 'gmail.com',
            'yahoo': 'yahoo.com',
            'outlook': 'outlook.com',
            'hotmail': 'hotmail.com'
        }
        
        for domain_key, domain_full in domains.items():
            if domain_key in email_str:
                # Extract username
                username = email_str.replace(domain_key, '').replace('.com', '').replace('@', '').strip()
                if username:
                    email_str = f"{username}@{domain_full}"
                    break
    
    # Validate email pattern
    if re.match(EMAIL_REGEX_PATTERN, email_str):
        logger_validation.debug("Email validated", input=email, output=email_str)
        audit_logger.log_validation("email", "email", email, "valid", None)
        return ValidationResult(True, value=email_str, confidence=0.9)
    
    # Log failed validation
    logger_validation.warning("Email validation failed", input=email, pattern=EMAIL_REGEX_PATTERN)
    audit_logger.log_validation("email", "email", email, "invalid", "Pattern match failed")
    return ValidationResult(False, error=f"Invalid email format: {email_str}")

# ============================================================================
# DATE VALIDATION
# ============================================================================

@log_operation("date_validation")
def validate_date(date_str: str) -> ValidationResult:
    """Validate and normalize date string."""
    if not date_str:
        return ValidationResult(False, error="Date is required")
    
    cleaned = clean_input_text(date_str).lower().strip()
    today = datetime.now().date()
    
    # Check relative keywords
    for keyword_type, keywords in RELATIVE_DATE_KEYWORDS.items():
        if any(k in cleaned for k in keywords):
            if keyword_type == "today":
                return ValidationResult(True, value=today.strftime(DATE_FORMAT), confidence=0.95)
            elif keyword_type == "tomorrow":
                return ValidationResult(True, value=(today + timedelta(days=1)).strftime(DATE_FORMAT), confidence=0.95)
            elif keyword_type == "day_after":
                return ValidationResult(True, value=(today + timedelta(days=2)).strftime(DATE_FORMAT), confidence=0.95)
    
    # Try standard date patterns
    patterns = [
        (r'(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})', 'dmy'),
        (r'(\d{2,4})[-/](\d{1,2})[-/](\d{1,2})', 'ymd'),
    ]
    
    for pattern, format_type in patterns:
        match = re.search(pattern, cleaned)
        if match:
            parts = match.groups()
            try:
                if format_type == 'dmy':
                    day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                    if len(parts[2]) < 4:
                        year += 2000 if year < 50 else 1900
                else:  # ymd
                    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                    if len(parts[0]) < 4:
                        year += 2000 if year < 50 else 1900
                
                # Validate date
                parsed_date = datetime(year, month, day).date()
                formatted = parsed_date.strftime(DATE_FORMAT)
                
                logger_validation.debug("Date validated", input=date_str, output=formatted)
                audit_logger.log_validation("date", "date", date_str, "valid", None)
                return ValidationResult(True, value=formatted, confidence=0.95)
            
            except ValueError:
                continue
    
    # Try day-only extraction
    num_match = re.search(r'\b(\d{1,2})\b', cleaned)
    if num_match:
        try:
            day = int(num_match.group(1))
            if 1 <= day <= 31:
                month = today.month
                year = today.year
                # If day < today, assume next month
                if day < today.day and month == today.month:
                    month += 1
                    if month > 12:
                        month = 1
                        year += 1
                
                parsed_date = datetime(year, month, day).date()
                formatted = parsed_date.strftime(DATE_FORMAT)
                
                logger_validation.debug("Date validated (day only)", input=date_str, output=formatted)
                return ValidationResult(True, value=formatted, confidence=0.8)
        except ValueError:
            pass
    
    logger_validation.warning("Date validation failed", input=date_str)
    return ValidationResult(False, error=f"Could not parse date: {date_str}")

# ============================================================================
# TIME VALIDATION
# ============================================================================

@log_operation("time_validation")
def validate_time(time_str: str) -> ValidationResult:
    """Validate and normalize time string."""
    if not time_str:
        return ValidationResult(False, error="Time is required")
    
    cleaned = clean_input_text(time_str).lower()
    
    # Check relative keywords
    for keywords, default_time in [
        (MORNING_KEYWORDS, "09:00 AM"),
        (AFTERNOON_KEYWORDS, "02:00 PM"),
        (EVENING_KEYWORDS, "05:00 PM"),
        (NIGHT_KEYWORDS, "07:00 PM"),
    ]:
        if any(k in cleaned for k in keywords):
            logger_validation.debug("Time validated (keyword)", input=time_str, output=default_time)
            return ValidationResult(True, value=default_time, confidence=0.8)
    
    # Handle numeric times (e.g., "11" or "14")
    if cleaned.isdigit():
        hour = int(cleaned)
        if 1 <= hour <= 24:
            if hour < 12:
                formatted = f"{hour}:00 AM"
            elif hour == 12:
                formatted = "12:00 PM"
            else:
                formatted = f"{hour-12}:00 PM"
            return ValidationResult(True, value=formatted, confidence=0.85)
    
    # Standard time patterns
    patterns = [
        r'(?P<h>\d{1,2}):(?P<m>\d{2})\s*(?P<p>am|pm)?',
        r'(?P<h>\d{1,2})\s*(?P<p>am|pm)',
        r'(?P<h>\d{1,2})\.(?P<m>\d{2})\s*(?P<p>am|pm)?',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            try:
                hour = int(match.group('h'))
                minute = int(match.group('m')) if match.group('m') else 0
                period = (match.group('p') or '').upper()
                
                if not period:
                    period = 'AM' if hour < 12 else 'PM'
                    if hour > 12:
                        hour -= 12
                else:
                    if period == 'PM' and hour < 12:
                        hour += 12
                    elif period == 'AM' and hour == 12:
                        hour = 0
                
                # Format for display
                display_hour = hour if hour <= 12 else hour - 12
                if display_hour == 0:
                    display_hour = 12
                
                formatted = f"{display_hour}:{minute:02d} {period}"
                logger_validation.debug("Time validated", input=time_str, output=formatted)
                return ValidationResult(True, value=formatted, confidence=0.9)
            
            except Exception:
                continue
    
    logger_validation.warning("Time validation failed", input=time_str)
    return ValidationResult(False, error=f"Could not parse time: {time_str}")

# ============================================================================
# NAME VALIDATION
# ============================================================================

@log_operation("name_validation")
def validate_name(name: str) -> ValidationResult:
    """Validate and normalize patient name."""
    if not name:
        return ValidationResult(False, error="Name is required")
    
    cleaned = str(name).strip().title()
    
    if len(cleaned) < 2:
        return ValidationResult(False, error="Name too short")
    
    if len(cleaned) > 100:
        return ValidationResult(False, error="Name too long")
    
    logger_validation.debug("Name validated", input=name, output=cleaned)
    return ValidationResult(True, value=cleaned, confidence=0.95)

# ============================================================================
# LANGUAGE VALIDATION
# ============================================================================

@log_operation("language_validation")
def validate_language(lang: str) -> ValidationResult:
    """Validate language code."""
    if not lang:
        return ValidationResult(True, value="en", confidence=1.0)
    
    lang_lower = str(lang).lower().strip()
    
    if lang_lower in SUPPORTED_LANGUAGES:
        return ValidationResult(True, value=lang_lower, confidence=0.95)
    
    # Try to map common variations
    lang_mapping = {
        'english': 'en',
        'hindi': 'hi',
        'kannada': 'kn',
        'telugu': 'te',
        'tamil': 'ta',
        'malayalam': 'ml',
        'marathi': 'mr',
    }
    
    if lang_lower in lang_mapping:
        return ValidationResult(True, value=lang_mapping[lang_lower], confidence=0.9)
    
    logger_validation.warning("Language not recognized", value=lang, default="en")
    return ValidationResult(True, value="en", confidence=0.5)

# ============================================================================
# BATCH VALIDATION
# ============================================================================

def validate_patient_data(patient: Dict) -> Tuple[bool, Dict[str, ValidationResult]]:
    """Validate entire patient record."""
    results = {
        'name': validate_name(patient.get('name', '')),
        'phone': validate_phone(patient.get('phone', '')),
        'email': validate_email(patient.get('email', '')),
    }
    
    all_valid = all(r.valid for r in results.values() if results.get(r))
    return all_valid, results

def validate_appointment_data(appointment: Dict) -> Tuple[bool, Dict[str, ValidationResult]]:
    """Validate entire appointment record."""
    results = {
        'date': validate_date(appointment.get('date', '')),
        'time': validate_time(appointment.get('time', '')),
    }
    
    all_valid = all(r.valid for r in results.values())
    return all_valid, results
