"""
Input Processor Module

Handles extraction, normalization, and validation of voice input for:
- Names
- Phone numbers (including spoken formats)
- Email addresses (including spoken formats like "abc at gmail dot com")
- Addresses
- Dates and times

This module addresses critical bugs in slot filling and input mapping.
"""

import re
import logging
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
from email_capture_handler import EmailCaptureHandler, EmailCaptureResult

logger = logging.getLogger(__name__)


class SpokenToWrittenConverter:
    """Converts spoken numbers/text to written format."""
    
    # Mapping of spoken words to written equivalents
    SPOKEN_WORDS = {
        'zero': '0', 'oh': '0', 'o': '0',
        'one': '1', 'won': '1',
        'two': '2', 'to': '2', 'too': '2',
        'three': '3', 'tree': '3',
        'four': '4', 'for': '4', 'fore': '4',
        'five': '5',
        'six': '6', 'sicks': '6',
        'seven': '7',
        'eight': '8', 'ate': '8',
        'nine': '9', 'niner': '9',
    }
    
    # Email domain variations in spoken format
    EMAIL_DOMAIN_MAP = {
        'gmail': 'gmail.com',
        'google mail': 'gmail.com',
        'yahoo': 'yahoo.com',
        'hotmail': 'hotmail.com',
        'outlook': 'outlook.com',
        'aol': 'aol.com',
        'rediff': 'rediffmail.com',
        'rediffmail': 'rediffmail.com',
    }
    
    @classmethod
    def convert_spoken_digit(cls, word: str) -> Optional[str]:
        """Convert a single spoken word to digit."""
        word_lower = word.lower().strip()
        return cls.SPOKEN_WORDS.get(word_lower)
    
    @classmethod
    def normalize_spoken_email(cls, email_text: str) -> str:
        """
        Normalize spoken email format to written format.
        Examples:
            "abc at gmail dot com" -> "abc@gmail.com"
            "john dot smith at yahoo dot com" -> "john.smith@yahoo.com"
        """
        if not email_text:
            return ""
        
        email = email_text.lower().strip()
        
        # Replace spoken words with symbols
        replacements = {
            ' at ': '@',
            ' dot ': '.',
            'dot': '.',
            ' at': '@',
            'at ': '@',
        }
        
        for spoken, symbol in replacements.items():
            email = email.replace(spoken, symbol)
        
        # Remove extra spaces
        email = re.sub(r'\s+', '', email)
        
        return email
    
    @classmethod
    def extract_email_domain(cls, domain_text: str) -> str:
        """
        Extract email domain from text.
        Examples: "gmail" -> "gmail.com", "yahoo" -> "yahoo.com"
        """
        domain_text = domain_text.lower().strip()
        
        # Check if it matches a known domain
        for key, value in cls.EMAIL_DOMAIN_MAP.items():
            if key in domain_text:
                return value
        
        # If not found, return as-is (might be a custom domain)
        if '.' in domain_text:
            return domain_text
        
        # Default to .com if no domain found
        return f"{domain_text}.com"


class PhoneExtractor:
    """Robust phone number extraction from spoken text."""
    
    @staticmethod
    def extract_phone(text: str) -> Optional[str]:
        """
        Extract phone number from spoken text.
        Handles:
        - Direct digits: "9876543210"
        - Spoken digits: "nine eight seven six..."
        - Grouped numbers: "98 76 54 32 10"
        - With pauses/spaces
        
        Returns 10-digit phone number or None.
        """
        if not text:
            return None
        
        text = text.lower().strip()
        
        # First, try to extract any existing digits
        direct_digits = re.findall(r'\d', text)
        
        # If we have 10 digits, use them
        if len(direct_digits) >= 10:
            phone = ''.join(direct_digits)
            # Validate Indian phone number (should start with 6-9)
            if len(phone) >= 10 and phone[-10] in '6789':
                return phone[-10:]
            return phone[-10:] if len(phone) >= 10 else None
        
        # If we have some digits, convert spoken words to digits
        words = re.findall(r'\b\w+\b', text)
        extracted_digits = []
        
        for word in words:
            if word.isdigit():
                # Direct digit
                extracted_digits.append(word)
            else:
                # Try to convert spoken word to digit
                digit = SpokenToWrittenConverter.convert_spoken_digit(word)
                if digit:
                    extracted_digits.append(digit)
        
        phone = ''.join(extracted_digits)
        
        if len(phone) >= 10:
            # Validate: Indian numbers typically start with 6-9
            if phone[-10] in '6789':
                return phone[-10:]
            return phone[-10:]
        
        return None
    
    @staticmethod
    def format_phone(phone: str) -> str:
        """Format phone number (e.g., 9876543210 -> +91-98765-43210)."""
        if not phone or len(phone) < 10:
            return phone
        
        phone = phone.strip()[-10:]  # Take last 10 digits
        return f"+91-{phone[:5]}-{phone[5:]}"


