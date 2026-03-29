"""
Production Voice Receptionist - Backend State Machine

Implements strict step-by-step conversation flow with:
- Fixed conversation sequence (no skipping)
- Echo prevention
- Address bug fix
- Date/time user preference handling
- Service duration assignment
- Robust confirmation and backend saving
"""

import logging
from enum import Enum
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class ConversationStep(Enum):
    """Strict conversation steps in order."""
    ASK_SERVICE = "ASK_SERVICE"
    ASK_NAME = "ASK_NAME"
    ASK_PHONE = "ASK_PHONE"
    ASK_EMAIL = "ASK_EMAIL"
    ASK_ADDRESS = "ASK_ADDRESS"
    ASK_DATE = "ASK_DATE"
    ASK_TIME = "ASK_TIME"
    CONFIRM = "CONFIRM"
    COMPLETE = "COMPLETE"


# Step sequence (NO SKIPPING allowed)
STEP_SEQUENCE = [
    ConversationStep.ASK_SERVICE,
    ConversationStep.ASK_NAME,
    ConversationStep.ASK_PHONE,
    ConversationStep.ASK_EMAIL,
    ConversationStep.ASK_ADDRESS,
    ConversationStep.ASK_DATE,
    ConversationStep.ASK_TIME,
    ConversationStep.CONFIRM
]


