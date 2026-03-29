"""
Voice-Only Appointment Booking Flow Manager

This module implements a fully voice-driven, receptionist-like appointment booking
experience. The flow eliminates all UI button interactions and provides natural,
conversational guidance through the booking process.

Key Features:
- Completely voice-driven (no button interactions required)
- Natural language understanding for conversational flow
- Context-aware probing (avoids redundant questions)
- Receptionist-like behavior (friendly, natural, helpful)
- Multi-stage conversation management
- Automatic progression through booking steps
- Error recovery and clarification flows
- Bilingual support (EN, HI, and others)
"""

import json
import logging
from enum import Enum
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field

# Import robust input processor for fixing slot filling issues
from input_processor import InputProcessor, PhoneExtractor, EmailExtractor, NameExtractor, AddressExtractor

logger = logging.getLogger(__name__)


class BookingStage(Enum):
    """Stages in the voice-driven booking flow."""
    WELCOME = "welcome"           # Initial greeting and language confirmation
    SERVICE_SELECTION = "service" # Determine which dental service needed
    PATIENT_INFO = "patient_info" # Collect name, phone, email, address
    DATE_SELECTION = "date"       # Determine preferred date
    TIME_SELECTION = "time"       # Determine preferred time
    CONFIRMATION = "confirmation" # Final confirmation before booking
    COMPLETION = "completion"     # Booking complete, email sent


class ConversationIntent(Enum):
    """Intent classification for voice input."""
    GREETING = "greeting"
    SERVICE_REQUEST = "service"
    PROVIDE_INFO = "info"
    CONFIRM = "confirm"
    DENY = "deny"
    UNCLEAR = "unclear"
    REPEAT = "repeat"
    HELP = "help"


