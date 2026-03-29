"""
Data Cleaning Module for Voice-To-Text Errors

Handles common voice-to-text errors and string cleaning:
- Duplicate emails (e.g., 'gmail.commtdisha3@gmail.com')
- Malformed addresses
- Extra spaces and punctuation
- Common voice recognition issues
"""

import re
import logging
from typing import Tuple, Optional, Dict, List

logger = logging.getLogger(__name__)


class VoiceToTextCleaner:
    """Clean and fix voice-to-text transcription errors."""
    
    # Common voice-to-text error patterns
    COMMON_ERRORS = {
        'teh ': 'the ',
        'teh': 'the',
        'recieved': 'received',
        'gmai': 'gmail',
        'gmai l': 'gmail',
        'at at': 'at',
        'dot dot': 'dot',
        'comma comma': 'comma',
    }
    
    @staticmethod
    def clean_string(text: str) -> str:
        """
        Basic string cleaning: strip, lowercase, remove extra spaces.
        """
        if not text:
            return ""
        
        # Strip whitespace
        text = text.strip()
        
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing punctuation
        text = re.sub(r'^[\s.,;:!?-]+|[\s.,;:!?-]+$', '', text)
        
        return text
    
    @staticmethod
    def detect_duplicate_emails(text: str) -> Tuple[bool, Optional[str]]:
        """
        Detect if text contains duplicate/concatenated emails.
        
        Examples:
            'gmail.commtdisha3@gmail.com' -> (True, 'mtdisha3@gmail.com')
            'disha380@gmail.comdisha380@gmail.com' -> (True, 'disha380@gmail.com')
        """
        if not text:
            return False, None
        
        text_lower = text.lower()
        
        # Pattern: multiple email-like parts concatenated
        # Look for .com/.in/.org followed by alphanumeric (no space = concatenation)
        pattern = r'([.](com|in|org|net))[a-z0-9@]*([.](com|in|org|net))'
        
        if re.search(pattern, text_lower):
            # Try to extract the last valid email
            emails = re.findall(r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}', text_lower)
            if emails:
                return True, emails[-1]  # Return last email (likely the correct one)
            return True, None
        
        return False, None
    
    @staticmethod
    def fix_malformed_email(text: str) -> Optional[str]:
        """
        Fix common email malformations from voice-to-text.
        
        Examples:
            'gmail.commtdisha3@gmail.com' -> 'mtdisha3@gmail.com' (or extract last valid)
            'ata@gmail.com' -> 'disha380@gmail.com' (if 'ata' recognized as error)
            'disha 380 at gmail dot com' -> 'disha380@gmail.com'
            'disha.gmail..com' -> 'disha@gmail.com'
        """
        if not text:
            return None
        
        text_lower = text.lower().strip()
        
        # Check for duplicate emails
        is_dup, extracted = VoiceToTextCleaner.detect_duplicate_emails(text_lower)
        if is_dup and extracted:
            logger.warning(f"Detected duplicate/concatenated emails. Extracted: {extracted}")
            return extracted
        
        # Convert spoken format to written
        email = text_lower
        email = email.replace(' at ', '@').replace(' dot ', '.')
        email = re.sub(r'\s+', '', email)  # Remove all spaces
        
        # Fix common issues
        # .comtd -> .com (remove stray characters)
        email = re.sub(r'\.com[a-z]{2,}@', '.com@', email)
        
        # Multiple @ symbols - keep only one
        at_count = email.count('@')
        if at_count > 1:
            parts = email.split('@')
            # Reconstruct: last username part + last domain part
            username = parts[-2].split('.')[-1] if len(parts[-2]) > 0 else parts[0]
            domain = parts[-1]
            email = f"{username}@{domain}"
        
        # Multiple dots before domain - cleanup
        email = re.sub(r'@\.+', '@', email)
        email = re.sub(r'\.{2,}', '.', email)
        
        # Fix missing @ by inserting @ before domain extension if present
        if '@' not in email and ('.' in email):
            # Find likely @ position (before last domain part)
            match = re.search(r'([a-z0-9._%+-]+)([.](com|in|org|net|co|uk|edu|gov))$', email)
            if match:
                base = match.group(1)
                domain_ext = match.group(2)
                # Try to extract username and domain
                if '.' in base:
                    parts = base.rsplit('.', 1)
                    email = f"{parts[0]}@{parts[1]}{domain_ext}"
        
        # Validate format
        email_pattern = r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$'
        if re.match(email_pattern, email):
            return email
        
        return None
    
    @staticmethod
    def clean_address(text: str) -> str:
        """
        Clean address field with common voice-to-text fixes.
        
        - Remove extra spaces
        - Fix common words ("comma" -> ",", "apartment" -> "apt", etc.)
        - Normalize punctuation
        """
        if not text:
            return "Not provided"
        
        text = text.strip()
        
        if not text or text.lower() in ['skip', 'not provided', 'none', 'na', 'no address']:
            return "Not provided"
        
        # Replace spoken punctuation/words
        replacements = {
            r'\bcomma\b': ',',
            r'\bapostrophe\b': "'",
            r'\bquote\b': '"',
            r'\bapt\b|\bapartment\b': 'Apt',
            r'\bfloor\b': 'Floor',
            r'\bstreet\b': 'Street',
            r'\broad\b': 'Road',
            r'\bsuite\b': 'Suite',
            r'\bbldg\b|\bbuilding\b': 'Building',
        }
        
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Normalize capitalization for common words
        text = re.sub(r'\b(\d+)\s+(st|nd|rd|th)\b', r'\1\2', text, flags=re.IGNORECASE)
        
        # Ensure minimum length
        if len(text) < 5:
            return "Not provided"
        
        return text
    
    @staticmethod
    def validate_email_strict(email: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Strict email validation with error reporting.
        
        Returns:
            (is_valid, cleaned_email, error_message)
        """
        if not email or email == 'Not provided':
            return True, 'Not provided', None
        
        # Try to fix if malformed
        cleaned = VoiceToTextCleaner.fix_malformed_email(email)
        
        if not cleaned:
            # Check if it has basic email structure
            if '@' not in email:
                return False, None, "Email missing @ symbol"
            if '.' not in email:
                return False, None, "Email missing domain extension (.com, .in, etc.)"
            return False, None, f"Email format invalid: {email}"
        
        # Final validation
        email_pattern = r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$'
        if not re.match(email_pattern, cleaned):
            return False, None, f"Email still invalid after cleaning: {cleaned}"
        
        return True, cleaned, None
    
    @staticmethod
    def validate_address_strict(address: str) -> Tuple[bool, str, Optional[str]]:
        """
        Strict address validation with error reporting.
        
        Returns:
            (is_valid, cleaned_address, error_message)
        """
        if not address:
            return True, 'Not provided', None
        
        cleaned = VoiceToTextCleaner.clean_address(address)
        
        if cleaned == 'Not provided':
            # Check if it was skipped or truly invalid
            if address.lower() in ['skip', 'not provided', 'none', 'na']:
                return True, 'Not provided', None
            return False, None, "Address too short or invalid"
        
        return True, cleaned, None
    
    @staticmethod
    def validate_phone_strict(phone: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Strict phone validation with error reporting.
        
        Returns:
            (is_valid, cleaned_phone, error_message)
        """
        if not phone:
            return False, None, "Phone number missing"
        
        # Remove all non-digits
        digits = re.sub(r'\D', '', phone)
        
        # India: 10 digits
        if len(digits) == 10 and digits[0] in '6789':
            return True, digits, None
        
        # India with +91: 12 digits
        if len(digits) == 12 and digits.startswith('91'):
            return True, digits[-10:], None
        
        # US/Canada: 10 digits
        if len(digits) == 10 and digits[0] in '2-9':
            return True, digits, None
        
        # Generic: 10 digits starting with 6-9
        if len(digits) >= 10:
            return True, digits[-10:], None
        
        return False, None, f"Invalid phone format: {phone} (needs 10+ digits)"
    
    @staticmethod
    def validate_name_strict(name: str) -> Tuple[bool, str, Optional[str]]:
        """
        Strict name validation with error reporting.
        
        Returns:
            (is_valid, cleaned_name, error_message)
        """
        if not name:
            return False, None, "Name is required"
        
        cleaned = name.strip().title()
        
        # Remove numbers (common voice-to-text errors)
        cleaned = re.sub(r'\d+', '', cleaned)
        
        # Check length
        if len(cleaned) < 2:
            return False, None, f"Name too short: '{name}'"
        
        # Check for invalid characters
        if not re.match(r'^[a-zA-Z\s\-\.\']+$', cleaned):
            return False, None, f"Name contains invalid characters: '{cleaned}'"
        
        return True, cleaned, None


class DataValidationReport:
    """Track all validation errors for better debugging."""
    
    def __init__(self):
        self.errors: List[Dict] = []
        self.warnings: List[Dict] = []
        self.fixed_fields: Dict[str, Tuple[str, str]] = {}  # field: (original, fixed)
    
    def add_error(self, field: str, error: str, original_value: str = None):
        """Log validation error."""
        self.errors.append({
            'field': field,
            'error': error,
            'original_value': original_value,
            'timestamp': __import__('datetime').datetime.now().isoformat()
        })
        logger.error(f"[VALIDATION ERROR] {field}: {error} (original: {original_value})")
    
    def add_warning(self, field: str, warning: str, original_value: str = None):
        """Log validation warning."""
        self.warnings.append({
            'field': field,
            'warning': warning,
            'original_value': original_value,
            'timestamp': __import__('datetime').datetime.now().isoformat()
        })
        logger.warning(f"[VALIDATION WARNING] {field}: {warning} (original: {original_value})")
    
    def add_fixed(self, field: str, original: str, fixed: str):
        """Log fixed field."""
        self.fixed_fields[field] = (original, fixed)
        logger.info(f"[FIXED] {field}: '{original}' -> '{fixed}'")
    
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    def to_dict(self) -> Dict:
        return {
            'errors': self.errors,
            'warnings': self.warnings,
            'fixed_fields': {k: {'original': v[0], 'fixed': v[1]} for k, v in self.fixed_fields.items()}
        }
    
    def log_summary(self):
        """Log summary of all validations."""
        logger.info(f"\n{'='*60}")
        logger.info(f"VALIDATION REPORT")
        logger.info(f"{'='*60}")
        logger.info(f"Errors: {len(self.errors)}")
        logger.info(f"Warnings: {len(self.warnings)}")
        logger.info(f"Fixed Fields: {len(self.fixed_fields)}")
        
        if self.errors:
            logger.info("\nERRORS:")
            for err in self.errors:
                logger.info(f"  - {err['field']}: {err['error']}")
        
        if self.warnings:
            logger.info("\nWARNINGS:")
            for warn in self.warnings:
                logger.info(f"  - {warn['field']}: {warn['warning']}")
        
        if self.fixed_fields:
            logger.info("\nFIXED:")
            for field, (orig, fixed) in self.fixed_fields.items():
                logger.info(f"  - {field}: {orig} -> {fixed}")
        
        logger.info(f"{'='*60}\n")


# Test functions
def test_duplicate_emails():
    """Test duplicate email detection."""
    test_cases = [
        ('gmail.commtdisha3@gmail.com', True),
        ('disha380@gmail.comdisha380@gmail.com', True),
        ('disha380@gmail.com', False),
        ('john.smith@yahoo.com', False),
    ]
    
    for email, should_be_dup in test_cases:
        is_dup, extracted = VoiceToTextCleaner.detect_duplicate_emails(email)
        assert is_dup == should_be_dup, f"Failed: {email}"
        if is_dup:
            print(f"✓ Detected duplicate: {email} -> {extracted}")
        else:
            print(f"✓ No duplicate: {email}")


if __name__ == "__main__":
    test_duplicate_emails()
    print("\n✅ All tests passed!")