class EmailExtractor:
    """Robust email extraction from spoken text using EmailCaptureHandler."""
    
    @staticmethod
    def extract_email(text: str) -> Optional[str]:
        """
        Extract email from spoken or written text.
        Delegates to EmailCaptureHandler for robust processing.
        
        Returns email or None.
        """
        if not text:
            return None
        
        # Use the new EmailCaptureHandler
        result = EmailCaptureHandler.process_email_input(text)
        
        # Return the email if valid, None otherwise
        return result.email if result.is_valid else None
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        if not email:
            return False
        
        return EmailCaptureHandler.validate_email_format(email)


class NameExtractor:
    """Name extraction and validation."""
    
    @staticmethod
    def extract_name(text: str) -> Optional[str]:
        """
        Extract person name from text.
        Removes common question patterns and cleans up.
        """
        if not text:
            return None
        
        name = text.strip()
        
        # Remove common question patterns
        patterns_to_remove = [
            r"(tell\s+me\s+)?your\s+name",
            r"my\s+name\s+is\s+",
            r"i'm\s+",
            r"i\s+am\s+",
            r"^(my\s+)?name",
        ]
        
        for pattern in patterns_to_remove:
            name = re.sub(pattern, "", name, flags=re.IGNORECASE)
        
        name = name.strip()
        
        # Remove special characters but keep spaces and hyphens
        name = re.sub(r'[^a-zA-Z\s\-\']', '', name)
        
        # Clean up multiple spaces
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Convert to title case
        if name and len(name) > 2:
            name = ' '.join(word.capitalize() for word in name.split())
            return name
        
        return None
    
    @staticmethod
    def validate_name(name: str) -> bool:
        """Validate name (at least 2 characters, no special chars)."""
        if not name:
            return False
        
        name = name.strip()
        
        # Should be at least 2 characters
        if len(name) < 2:
            return False
        
        # Should contain mostly letters
        letter_count = sum(1 for c in name if c.isalpha())
        if letter_count < len(name) * 0.6:  # At least 60% letters
            return False
        
        return True


class AddressExtractor:
    """Address extraction and validation."""
    
    @staticmethod
    def extract_address(text: str) -> Optional[str]:
        """
        Extract address from spoken text.
        Removes common question patterns.
        """
        if not text:
            return None
        
        address = text.strip()
        
        # Remove common question patterns
        patterns_to_remove = [
            r"(tell\s+me\s+)?your\s+address",
            r"what\s+is\s+your\s+address",
            r"my\s+address\s+is\s+",
        ]
        
        for pattern in patterns_to_remove:
            address = re.sub(pattern, "", address, flags=re.IGNORECASE)
        
        address = address.strip()
        
        # Remove extra punctuation but keep commas and numbers
        address = re.sub(r'\s+', ' ', address)
        
        if len(address) > 3:
            return address
        
        return None
    
    @staticmethod
    def validate_address(address: str) -> bool:
        """Validate address (at least 5 characters)."""
        if not address:
            return False
        
        address = address.strip()
        
        # Should be at least 5 characters
        if len(address) < 5:
            return False
        
        return True


