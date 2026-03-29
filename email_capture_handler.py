"""
Email Capture Handler - Implements EMAIL CAPTURE RULES for voice-to-text email processing.

RULES:
1. NEVER process an email until you hear a domain (e.g., "gmail", "outlook", "yahoo").
2. If only a fragment is provided (e.g., just "at gmail dot com"), ask for the username part.
3. STITCHING LOGIC: Combine email fragments if provided in pieces.
4. AUTO-REPLACE: "at" -> "@", "dot" -> ".", "slash" -> "/", remove all spaces.
"""

import re
from typing import Tuple, Optional, Dict
from dataclasses import dataclass


@dataclass
class EmailCaptureResult:
    """Result of email capture attempt."""
    is_valid: bool
    email: Optional[str] = None
    is_fragment: bool = False  # Only part of an email
    fragment_type: Optional[str] = None  # 'domain_only', 'username_only', etc.
    message: str = ""  # User-facing message
    domain_found: Optional[str] = None  # Domain that was detected
    username_provided: Optional[str] = None  # Username that was detected


class EmailCaptureHandler:
    """Handle email capture from voice transcription with validation rules."""
    
    # Known email domains
    KNOWN_DOMAINS = {
        'gmail': 'gmail.com',
        'yahoo': 'yahoo.com',
        'outlook': 'outlook.com',
        'hotmail': 'hotmail.com',
        'aol': 'aol.com',
        'rediff': 'rediff.com',
        'mail': 'mail.com',
        'protonmail': 'protonmail.com',
        'icloud': 'icloud.com',
        'ymail': 'ymail.com',
        'rocketmail': 'rocketmail.com'
    }
    
    @staticmethod
    def clean_voice_text(text: str) -> str:
        """
        Clean voice transcription by converting spoken words to symbols.
        
        AUTO-REPLACE RULES:
        - "at" -> "@"
        - "dot" -> "."
        - "slash" -> "/"
        - Remove all spaces
        """
        if not text:
            return ""
        
        text = text.lower().strip()
        
        # Replace spoken words with symbols
        replacements = {
            ' at ': '@',
            ' at': '@',
            'at ': '@',
            ' dot ': '.',
            ' dot': '.',
            'dot ': '.',
            ' slash ': '/',
            ' slash': '/',
            'slash ': '/',
        }
        
        for spoken, symbol in replacements.items():
            text = text.replace(spoken, symbol)
        
        # Remove all remaining spaces
        text = re.sub(r'\s+', '', text)
        
        return text
    
    @staticmethod
    def detect_domain(text: str) -> Optional[str]:
        """
        Detect if a known domain is present in the text.
        
        Returns the detected domain key (e.g., 'gmail') or None.
        """
        text_lower = text.lower()
        
        for domain_key in EmailCaptureHandler.KNOWN_DOMAINS.keys():
            if domain_key in text_lower:
                return domain_key
        
        return None
    
    @staticmethod
    def extract_username_from_domain(text: str, domain_key: str) -> Optional[str]:
        """
        Extract the username part before the domain.
        
        E.g., if text is "disha380@gmail.com" or "disha380 gmail", extract "disha380"
        """
        # Try to find username before @
        if '@' in text:
            parts = text.split('@')
            if len(parts) >= 1:
                username = parts[0].strip()
                if username:
                    return username
        
        # Try to find username before domain name
        domain_lower = domain_key.lower()
        pattern = rf'(.+?)\.?{domain_key}'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            username = match.group(1).strip()
            # Remove trailing dots or special chars
            username = re.sub(r'[._-]+$', '', username)
            if username:
                return username
        
        return None
    
    @staticmethod
    def is_fragment(text: str) -> Tuple[bool, Optional[str]]:
        """
        Determine if the text is just a fragment (incomplete email).
        
        FRAGMENT CASES:
        - Just domain: "gmail", "gmail.com"
        - Domain with @: "@gmail.com"
        - Only partial domain: "gm", "gmai"
        
        Returns: (is_fragment, fragment_type)
        """
        text = text.lower().strip()
        domain = EmailCaptureHandler.detect_domain(text)
        
        # If a domain is detected, check if there's a username part
        if domain:
            username = EmailCaptureHandler.extract_username_from_domain(text, domain)
            if not username:
                return True, 'domain_only'
        
        # Check for incomplete domain (contains @ but no valid domain)
        if '@' in text and not domain:
            parts = text.split('@')
            if len(parts) == 2:
                if parts[0].strip():  # Has username but no domain
                    return True, 'username_only'
                else:  # Only has @
                    return True, 'at_symbol_only'
        
        return False, None
    
    @staticmethod
    def stitch_email(username: str, domain_key: str) -> str:
        """Stitch username and domain together to form complete email."""
        username = username.lower().strip()
        
        if domain_key not in EmailCaptureHandler.KNOWN_DOMAINS:
            return ""
        
        full_domain = EmailCaptureHandler.KNOWN_DOMAINS[domain_key]
        return f"{username}@{full_domain}"
    
    @staticmethod
    def reconstruct_from_fragments(fragments: Dict) -> EmailCaptureResult:
        """
        Reconstruct email from previously captured fragments.
        
        EMAIL RECONSTRUCTION RULE:
        - If user provided email in fragments (e.g., "disha380" then "at gmail.com")
        - Append them together
        - DO NOT confirm until BOTH username AND domain present
        
        Args:
            fragments: Dict with keys 'username' and/or 'domain'
            
        Returns:
            EmailCaptureResult with reconstruction attempt
        """
        if not fragments:
            return EmailCaptureResult(
                is_valid=False,
                message="No email fragments to reconstruct."
            )
        
        username = fragments.get('username', '').lower().strip()
        domain = fragments.get('domain', '').lower().strip()
        
        # Check if we have both parts
        if not username:
            return EmailCaptureResult(
                is_valid=False,
                is_fragment=True,
                fragment_type='username_missing',
                domain_found=domain if domain in EmailCaptureHandler.KNOWN_DOMAINS else None,
                message=f"I have the domain '{domain}', but what is the username before the @ sign?"
            )
        
        if not domain:
            return EmailCaptureResult(
                is_valid=False,
                is_fragment=True,
                fragment_type='domain_missing',
                username_provided=username,
                message=f"I have the username '{username}', but what is the domain? (e.g., @gmail.com)"
            )
        
        # Both parts present - validate domain
        detected_domain = EmailCaptureHandler.detect_domain(domain)
        if not detected_domain:
            return EmailCaptureResult(
                is_valid=False,
                is_fragment=True,
                fragment_type='invalid_domain',
                username_provided=username,
                message=f"'{domain}' doesn't look like a valid domain. Are you sure? (e.g., gmail, yahoo, outlook)"
            )
        
        # Check username length
        if len(username) < 3:
            return EmailCaptureResult(
                is_valid=False,
                is_fragment=True,
                fragment_type='username_too_short',
                domain_found=detected_domain,
                username_provided=username,
                message=f"The username '{username}' seems too short. Could you provide a longer one?"
            )
        
        # Stitch email
        email = EmailCaptureHandler.stitch_email(username, detected_domain)
        
        if not email:
            return EmailCaptureResult(
                is_valid=False,
                message="Could not reconstruct email from fragments. Please provide again."
            )
        
        # Validate final format
        if not EmailCaptureHandler.validate_email_format(email):
            return EmailCaptureResult(
                is_valid=False,
                message=f"'{email}' doesn't look like a valid email. Please try again."
            )
        
        # SUCCESS - return stitched email
        return EmailCaptureResult(
            is_valid=True,
            email=email,
            domain_found=detected_domain,
            username_provided=username,
            message=f"I reconstructed your email as '{email}'. Is that correct?"
        )
    
    @staticmethod
    def extract_domain_from_text(text: str) -> Optional[str]:
        """
        Extract just the domain name from text.
        
        Examples:
            "gmail.com" -> "gmail"
            "at gmail dot com" -> "gmail"
            "yahoo" -> "yahoo"
        """
        text = text.lower().strip()
        
        # Clean spoken words
        text = text.replace(' at ', '@').replace(' dot ', '.')
        text = re.sub(r'\s+', '', text)  # Remove spaces
        
        # Try to detect domain
        for domain_key in EmailCaptureHandler.KNOWN_DOMAINS.keys():
            if domain_key in text:
                return domain_key
        
        # Try exact domain name in KNOWN_DOMAINS
        for domain_key, full_domain in EmailCaptureHandler.KNOWN_DOMAINS.items():
            if text == domain_key or text == full_domain:
                return domain_key
        
        return None
    
    @staticmethod
    def extract_username_from_text(text: str) -> Optional[str]:
        """
        Extract just the username part from text.
        
        Rules:
        - Strip all spaces: "disha 3 8 0" -> "disha380"
        - Only return if no domain is present
        - Minimum 3 characters
        
        Examples:
            "disha 380" -> "disha380"
            "MT Disha 3" -> "mtdisha3"
            "disha380 at gmail dot com" -> None (has domain, not just username)
        """
        if not text:
            return None
        
        # Clean the text - remove spaces but keep alphanumeric
        cleaned = re.sub(r'[^a-z0-9._\-+%]', '', text.lower())
        
        # If cleaned text contains @, it has a domain - return None
        if '@' in cleaned or any(d in cleaned for d in EmailCaptureHandler.KNOWN_DOMAINS.keys()):
            return None
        
        # Ensure minimum length
        if len(cleaned) >= 3:
            return cleaned
        
        return None
    
    @staticmethod
    def validate_email_format(email: str) -> bool:
        """Validate that email matches standard format."""
        email_pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email.lower()))
    
    @staticmethod
    def process_email_input(text: str, previous_fragments: Optional[Dict] = None) -> EmailCaptureResult:
        """
        Process email input from voice transcription.
        
        Args:
            text: Voice transcribed text
            previous_fragments: Dict with previously captured fragments
                               E.g., {'username': 'disha380', 'domain': 'gmail'}
        
        Returns:
            EmailCaptureResult with validation status and user message
            
        RULE: NEVER process an email until you hear a domain.
        """
        if not text:
            return EmailCaptureResult(
                is_valid=False,
                message="I didn't catch that. Please provide your email address."
            )
        
        # Clean the voice text
        cleaned_text = EmailCaptureHandler.clean_voice_text(text)
        
        # Detect domain
        domain = EmailCaptureHandler.detect_domain(cleaned_text)
        
        # CRITICAL RULE: No domain detected - FRAGMENT
        if not domain:
            return EmailCaptureResult(
                is_valid=False,
                is_fragment=True,
                fragment_type='no_domain',
                message="I didn't catch a domain like gmail, yahoo, or outlook. Could you please say your email ending, like 'gmail' or 'yahoo'?"
            )
        
        # Extract username
        username = EmailCaptureHandler.extract_username_from_domain(cleaned_text, domain)
        
        # CRITICAL RULE: Only domain detected - ASK FOR USERNAME
        if not username:
            return EmailCaptureResult(
                is_valid=False,
                is_fragment=True,
                fragment_type='domain_only',
                domain_found=domain,
                message=f"I got the {domain} part, but what's the name before the @ sign?"
            )
        
        # Validate username format (basic check)
        if len(username) < 3:
            return EmailCaptureResult(
                is_valid=False,
                is_fragment=True,
                fragment_type='username_too_short',
                domain_found=domain,
                username_provided=username,
                message=f"The username '{username}' seems too short. Could you repeat it?"
            )
        
        # Stitch email together
        email = EmailCaptureHandler.stitch_email(username, domain)
        
        if not email:
            return EmailCaptureResult(
                is_valid=False,
                message="I couldn't process that email. Please try again."
            )
        
        # Final validation
        if not EmailCaptureHandler.validate_email_format(email):
            return EmailCaptureResult(
                is_valid=False,
                message=f"'{email}' doesn't look like a valid email. Please try again."
            )
        
        # SUCCESS
        return EmailCaptureResult(
            is_valid=True,
            email=email,
            domain_found=domain,
            username_provided=username,
            message=f"I heard '{email}', is that correct?"
        )
    
    @staticmethod
    def confirm_email(text: str, proposed_email: str) -> Tuple[bool, str]:
        """
        Handle user confirmation of email.
        
        Args:
            text: User's confirmation response
            proposed_email: The email waiting for confirmation
            
        Returns:
            (is_confirmed, message)
        """
        text_lower = text.lower().strip()
        
        # Affirmative responses
        affirmatives = ['yes', 'yep', 'yeah', 'correct', 'right', 'that\'s right', 'that is right']
        if any(word in text_lower for word in affirmatives):
            return True, "Great! Email confirmed."
        
        # Negative responses
        negatives = ['no', 'nope', 'wrong', 'incorrect', 'that\'s not right']
        if any(word in text_lower for word in negatives):
            return False, "Let's try again. Please provide your email address."
        
        # Unclear response
        return False, "I'm not sure if that's a yes or no. Can you confirm? Is the email correct?"


# Example usage in conversation flow:
"""
Example 1: User provides complete email
Input: "disha380 at gmail dot com"
Output: EmailCaptureResult(is_valid=True, email='disha380@gmail.com', message="I heard 'disha380@gmail.com', is that correct?")

Example 2: User provides only domain (FRAGMENT)
Input: "gmail"
Output: EmailCaptureResult(is_valid=False, is_fragment=True, fragment_type='domain_only', 
                          domain_found='gmail', message="I got the gmail part, but what's the name before the @ sign?")

Example 3: User provides only username (NO DOMAIN - CRITICAL RULE VIOLATION)
Input: "disha380"
Output: EmailCaptureResult(is_valid=False, is_fragment=True, fragment_type='no_domain',
                          message="I didn't catch a domain like gmail, yahoo, or outlook. Could you please say your email ending?")

Example 4: User provides domain but username is too short
Input: "di at gmail dot com"
Output: EmailCaptureResult(is_valid=False, is_fragment=True, fragment_type='username_too_short',
                          domain_found='gmail', username_provided='di', message="The username 'di' seems too short. Could you repeat it?")
"""