@dataclass
class PatientContext:
    """Context for patient information during conversation."""
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    
    def has_complete_contact_info(self) -> bool:
        """Check if we have enough contact info."""
        return bool(self.name and self.phone)
    
    def to_dict(self) -> Dict[str, Optional[str]]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class AppointmentContext:
    """Context for appointment details during conversation."""
    service: Optional[str] = None
    service_id: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    doctor_id: str = "doc_001"
    
    def is_complete(self) -> bool:
        """Check if appointment details are complete."""
        return bool(self.service and self.date and self.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ConversationState:
    """Complete state of the voice conversation."""
    session_id: str
    stage: BookingStage = BookingStage.WELCOME
    language: str = "en"
    patient: PatientContext = field(default_factory=PatientContext)
    appointment: AppointmentContext = field(default_factory=AppointmentContext)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    last_system_prompt: str = ""
    clarification_count: int = 0
    max_clarifications: int = 3
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_message(self, speaker: str, text: str, intent: Optional[str] = None) -> None:
        """Add a message to conversation history."""
        self.conversation_history.append({
            "speaker": speaker,
            "text": text,
            "intent": intent,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_conversation_summary(self) -> str:
        """Get a summary of conversation so far."""
        messages = "\n".join([
            f"{msg['speaker']}: {msg['text']}" 
            for msg in self.conversation_history[-5:]  # Last 5 messages
        ])
        return messages
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "stage": self.stage.value,
            "language": self.language,
            "patient": self.patient.to_dict(),
            "appointment": self.appointment.to_dict(),
            "conversation_history": self.conversation_history,
            "last_system_prompt": self.last_system_prompt,
            "clarification_count": self.clarification_count,
            "start_time": self.start_time
        }


class VoiceBookingFlowManager:
    """
    Manages the complete voice-driven appointment booking flow.
    
    This class orchestrates a natural, receptionist-like conversation that
    guides users through booking without any UI button interactions.
    """
    
    # Welcome messages in different languages
    WELCOME_MESSAGES = {
        'en': {
            'first': "Welcome to Smile Dental Clinic. I'm your virtual receptionist. I'll help you book an appointment today. Which service would you like to book?",
            'returning': "Welcome back to Smile Dental Clinic. What can I help you with today?",
            'service_examples': "We offer services like cleaning, checkups, fillings, root canals, extractions, and more. What service are you interested in?"
        },
        'hi': {
            'first': "स्माइल डेंटल क्लिनिक में आपका स्वागत है। मैं आपका वर्चुअल रिसेप्शनिस्ट हूं। मैं आपकी appointment बुक करने में मदद करूंगा। आप कौन सी सेवा बुक करना चाहते हैं?",
            'returning': "स्माइल डेंटल क्लिनिक में आपका पुनः स्वागत है। आज मैं आपकी कोई मदद कर सकता हूं?",
            'service_examples': "हम cleaning, checkups, fillings, root canals, extractions जैसी सेवाएं प्रदान करते हैं। आप किस सेवा में रुचि रखते हैं?"
        }
    }
    
    # Follow-up prompts that sound natural and conversational
    CONVERSATIONAL_PROMPTS = {
        'en': {
            'confirm_service': "Just to confirm, you're looking for {service}? Is that correct?",
            'name_request': "Great! To get started, could you please tell me your full name?",
            'phone_request': "Thank you, {name}. What's the best phone number to reach you?",
            'email_request': "Perfect. And your email address? This is where we'll send your confirmation.",
            'address_request': "Do you have an address on file with us, or should I note your current address?",
            'date_request': "Wonderful. When would you like to come in? You can say today, tomorrow, next week, or a specific date.",
            'time_request': "What time works best for you? Morning, afternoon, or a specific time?",
            'final_confirmation': "Let me confirm your booking: {name}, {service} on {date} at {time}. Should I go ahead and book this?",
            'thank_you': "Thank you, {name}! Your appointment is confirmed. You'll receive an email confirmation shortly with all the details."
        },
        'hi': {
            'confirm_service': "बस confirm करने के लिए, आप {service} ढूंढ रहे हैं? क्या यह सही है?",
            'name_request': "शुरु करने के लिए, कृपया अपना पूरा नाम बताएं?",
            'phone_request': "धन्यवाद, {name}। आपसे संपर्क करने का सर्वोत्तम फोन नंबर क्या है?",
            'email_request': "बहुत अच्छा। और आपका ईमेल पता? हम यहां आपकी पुष्टि भेजेंगे।",
            'address_request': "क्या आपके पास हमारे साथ एक पता है, या मुझे आपका वर्तमान पता नोट करना चाहिए?",
            'date_request': "शानदार। आप कब आना चाहते हैं? आप आज, कल, अगले सप्ताह, या एक विशिष्ट तारीख कह सकते हैं।",
            'time_request': "आपके लिए कौन सा समय सबसे अच्छा है? सुबह, दोपहर, या एक विशिष्ट समय?",
            'final_confirmation': "आपकी booking की पुष्टि करते हैं: {name}, {service} पर {date} {time} पर। क्या मैं यह book कर दूं?",
            'thank_you': "धन्यवाद, {name}! आपकी appointment की पुष्टि हुई। आपको सभी विवरणों के साथ जल्द ही एक ईमेल पुष्टि मिलेगी।"
        }
    }
    
    # Error and clarification messages
    ERROR_MESSAGES = {
        'en': {
            'unclear': "I didn't quite understand that. Could you please repeat or rephrase?",
            'invalid_name': "I didn't catch the name clearly. Could you spell it or say it again?",
            'invalid_phone': "That doesn't seem like a valid phone number. Could you provide a 10-digit number?",
            'invalid_email': "That doesn't look like a valid email. Could you try again?",
            'no_slots': "Unfortunately, we don't have availability at that time. Would you like to try another time?",
            'clarify_service': "We have several services. Could you be more specific about what you need?"
        },
        'hi': {
            'unclear': "मुझे यह बिल्कुल समझ नहीं आया। क्या आप कृपया दोहराएंगे या फिर से बयां करेंगे?",
            'invalid_name': "मुझे नाम स्पष्ट नहीं सुनाई दिया। क्या आप इसे spell कर सकते हैं या फिर से कह सकते हैं?",
            'invalid_phone': "यह एक valid फोन नंबर नहीं लगता। क्या आप 10-digit नंबर प्रदान कर सकते हैं?",
            'invalid_email': "यह एक valid email नहीं लगता। क्या आप फिर से कोशिश कर सकते हैं?",
            'no_slots': "दुर्भाग्यवश, हमारे पास उस समय उपलब्धता नहीं है। क्या आप किसी अन्य समय की कोशिश करना चाहेंगे?",
            'clarify_service': "हमारे पास कई सेवाएं हैं। क्या आप यह निर्दिष्ट कर सकते हैं कि आपको क्या चाहिए?"
        }
    }
    
    def __init__(self, session_id: str, language: str = "en"):
        """Initialize the booking flow manager."""
        self.session_id = session_id
        self.state = ConversationState(
            session_id=session_id,
            stage=BookingStage.WELCOME,
            language=language
        )
        logger.info(f"VoiceBookingFlowManager initialized: {session_id}, lang={language}")
    
    def process_voice_input(self, voice_text: str) -> Dict[str, Any]:
        """
        Process voice input and determine next action.
        
        This is the main entry point for handling user voice input.
        """
        if not voice_text or voice_text.strip() == "":
            return self._no_input_response()
        
        # Classify intent
        intent = self._classify_intent(voice_text)
        self.state.add_message("user", voice_text, intent.value)
        
        # Route based on current stage
        if self.state.stage == BookingStage.WELCOME:
            return self._handle_welcome_stage(voice_text, intent)
        elif self.state.stage == BookingStage.SERVICE_SELECTION:
            return self._handle_service_stage(voice_text, intent)
        elif self.state.stage == BookingStage.PATIENT_INFO:
            return self._handle_patient_info_stage(voice_text, intent)
        elif self.state.stage == BookingStage.DATE_SELECTION:
            return self._handle_date_stage(voice_text, intent)
        elif self.state.stage == BookingStage.TIME_SELECTION:
            return self._handle_time_stage(voice_text, intent)
        elif self.state.stage == BookingStage.CONFIRMATION:
            return self._handle_confirmation_stage(voice_text, intent)
        else:
            return self._stage_not_implemented()
    
    # ==================== INTENT CLASSIFICATION ====================
    
    def _classify_intent(self, voice_text: str) -> ConversationIntent:
        """Classify the intent of the user's voice input."""
        text = voice_text.lower().strip()
        
        # Check for clarifications FIRST (higher priority)
        clarify = ['what', 'huh', 'pardon', 'unclear', 'again', 'repeat', 'dobara', 'phir se']
        if any(word in text for word in clarify):
            return ConversationIntent.REPEAT
        
        # Check for common patterns
        affirmative = ['yes', 'yeah', 'sure', 'ok', 'okay', 'confirm', 'that\'s correct',
                       'haan', 'ha', 'bilkul', 'theek', 'sahi', 'ji']
        negative = ['no', 'nope', 'not', 'cancel', 'nahi', 'nay', 'mat', 'asli mein']
        
        if any(word in text for word in affirmative):
            return ConversationIntent.CONFIRM
        elif any(word in text for word in negative):
            return ConversationIntent.DENY
        elif text in ['help', 'assist', 'madad', 'sahayata']:
            return ConversationIntent.HELP
        elif any(service in text for service in ['clean', 'check', 'fill', 'root', 'extract', 'whiten', 'implant', 'brace']):
            return ConversationIntent.SERVICE_REQUEST
        else:
            return ConversationIntent.PROVIDE_INFO
    
    # ==================== STAGE HANDLERS ====================
    
    def _handle_welcome_stage(self, voice_text: str, intent: ConversationIntent) -> Dict[str, Any]:
        """Handle welcome stage - initial greeting."""
        # Check if user is acknowledging welcome or providing service info
        if intent in [ConversationIntent.CONFIRM, ConversationIntent.SERVICE_REQUEST]:
            # They're ready to proceed - move to service selection
            if intent == ConversationIntent.SERVICE_REQUEST:
                # They mentioned a service directly
                service_info = self._extract_service_from_text(voice_text)
                if service_info:
                    self.state.appointment.service = service_info['name']
                    self.state.appointment.service_id = service_info['id']
                    # Move directly to patient info
                    self.state.stage = BookingStage.PATIENT_INFO
                    response_text = self.CONVERSATIONAL_PROMPTS[self.state.language]['name_request']
                    self.state.last_system_prompt = response_text
                    self.state.add_message("system", response_text)
                    return self._response(response_text, next_action="listen_for_name")
                else:
                    # Service not recognized, ask for clarification
                    response_text = self.CONVERSATIONAL_PROMPTS[self.state.language].get('clarify_service',
                        self.ERROR_MESSAGES[self.state.language]['clarify_service'])
                    self.state.last_system_prompt = response_text
                    self.state.add_message("system", response_text)
                    return self._response(response_text, next_action="listen_for_service")
            else:
                # Just confirming they understood - move to service selection
                self.state.stage = BookingStage.SERVICE_SELECTION
                response_text = self.WELCOME_MESSAGES[self.state.language]['service_examples']
                self.state.last_system_prompt = response_text
                self.state.add_message("system", response_text)
                return self._response(response_text, next_action="listen_for_service")
        else:
            # Unknown response, increment clarification and repeat welcome
            self.state.clarification_count += 1
            response_text = self.WELCOME_MESSAGES[self.state.language]['first']
            self.state.last_system_prompt = response_text
            self.state.add_message("system", response_text)
            return self._response(response_text, next_action="listen_for_service")
    
    def _handle_service_stage(self, voice_text: str, intent: ConversationIntent) -> Dict[str, Any]:
        """Handle service selection stage."""
        # Handle repeat intent
        if intent == ConversationIntent.REPEAT:
            guidance = self.WELCOME_MESSAGES[self.state.language]['service_examples']
            self.state.last_system_prompt = guidance
            self.state.add_message("system", guidance)
            self.state.clarification_count += 1
            return self._response(guidance, next_action="listen_for_service")
        
        service_info = self._extract_service_from_text(voice_text)
        
        if service_info:
            self.state.appointment.service = service_info['name']
            self.state.appointment.service_id = service_info['id']
            
            # Confirm the service with the user
            confirmation = self.CONVERSATIONAL_PROMPTS[self.state.language]['confirm_service'].format(
                service=service_info['name']
            )
            self.state.last_system_prompt = confirmation
            self.state.add_message("system", confirmation)
            return self._response(confirmation, next_action="confirm_service")
        else:
            # Service not found, provide guidance
            error_text = self.ERROR_MESSAGES[self.state.language]['clarify_service']
            self.state.last_system_prompt = error_text
            self.state.add_message("system", error_text)
            self.state.clarification_count += 1
            return self._response(error_text, next_action="listen_for_service")
    
    def _handle_patient_info_stage(self, voice_text: str, intent: ConversationIntent) -> Dict[str, Any]:
        """Handle patient information collection stage with robust input validation."""
        # Determine what info we're currently collecting
        if not self.state.patient.name:
            # Collecting name with validation
            if intent not in [ConversationIntent.CONFIRM, ConversationIntent.DENY]:
                name, is_valid, error_msg = InputProcessor.process_name_input(voice_text)
                
                if is_valid:
                    self.state.patient.name = name
                    # Ask for phone
                    response_text = self.CONVERSATIONAL_PROMPTS[self.state.language]['phone_request'].format(
                        name=self.state.patient.name
                    )
                    self.state.last_system_prompt = response_text
                    self.state.add_message("system", response_text)
                    return self._response(response_text, next_action="listen_for_phone")
                else:
                    # Invalid name input
                    self.state.clarification_count += 1
                    error_text = self.ERROR_MESSAGES[self.state.language]['invalid_name']
                    self.state.last_system_prompt = error_text
                    self.state.add_message("system", error_text)
                    return self._response(error_text, next_action="listen_for_name")
            else:
                # User confirmed something we didn't ask for, still need name
                response_text = self.CONVERSATIONAL_PROMPTS[self.state.language]['name_request']
                self.state.last_system_prompt = response_text
                self.state.add_message("system", response_text)
                return self._response(response_text, next_action="listen_for_name")
        
        elif not self.state.patient.phone:
            # Collecting phone with validation
            phone, is_valid, error_msg = InputProcessor.process_phone_input(voice_text)
            
            if is_valid:
                self.state.patient.phone = phone
                # Ask for email
                response_text = self.CONVERSATIONAL_PROMPTS[self.state.language]['email_request']
                self.state.last_system_prompt = response_text
                self.state.add_message("system", response_text)
                return self._response(response_text, next_action="listen_for_email")
            else:
                # Invalid phone
                self.state.clarification_count += 1
                error_text = self.ERROR_MESSAGES[self.state.language]['invalid_phone']
                self.state.last_system_prompt = error_text
                self.state.add_message("system", error_text)
                return self._response(error_text, next_action="listen_for_phone")
        
        elif not self.state.patient.email:
            # Collecting email with validation
            email, is_valid, error_msg = InputProcessor.process_email_input(voice_text)
            
            if is_valid:
                self.state.patient.email = email
                # Ask for address
                response_text = self.CONVERSATIONAL_PROMPTS[self.state.language]['address_request']
                self.state.last_system_prompt = response_text
                self.state.add_message("system", response_text)
                return self._response(response_text, next_action="listen_for_address")
            else:
                # Invalid email
                self.state.clarification_count += 1
                error_text = self.ERROR_MESSAGES[self.state.language]['invalid_email']
                self.state.last_system_prompt = error_text
                self.state.add_message("system", error_text)
                return self._response(error_text, next_action="listen_for_email")
        
        elif not self.state.patient.address:
            # Collecting address with validation
            address, is_valid, error_msg = InputProcessor.process_address_input(voice_text)
            
            if is_valid:
                self.state.patient.address = address
                # Move to date selection
                self.state.stage = BookingStage.DATE_SELECTION
                response_text = self.CONVERSATIONAL_PROMPTS[self.state.language]['date_request']
                self.state.last_system_prompt = response_text
                self.state.add_message("system", response_text)
                return self._response(response_text, next_action="listen_for_date")
            else:
                # Invalid address input
                self.state.clarification_count += 1
                error_text = self.ERROR_MESSAGES[self.state.language]['unclear']
                self.state.last_system_prompt = error_text
                self.state.add_message("system", error_text)
                return self._response(error_text, next_action="listen_for_address")
        
        return self._response("Error in info collection", next_action="error")
    
    def _handle_date_stage(self, voice_text: str, intent: ConversationIntent) -> Dict[str, Any]:
        """Handle date selection stage."""
        parsed_date = self._parse_date_from_text(voice_text)
        
        if parsed_date:
            self.state.appointment.date = parsed_date
            # Move to time selection
            self.state.stage = BookingStage.TIME_SELECTION
            response_text = self.CONVERSATIONAL_PROMPTS[self.state.language]['time_request']
            self.state.last_system_prompt = response_text
            self.state.add_message("system", response_text)
            return self._response(response_text, next_action="listen_for_time")
        else:
            error_text = self.ERROR_MESSAGES[self.state.language]['unclear']
            self.state.last_system_prompt = error_text
            self.state.add_message("system", error_text)
            self.state.clarification_count += 1
            return self._response(error_text, next_action="listen_for_date")
    
    def _handle_time_stage(self, voice_text: str, intent: ConversationIntent) -> Dict[str, Any]:
        """Handle time selection stage."""
        parsed_time = self._parse_time_from_text(voice_text)
        
        if parsed_time:
            self.state.appointment.time = parsed_time
            # Move to confirmation
            self.state.stage = BookingStage.CONFIRMATION
            confirmation = self.CONVERSATIONAL_PROMPTS[self.state.language]['final_confirmation'].format(
                name=self.state.patient.name,
                service=self.state.appointment.service,
                date=self.state.appointment.date,
                time=self.state.appointment.time
            )
            self.state.last_system_prompt = confirmation
            self.state.add_message("system", confirmation)
            return self._response(confirmation, next_action="confirm_booking")
        else:
            error_text = self.ERROR_MESSAGES[self.state.language]['unclear']
            self.state.last_system_prompt = error_text
            self.state.add_message("system", error_text)
            self.state.clarification_count += 1
            return self._response(error_text, next_action="listen_for_time")
    
    def _handle_confirmation_stage(self, voice_text: str, intent: ConversationIntent) -> Dict[str, Any]:
        """Handle final confirmation stage."""
        if intent == ConversationIntent.CONFIRM:
            # Booking confirmed!
            self.state.stage = BookingStage.COMPLETION
            thank_you = self.CONVERSATIONAL_PROMPTS[self.state.language]['thank_you'].format(
                name=self.state.patient.name
            )
            self.state.last_system_prompt = thank_you
            self.state.add_message("system", thank_you)
            return self._response(
                thank_you,
                next_action="booking_complete",
                booking_data=self._prepare_booking_data()
            )
        elif intent == ConversationIntent.DENY:
            # They want to change something
            clarification = "What would you like to change? You can say name, phone, email, service, date, or time."
            self.state.last_system_prompt = clarification
            self.state.add_message("system", clarification)
            return self._response(clarification, next_action="listen_for_change")
        else:
            # Unclear response, repeat confirmation
            confirmation = self.CONVERSATIONAL_PROMPTS[self.state.language]['final_confirmation'].format(
                name=self.state.patient.name,
                service=self.state.appointment.service,
                date=self.state.appointment.date,
                time=self.state.appointment.time
            )
            self.state.last_system_prompt = confirmation
            self.state.add_message("system", confirmation)
            return self._response(confirmation, next_action="confirm_booking")
    
    # ==================== HELPER METHODS ====================
    
    def _extract_service_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract service information from spoken text."""
        text_lower = text.lower()
        
        services_map = {
            'clean': {'name': 'Teeth Cleaning', 'id': 'cleaning'},
            'check': {'name': 'Dental Checkup', 'id': 'checkup'},
            'fill': {'name': 'Tooth Filling', 'id': 'filling'},
            'root': {'name': 'Root Canal Treatment', 'id': 'root_canal'},
            'extract': {'name': 'Tooth Extraction', 'id': 'extraction'},
            'whiten': {'name': 'Teeth Whitening', 'id': 'whitening'},
            'implant': {'name': 'Implant Consultation', 'id': 'implant_consult'},
            'brace': {'name': 'Braces Consultation', 'id': 'braces_consult'},
            'emergency': {'name': 'Emergency Care', 'id': 'emergency'},
        }
        
        for keyword, service_info in services_map.items():
            if keyword in text_lower:
                return service_info
        
        return None
    
    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number from spoken text using robust processor."""
        phone = PhoneExtractor.extract_phone(text)
        return phone if phone else None
    
    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email from spoken text using robust processor."""
        email = EmailExtractor.extract_email(text)
        return email if email else None
    
    def _parse_date_from_text(self, text: str) -> Optional[str]:
        """Parse date from spoken text using natural language parser."""
        from natural_language_datetime import NaturalLanguageDatetimeParser
        
        try:
            # NaturalLanguageDatetimeParser returns a ParsedDateTime object with resolved_date
            result = NaturalLanguageDatetimeParser.parse(text)
            if result and result.resolved_date:
                return result.resolved_date
        except Exception as e:
            logger.warning(f"Date parsing error: {e}")
        
        return None
    
    def _parse_time_from_text(self, text: str) -> Optional[str]:
        """Parse time from spoken text using natural language parser."""
        from natural_language_datetime import NaturalLanguageDatetimeParser
        
        try:
            # NaturalLanguageDatetimeParser returns a ParsedDateTime object with resolved_time
            result = NaturalLanguageDatetimeParser.parse(text)
            if result and result.resolved_time:
                return result.resolved_time
        except Exception as e:
            logger.warning(f"Time parsing error: {e}")
        
        return None
    
    def _prepare_booking_data(self) -> Dict[str, Any]:
        """Prepare booking data for API call."""
        return {
            'patient': {
                'name': self.state.patient.name,
                'phone': self.state.patient.phone,
                'email': self.state.patient.email,
                'address': self.state.patient.address or 'Not provided'
            },
            'appointment': {
                'service': self.state.appointment.service,
                'service_id': self.state.appointment.service_id,
                'date': self.state.appointment.date,
                'time': self.state.appointment.time,
                'doctor_id': self.state.appointment.doctor_id
            },
            'language': self.state.language,
            'conversationHistory': self.state.conversation_history
        }
    
    def _no_input_response(self) -> Dict[str, Any]:
        """Handle no input from user."""
        response_text = "I'm listening. Please go ahead with your request."
        self.state.last_system_prompt = response_text
        return self._response(response_text, next_action="listen")
    
    def _stage_not_implemented(self) -> Dict[str, Any]:
        """Handle unimplemented stage."""
        response_text = "I encountered an unexpected state. Let me start over. What service would you like to book?"
        self.state.stage = BookingStage.SERVICE_SELECTION
        return self._response(response_text, next_action="listen_for_service")
    
    def _response(self, text: str, next_action: str, booking_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Format response for frontend."""
        return {
            'success': True,
            'text': text,
            'nextAction': next_action,
            'state': self.state.to_dict(),
            'bookingData': booking_data,
            'sessionId': self.session_id
        }
    
    def get_state(self) -> Dict[str, Any]:
        """Get current conversation state."""
        return self.state.to_dict()