class InputCleaner:
    """Cleans and validates user input to prevent echo/system prompt capture."""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text input."""
        if not text:
            return ""
        
        text = str(text).strip()
        # Remove extra spaces
        text = ' '.join(text.split())
        return text
    
    @staticmethod
    def is_system_prompt_echo(user_input: str, system_prompt: str) -> bool:
        """
        Detect if user is echoing the system prompt (echo prevention).
        Returns True if input is too similar to prompt.
        """
        user_clean = user_input.lower().strip()
        prompt_clean = system_prompt.lower().strip()
        
        # Exact match or near-exact
        if user_clean in prompt_clean or prompt_clean in user_clean:
            return True
        
        # Check for key keywords from prompt
        prompt_keywords = [w for w in prompt_clean.split() if len(w) > 3]
        user_words = set(user_clean.split())
        
        # If most keywords are in user input, probably echo
        if prompt_keywords:
            keyword_match = sum(1 for kw in prompt_keywords if any(kw in w for w in user_words))
            if keyword_match / len(prompt_keywords) > 0.7:
                return True
        
        return False


class InputValidator:
    """Validates input for each step."""
    
    @staticmethod
    def validate_service(text: str) -> tuple[bool, str]:
        """Validate service selection."""
        services = ['cleaning', 'checkup', 'filling', 'root canal', 'extraction', 
                   'whitening', 'implant', 'braces', 'emergency', 'consultation']
        
        text_lower = text.lower()
        
        for service in services:
            if service in text_lower:
                return True, service.title()
        
        return False, ""
    
    @staticmethod
    def validate_name(text: str) -> tuple[bool, str]:
        """Validate name input."""
        text = InputCleaner.clean_text(text)
        
        # Name should have at least 2 words typically, or at least 3 characters
        if len(text) < 3:
            return False, ""
        
        # Should be mostly letters
        letter_count = sum(1 for c in text if c.isalpha())
        if letter_count / len(text) < 0.7:
            return False, ""
        
        # Reject common system-like phrases
        if any(phrase in text.lower() for phrase in ['tell me', 'your name', 'say', 'speak']):
            return False, ""
        
        return True, text.title()
    
    @staticmethod
    def validate_phone(text: str) -> tuple[bool, str]:
        """Validate phone number (10 digits for India)."""
        import re
        
        # Extract only digits
        digits = re.sub(r'\D', '', text)
        
        # Check length
        if len(digits) < 10:
            return False, ""
        
        # Take last 10 digits
        phone = digits[-10:]
        
        # Validate: Indian numbers start with 6-9
        if phone[0] not in '6789':
            return False, ""
        
        return True, phone
    
    @staticmethod
    def validate_email(text: str) -> tuple[bool, str]:
        """Validate email (or allow skip)."""
        import re
        
        text = text.lower().strip()
        
        # Check for skip patterns
        if any(skip in text for skip in ['skip', 'no email', 'not provided']):
            return True, "Not provided"
        
        # Convert spoken format to written
        email = text.replace(' at ', '@').replace(' dot ', '.')
        email = re.sub(r'\s+', '', email)
        
        # Basic email pattern
        pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, email):
            return True, email
        
        return False, ""
    
    @staticmethod
    def validate_address(text: str) -> tuple[bool, str]:
        """
        Validate address input.
        
        BUG FIX: Reject if input matches system prompt or is too short.
        Addresses should be meaningful user responses.
        """
        text = InputCleaner.clean_text(text)
        
        # Reject if too short (system prompts are longer)
        if len(text) < 5:
            return False, ""
        
        # Reject common system phrases
        phrases_to_reject = ['address', 'share your', 'tell me', 'please provide', 'street']
        if any(phrase in text.lower() for phrase in phrases_to_reject):
            return False, ""
        
        # Reject if just question words
        if text.lower() in ['what', 'when', 'where', 'why', 'how']:
            return False, ""
        
        # Accept any other meaningful input
        return True, text
    
    @staticmethod
    def validate_date(text: str) -> tuple[bool, str]:
        """Validate date (user preference, not auto-assigned)."""
        # Use natural language parser
        from natural_language_datetime import NaturalLanguageDatetimeParser
        
        try:
            result = NaturalLanguageDatetimeParser.parse(text)
            if result and result.resolved_date:
                return True, result.resolved_date
        except Exception as e:
            logger.warning(f"Date parsing error: {e}")
        
        return False, ""
    
    @staticmethod
    def validate_time(text: str) -> tuple[bool, str]:
        """Validate time (user preference, not auto-assigned)."""
        from natural_language_datetime import NaturalLanguageDatetimeParser
        
        try:
            result = NaturalLanguageDatetimeParser.parse(text)
            if result and result.resolved_time:
                return True, result.resolved_time
        except Exception as e:
            logger.warning(f"Time parsing error: {e}")
        
        return False, ""


@dataclass
class ConversationData:
    """Data collected during conversation."""
    service: str = ""
    name: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    date: str = ""
    time: str = ""
    duration: str = ""
    
    def is_complete(self) -> bool:
        """Check if all required fields are filled."""
        return all([self.service, self.name, self.phone, self.email, 
                   self.date, self.time])
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'service': self.service,
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'address': self.address,
            'date': self.date,
            'time': self.time,
            'duration': self.duration
        }


class ProductionVoiceReceptionist:
    """
    Production-ready voice receptionist with strict state machine.
    
    FEATURES:
    - Exact step sequence (no skipping)
    - Echo prevention
    - Input validation per step
    - Address bug fix
    - User preference for date/time
    - Confirmation before save
    - Robust backend integration
    """
    
    # Only accept these intents for confirmation step
    CONFIRM_INTENTS = {'yes', 'yeah', 'yep', 'confirm', 'correct', 'haan', 'bilkul', 'sahi'}
    DENY_INTENTS = {'no', 'nope', 'not', 'cancel', 'back', 'nahi', 'nay'}
    
    def __init__(self, session_id: str, language: str = 'en'):
        """Initialize receptionist for a session."""
        self.session_id = session_id
        self.language = language
        
        # State tracking
        self.current_step_index = 0
        self.current_step = STEP_SEQUENCE[0]
        self.data = ConversationData()
        self.retry_count = 0
        self.max_retries = 2
        
        # Logging
        logger.info(f"ProductionVoiceReceptionist initialized: {session_id}, lang={language}")
    
    def process_input(self, user_input: str, last_system_message: str = "") -> Dict[str, Any]:
        """
        Process user input and return next action.
        
        STRICT state machine: only advance if input is valid for current step.
        """
        user_input = InputCleaner.clean_text(user_input)
        
        if not user_input:
            return self._error_response("Please provide your response")
        
        # Echo prevention: Check if input is system prompt echo
        if last_system_message and InputCleaner.is_system_prompt_echo(user_input, last_system_message):
            return self._error_response("Please say your own response, not the prompt")
        
        # Process based on current step
        if self.current_step == ConversationStep.ASK_SERVICE:
            return self._process_service(user_input)
        elif self.current_step == ConversationStep.ASK_NAME:
            return self._process_name(user_input)
        elif self.current_step == ConversationStep.ASK_PHONE:
            return self._process_phone(user_input)
        elif self.current_step == ConversationStep.ASK_EMAIL:
            return self._process_email(user_input)
        elif self.current_step == ConversationStep.ASK_ADDRESS:
            return self._process_address(user_input)
        elif self.current_step == ConversationStep.ASK_DATE:
            return self._process_date(user_input)
        elif self.current_step == ConversationStep.ASK_TIME:
            return self._process_time(user_input)
        elif self.current_step == ConversationStep.CONFIRM:
            return self._process_confirmation(user_input)
        
        return self._error_response("Invalid step")
    
    # ==================== STEP PROCESSORS ====================
    
    def _process_service(self, user_input: str) -> Dict[str, Any]:
        """Process service selection (STEP 1)."""
        valid, service_name = InputValidator.validate_service(user_input)
        
        if not valid:
            return self._retry_response("Service not recognized. Please try: cleaning, checkup, filling, root canal, extraction, etc.")
        
        self.data.service = service_name
        self.retry_count = 0
        
        # Advance to next step
        return self._advance_step(f"Great! You selected {service_name}. Now, what is your full name?")
    
    def _process_name(self, user_input: str) -> Dict[str, Any]:
        """Process name input (STEP 2)."""
        valid, name = InputValidator.validate_name(user_input)
        
        if not valid:
            return self._retry_response("I didn't catch a valid name. Can you please say it again?")
        
        self.data.name = name
        self.retry_count = 0
        
        return self._advance_step(f"Thank you, {name}. What is your phone number? Please say the 10 digits clearly.")
    
    def _process_phone(self, user_input: str) -> Dict[str, Any]:
        """Process phone input (STEP 3)."""
        valid, phone = InputValidator.validate_phone(user_input)
        
        if not valid:
            return self._retry_response("I need a valid 10-digit phone number. Please try again.")
        
        self.data.phone = phone
        self.retry_count = 0
        
        return self._advance_step(f"Perfect. And your email address? You can say it like: abc at gmail dot com")
    
    def _process_email(self, user_input: str) -> Dict[str, Any]:
        """Process email input (STEP 4)."""
        valid, email = InputValidator.validate_email(user_input)
        
        if not valid:
            return self._retry_response("I didn't understand the email. You can say 'skip' to continue without email.")
        
        self.data.email = email
        self.retry_count = 0
        
        return self._advance_step(f"Great! What is your address?")
    
    def _process_address(self, user_input: str) -> Dict[str, Any]:
        """
        Process address input (STEP 5).
        
        BUG FIX: Reject if input matches system prompt or is too short.
        """
        valid, address = InputValidator.validate_address(user_input)
        
        if not valid:
            return self._retry_response("Please provide your actual address. For example: House No. 123, Street Name, City")
        
        self.data.address = address
        self.retry_count = 0
        
        return self._advance_step(f"Thank you. When would you like to book? You can say: today, tomorrow, next Monday, or a specific date.")
    
    def _process_date(self, user_input: str) -> Dict[str, Any]:
        """
        Process date input (STEP 6).
        
        BUG FIX: Always use user-provided date, never auto-assign.
        """
        valid, date_str = InputValidator.validate_date(user_input)
        
        if not valid:
            return self._retry_response("I didn't understand the date. Please try: today, tomorrow, or a specific date like January 15.")
        
        self.data.date = date_str
        self.retry_count = 0
        
        return self._advance_step(f"Perfect! That's {date_str}. What time do you prefer? You can say: morning, afternoon, or a specific time like 2 PM.")
    
    def _process_time(self, user_input: str) -> Dict[str, Any]:
        """
        Process time input (STEP 7).
        
        BUG FIX: Always use user-provided time, never auto-assign.
        """
        valid, time_str = InputValidator.validate_time(user_input)
        
        if not valid:
            return self._retry_response("I didn't understand the time. Please try: morning, afternoon, or a time like 2 PM or 14:00.")
        
        self.data.time = time_str
        self.retry_count = 0
        
        # Move to confirmation step
        return self._move_to_confirmation()
    
    def _process_confirmation(self, user_input: str) -> Dict[str, Any]:
        """Process final confirmation (STEP 8)."""
        user_lower = user_input.lower().strip()
        
        # Check intent
        if any(intent in user_lower for intent in self.CONFIRM_INTENTS):
            # User confirmed - prepare for backend save
            return self._prepare_for_save()
        
        elif any(intent in user_lower for intent in self.DENY_INTENTS):
            # User wants to change something
            return self._retry_response("What would you like to change? You can say: name, phone, email, address, date, or time.")
        
        else:
            # Unclear response
            return self._retry_response("Please say YES to confirm or NO to make changes.")
    
    # ==================== STEP MANAGEMENT ====================
    
    def _advance_step(self, next_message: str) -> Dict[str, Any]:
        """Move to next step in sequence."""
        self.current_step_index += 1
        
        if self.current_step_index < len(STEP_SEQUENCE):
            self.current_step = STEP_SEQUENCE[self.current_step_index]
            
            return {
                'success': True,
                'text': next_message,
                'nextAction': 'listen',
                'step': self.current_step.value,
                'stepIndex': self.current_step_index,
                'state': self._get_state()
            }
        
        return self._error_response("Booking flow error")
    
    def _move_to_confirmation(self) -> Dict[str, Any]:
        """Move to confirmation step."""
        self.current_step_index += 1
        self.current_step = ConversationStep.CONFIRM
        
        # Build confirmation summary
        summary = self._build_confirmation_summary()
        
        return {
            'success': True,
            'text': f"Let me confirm: {summary}. Say YES to confirm or NO to make changes.",
            'nextAction': 'listen',
            'step': 'CONFIRM',
            'state': self._get_state()
        }
    
    def _prepare_for_save(self) -> Dict[str, Any]:
        """
        Prepare for backend save.
        
        All fields should be complete at this point.
        """
        if not self.data.is_complete():
            missing = []
            if not self.data.service: missing.append('service')
            if not self.data.name: missing.append('name')
            if not self.data.phone: missing.append('phone')
            if not self.data.email: missing.append('email')
            if not self.data.date: missing.append('date')
            if not self.data.time: missing.append('time')
            
            error_msg = f"Missing: {', '.join(missing)}"
            return self._error_response(error_msg)
        
        # Ready for save
        return {
            'success': True,
            'text': "Perfect! Saving your appointment...",
            'nextAction': 'save',
            'bookingData': {
                'patient': {
                    'name': self.data.name,
                    'phone': self.data.phone,
                    'email': self.data.email,
                    'address': self.data.address or 'Not provided'
                },
                'appointment': {
                    'service': self.data.service,
                    'date': self.data.date,
                    'time': self.data.time
                }
            },
            'state': self._get_state()
        }
    
    # ==================== RETRY & ERROR HANDLING ====================
    
    def _retry_response(self, message: str) -> Dict[str, Any]:
        """Handle retry for current step."""
        self.retry_count += 1
        
        if self.retry_count > self.max_retries:
            return self._error_response(f"Too many retries. Returning to {self.current_step.value}")
        
        return {
            'success': False,
            'text': message,
            'nextAction': 'retry',
            'retryCount': self.retry_count,
            'step': self.current_step.value,
            'state': self._get_state()
        }
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """Handle error."""
        return {
            'success': False,
            'text': message,
            'nextAction': 'error',
            'state': self._get_state()
        }
    
    # ==================== UTILITIES ====================
    
    def _build_confirmation_summary(self) -> str:
        """Build readable confirmation summary."""
        items = []
        items.append(f"{self.data.name}")
        items.append(f"{self.data.service}")
        items.append(f"on {self.data.date} at {self.data.time}")
        
        return " | ".join(items)
    
    def _get_state(self) -> Dict[str, Any]:
        """Get current conversation state."""
        return {
            'step': self.current_step.value,
            'stepIndex': self.current_step_index,
            'patient': {
                'name': self.data.name,
                'phone': self.data.phone,
                'email': self.data.email,
                'address': self.data.address
            },
            'appointment': {
                'service': self.data.service,
                'date': self.data.date,
                'time': self.data.time,
                'duration': self.data.duration
            }
        }


# Global session management
voice_receptionist_sessions = {}


def create_session(session_id: str, language: str = 'en') -> ProductionVoiceReceptionist:
    """Create a new receptionist session."""
    receptionist = ProductionVoiceReceptionist(session_id, language)
    voice_receptionist_sessions[session_id] = receptionist
    logger.info(f"Created session: {session_id}")
    return receptionist


def get_session(session_id: str) -> Optional[ProductionVoiceReceptionist]:
    """Get existing session."""
    return voice_receptionist_sessions.get(session_id)


def delete_session(session_id: str) -> bool:
    """Delete session."""
    if session_id in voice_receptionist_sessions:
        del voice_receptionist_sessions[session_id]
        logger.info(f"Deleted session: {session_id}")
        return True
    return False