class InputValidator:
    """Validates all input fields."""
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number."""
        if not phone:
            return False
        
        digits = re.sub(r'\D', '', phone)
        
        # Should have at least 10 digits
        if len(digits) < 10:
            return False
        
        # Indian phone: should start with 6, 7, 8, or 9
        if digits[-10] not in '6789':
            return False
        
        return True
    
    @staticmethod
    def validate_email_format(email: str) -> bool:
        """Validate email format."""
        return EmailExtractor.validate_email(email)
    
    @staticmethod
    def validate_name_format(name: str) -> bool:
        """Validate name format."""
        return NameExtractor.validate_name(name)
    
    @staticmethod
    def validate_address_format(address: str) -> bool:
        """Validate address format."""
        return AddressExtractor.validate_address(address)


class InputProcessor:
    """Main processor combining all extraction and validation."""
    
    @staticmethod
    def process_name_input(text: str) -> Tuple[Optional[str], bool, str]:
        """
        Process name input.
        Returns: (name, is_valid, error_message)
        """
        name = NameExtractor.extract_name(text)
        
        if not name:
            return None, False, "Could not extract a valid name. Please try again."
        
        if not InputValidator.validate_name_format(name):
            return None, False, f"'{name}' doesn't look like a valid name. Please provide your full name."
        
        return name, True, ""
    
    @staticmethod
    def process_phone_input(text: str) -> Tuple[Optional[str], bool, str]:
        """
        Process phone input.
        Returns: (phone, is_valid, error_message)
        """
        phone = PhoneExtractor.extract_phone(text)
        
        if not phone:
            return None, False, "Could not extract a valid phone number. Please provide 10 digits."
        
        if not InputValidator.validate_phone(phone):
            return None, False, f"The phone number '{phone}' doesn't appear to be valid. Please check and try again."
        
        return phone, True, ""
    
    @staticmethod
    def process_email_input(text: str) -> Tuple[Optional[str], bool, str]:
        """
        Process email input using EmailCaptureHandler.
        Implements CRITICAL EMAIL CAPTURE RULES:
        - NEVER process an email until you hear a domain
        - If only a fragment is provided, ask for the missing part
        - Auto-replace: "at" -> "@", "dot" -> ".", remove spaces
        
        Returns: (email, is_valid, error_message)
        """
        # Check for "skip" or "not provided"
        skip_words = ['skip', 'not provided', 'none', 'na', 'नहीं', 'ಇಲ್ಲ', 'లేదు', 'स्किப']
        if any(word in text.lower() for word in skip_words):
            return 'Not provided', True, ""
        
        # Use EmailCaptureHandler for robust processing
        result = EmailCaptureHandler.process_email_input(text)
        
        if result.is_valid:
            return result.email, True, ""
        
        # Return the handler's message for user guidance
        return None, False, result.message
    
    @staticmethod
    def process_address_input(text: str) -> Tuple[Optional[str], bool, str]:
        """
        Process address input.
        Returns: (address, is_valid, error_message)
        """
        # Check for "skip" or "not provided"
        skip_words = ['skip', 'not provided', 'none', 'na', 'नहीं', 'ಇಲ್ಲ', 'లేదు', 'स्किप']
        if any(word in text.lower() for word in skip_words):
            return 'Not provided', True, ""
        
        address = AddressExtractor.extract_address(text)
        
        if not address:
            return None, False, "Could not extract a valid address. Please try again."
        
        if not InputValidator.validate_address_format(address):
            return None, False, "The address seems too short. Please provide a complete address."
        
        return address, True, ""


# Test function (run directly for testing)
if __name__ == "__main__":
    # Test cases
    print("=== Testing EmailExtractor ===")
    test_emails = [
        "abc at gmail dot com",
        "john smith at yahoo dot com",
        "abc@gmail.com",
        "john dot smith at yahoo",
    ]
    for email_str in test_emails:
        result = EmailExtractor.extract_email(email_str)
        print(f"  '{email_str}' -> {result}")
    
    print("\n=== Testing PhoneExtractor ===")
    test_phones = [
        "9876543210",
        "nine eight seven six five four three two one oh",
        "98 76 54 32 10",
    ]
    for phone_str in test_phones:
        result = PhoneExtractor.extract_phone(phone_str)
        print(f"  '{phone_str}' -> {result}")
    
    print("\n=== Testing NameExtractor ===")
    test_names = [
        "My name is John Smith",
        "I'm Rajesh Kumar",
        "Tell me your name: Priya Singh",
    ]
    for name_str in test_names:
        result = NameExtractor.extract_name(name_str)
        print(f"  '{name_str}' -> {result}")
    
    print("\n=== Testing InputProcessor ===")
    name, valid, msg = InputProcessor.process_name_input("my name is john smith")
    print(f"  Name: {name}, Valid: {valid}, Msg: {msg}")
