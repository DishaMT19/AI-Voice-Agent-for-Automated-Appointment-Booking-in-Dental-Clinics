"""
Test Suite for Voice-Only Booking Flow

Comprehensive testing of the voice-driven appointment booking system.
Tests cover:
- Conversation state management
- Intent classification
- Natural language parsing
- Complete booking workflow
- Error handling and clarifications
- Bilingual support (English and Hindi)
"""

import unittest
import json
from datetime import datetime, timedelta
from voice_only_booking_flow import (
    VoiceBookingFlowManager,
    BookingStage,
    ConversationIntent,
    PatientContext,
    AppointmentContext,
    ConversationState
)


class TestConversationState(unittest.TestCase):
    """Test conversation state management."""
    
    def test_state_initialization(self):
        """Test state initializes correctly."""
        state = ConversationState(session_id="test_123")
        self.assertEqual(state.session_id, "test_123")
        self.assertEqual(state.stage, BookingStage.WELCOME)
        self.assertEqual(state.language, "en")
        self.assertEqual(len(state.conversation_history), 0)
    
    def test_add_message(self):
        """Test adding messages to conversation history."""
        state = ConversationState(session_id="test_123")
        state.add_message("user", "Hello")
        state.add_message("system", "Welcome")
        
        self.assertEqual(len(state.conversation_history), 2)
        self.assertEqual(state.conversation_history[0]["speaker"], "user")
        self.assertEqual(state.conversation_history[1]["speaker"], "system")
    
    def test_patient_context(self):
        """Test patient context tracking."""
        patient = PatientContext()
        self.assertFalse(patient.has_complete_contact_info())
        
        patient.name = "John Doe"
        patient.phone = "9876543210"
        self.assertTrue(patient.has_complete_contact_info())
    
    def test_appointment_context(self):
        """Test appointment context tracking."""
        appt = AppointmentContext()
        self.assertFalse(appt.is_complete())
        
        appt.service = "Teeth Cleaning"
        appt.date = "2024-12-20"
        appt.time = "10:00 AM"
        self.assertTrue(appt.is_complete())
    
    def test_state_serialization(self):
        """Test state can be converted to dictionary."""
        state = ConversationState(session_id="test_123", language="en")
        state.patient.name = "Jane Smith"
        
        state_dict = state.to_dict()
        self.assertEqual(state_dict["session_id"], "test_123")
        self.assertEqual(state_dict["patient"]["name"], "Jane Smith")


class TestIntentClassification(unittest.TestCase):
    """Test intent classification from voice input."""
    
    def setUp(self):
        self.manager = VoiceBookingFlowManager("session_123", "en")
    
    def test_confirm_intent(self):
        """Test recognizing confirmation intents."""
        intents = [
            "yes", "yeah", "sure", "ok", "okay", "confirm",
            "haan", "bilkul", "sahi"
        ]
        
        for text in intents:
            intent = self.manager._classify_intent(text)
            self.assertEqual(intent, ConversationIntent.CONFIRM,
                           f"Failed to classify '{text}' as CONFIRM")
    
    def test_deny_intent(self):
        """Test recognizing denial intents."""
        intents = ["no", "nope", "not", "cancel", "nahi"]
        
        for text in intents:
            intent = self.manager._classify_intent(text)
            self.assertEqual(intent, ConversationIntent.DENY,
                           f"Failed to classify '{text}' as DENY")
    
    def test_service_request_intent(self):
        """Test recognizing service request intents."""
        intents = [
            "I need cleaning", "teeth checkup", "root canal",
            "tooth extraction", "whitening"
        ]
        
        for text in intents:
            intent = self.manager._classify_intent(text)
            self.assertEqual(intent, ConversationIntent.SERVICE_REQUEST,
                           f"Failed to classify '{text}' as SERVICE_REQUEST")
    
    def test_repeat_intent(self):
        """Test recognizing repeat/clarification intents."""
        intents = ["what", "huh", "repeat", "again", "dobara"]
        
        for text in intents:
            intent = self.manager._classify_intent(text)
            self.assertEqual(intent, ConversationIntent.REPEAT,
                           f"Failed to classify '{text}' as REPEAT")


class TestServiceExtraction(unittest.TestCase):
    """Test service extraction from voice input."""
    
    def setUp(self):
        self.manager = VoiceBookingFlowManager("session_123", "en")
    
    def test_extract_cleaning(self):
        """Test extracting teeth cleaning service."""
        result = self.manager._extract_service_from_text("I need teeth cleaning")
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 'cleaning')
    
    def test_extract_checkup(self):
        """Test extracting dental checkup service."""
        result = self.manager._extract_service_from_text("Can I get a checkup")
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 'checkup')
    
    def test_extract_root_canal(self):
        """Test extracting root canal service."""
        result = self.manager._extract_service_from_text("I need a root canal treatment")
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 'root_canal')
    
    def test_extract_extraction(self):
        """Test extracting tooth extraction service."""
        result = self.manager._extract_service_from_text("I need a tooth extracted")
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 'extraction')
    
    def test_unknown_service(self):
        """Test handling of unknown service."""
        result = self.manager._extract_service_from_text("I need something weird")
        self.assertIsNone(result)


class TestPhoneExtraction(unittest.TestCase):
    """Test phone number extraction."""
    
    def setUp(self):
        self.manager = VoiceBookingFlowManager("session_123", "en")
    
    def test_extract_10_digit_phone(self):
        """Test extracting 10-digit phone number."""
        result = self.manager._extract_phone("9876543210")
        self.assertEqual(result, "9876543210")
    
    def test_extract_phone_with_spacing(self):
        """Test extracting phone with spaces."""
        result = self.manager._extract_phone("98 76 54 32 10")
        self.assertEqual(result, "9876543210")
    
    def test_extract_phone_with_dashes(self):
        """Test extracting phone with dashes."""
        result = self.manager._extract_phone("98-765-43210")
        self.assertEqual(result, "9876543210")
    
    def test_invalid_short_phone(self):
        """Test handling too short phone number."""
        result = self.manager._extract_phone("98765")
        self.assertIsNone(result)


class TestEmailExtraction(unittest.TestCase):
    """Test email extraction from voice input."""
    
    def setUp(self):
        self.manager = VoiceBookingFlowManager("session_123", "en")
    
    def test_extract_simple_email(self):
        """Test extracting simple email."""
        result = self.manager._extract_email("john@example.com")
        self.assertEqual(result, "john@example.com")
    
    def test_extract_complex_email(self):
        """Test extracting complex email."""
        result = self.manager._extract_email("john.doe+test@example.co.uk")
        self.assertIsNotNone(result)
    
    def test_invalid_email(self):
        """Test handling invalid email."""
        result = self.manager._extract_email("john dot example")
        self.assertIsNone(result)


class TestWelcomeFlow(unittest.TestCase):
    """Test welcome stage handling."""
    
    def setUp(self):
        self.manager = VoiceBookingFlowManager("session_123", "en")
    
    def test_welcome_stage_initial(self):
        """Test initial state is welcome."""
        self.assertEqual(self.manager.state.stage, BookingStage.WELCOME)
    
    def test_welcome_with_service_request(self):
        """Test welcome flow when user mentions service."""
        response = self.manager.process_voice_input("I need teeth cleaning")
        
        self.assertTrue(response['success'])
        self.assertEqual(self.manager.state.stage, BookingStage.PATIENT_INFO)
        self.assertEqual(self.manager.state.appointment.service, "Teeth Cleaning")
    
    def test_welcome_with_confirmation(self):
        """Test welcome when user just confirms."""
        response = self.manager.process_voice_input("yes")
        
        self.assertTrue(response['success'])
        self.assertEqual(self.manager.state.stage, BookingStage.SERVICE_SELECTION)
    
    def test_welcome_messages_exist(self):
        """Test welcome messages for supported languages."""
        for lang in ['en', 'hi']:
            self.assertIn(lang, self.manager.WELCOME_MESSAGES)
            self.assertIn('first', self.manager.WELCOME_MESSAGES[lang])


class TestBilingualSupport(unittest.TestCase):
    """Test bilingual (English and Hindi) support."""
    
    def test_english_flow(self):
        """Test complete flow in English."""
        manager = VoiceBookingFlowManager("session_en", "en")
        self.assertEqual(manager.state.language, "en")
    
    def test_hindi_flow(self):
        """Test complete flow in Hindi."""
        manager = VoiceBookingFlowManager("session_hi", "hi")
        self.assertEqual(manager.state.language, "hi")
    
    def test_prompts_available_english(self):
        """Test English prompts are available."""
        manager = VoiceBookingFlowManager("session_en", "en")
        prompts = manager.CONVERSATIONAL_PROMPTS['en']
        
        self.assertIn('name_request', prompts)
        self.assertIn('phone_request', prompts)
        self.assertIn('email_request', prompts)
    
    def test_prompts_available_hindi(self):
        """Test Hindi prompts are available."""
        manager = VoiceBookingFlowManager("session_hi", "hi")
        prompts = manager.CONVERSATIONAL_PROMPTS['hi']
        
        self.assertIn('name_request', prompts)
        self.assertIn('phone_request', prompts)
        self.assertIn('email_request', prompts)


class TestConversationFlow(unittest.TestCase):
    """Test complete conversation workflows."""
    
    def test_complete_booking_flow_english(self):
        """Test complete booking from start to finish in English."""
        manager = VoiceBookingFlowManager("session_complete", "en")
        
        # Service selection
        response1 = manager.process_voice_input("I need cleaning")
        self.assertTrue(response1['success'])
        self.assertEqual(manager.state.appointment.service, "Teeth Cleaning")
        
        # Confirm service
        response2 = manager.process_voice_input("yes")
        self.assertTrue(response2['success'])
        self.assertEqual(manager.state.stage, BookingStage.PATIENT_INFO)
        
        # Provide name
        response3 = manager.process_voice_input("John Smith")
        self.assertTrue(response3['success'])
        self.assertEqual(manager.state.patient.name, "John Smith")
        
        # Provide phone
        response4 = manager.process_voice_input("9876543210")
        self.assertTrue(response4['success'])
        self.assertEqual(manager.state.patient.phone, "9876543210")
        
        # Provide email
        response5 = manager.process_voice_input("john@example.com")
        self.assertTrue(response5['success'])
        self.assertEqual(manager.state.patient.email, "john@example.com")
    
    def test_no_input_handling(self):
        """Test handling of no input."""
        manager = VoiceBookingFlowManager("session_no_input", "en")
        response = manager.process_voice_input("")
        
        self.assertTrue(response['success'])
        # Should still be in welcome stage
        self.assertEqual(manager.state.stage, BookingStage.WELCOME)
    
    def test_clarification_flow(self):
        """Test handling of unclear inputs."""
        manager = VoiceBookingFlowManager("session_clarify", "en")
        
        # Unclear input in welcome
        response1 = manager.process_voice_input("xyzabc blahblah")
        self.assertEqual(manager.state.clarification_count, 1)
        
        # Retry with unclear input
        response2 = manager.process_voice_input("nothing makes sense")
        self.assertEqual(manager.state.clarification_count, 2)


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases."""
    
    def test_invalid_phone_retry(self):
        """Test retry on invalid phone."""
        manager = VoiceBookingFlowManager("session_phone", "en")
        
        # Set up to patient info stage
        manager.state.stage = BookingStage.PATIENT_INFO
        manager.state.patient.name = "John"
        
        # Invalid phone
        response = manager.process_voice_input("invalid phone")
        self.assertEqual(manager.state.clarification_count, 1)
        response_text = response.get('text', '').lower()
        self.assertTrue('error' in response_text or 'phone' in response_text)
    
    def test_invalid_email_retry(self):
        """Test retry on invalid email."""
        manager = VoiceBookingFlowManager("session_email", "en")
        
        # Set up to email stage
        manager.state.stage = BookingStage.PATIENT_INFO
        manager.state.patient.name = "John"
        manager.state.patient.phone = "9876543210"
        
        # Invalid email
        response = manager.process_voice_input("not an email")
        self.assertEqual(manager.state.clarification_count, 1)
    
    def test_max_clarifications_limit(self):
        """Test that clarification count is tracked."""
        manager = VoiceBookingFlowManager("session_limit", "en")
        
        # Add clarifications
        for i in range(5):
            manager.state.clarification_count = i + 1
        
        self.assertEqual(manager.state.clarification_count, 5)
        self.assertGreater(manager.state.clarification_count, manager.state.max_clarifications)


class TestSessionManagement(unittest.TestCase):
    """Test session management and data persistence."""
    
    def test_session_id_generation(self):
        """Test each session gets unique ID."""
        manager1 = VoiceBookingFlowManager("session_1", "en")
        manager2 = VoiceBookingFlowManager("session_2", "en")
        
        self.assertNotEqual(manager1.session_id, manager2.session_id)
    
    def test_state_isolation(self):
        """Test states don't leak between sessions."""
        manager1 = VoiceBookingFlowManager("session_1", "en")
        manager2 = VoiceBookingFlowManager("session_2", "en")
        
        manager1.state.patient.name = "Alice"
        manager2.state.patient.name = "Bob"
        
        self.assertNotEqual(manager1.state.patient.name, manager2.state.patient.name)
    
    def test_booking_data_preparation(self):
        """Test booking data is prepared correctly for API."""
        manager = VoiceBookingFlowManager("session_123", "en")
        
        manager.state.patient.name = "John Doe"
        manager.state.patient.phone = "9876543210"
        manager.state.patient.email = "john@example.com"
        manager.state.patient.address = "123 Main St"
        manager.state.appointment.service = "Teeth Cleaning"
        manager.state.appointment.service_id = "cleaning"
        manager.state.appointment.date = "2024-12-20"
        manager.state.appointment.time = "10:00 AM"
        
        booking_data = manager._prepare_booking_data()
        
        self.assertEqual(booking_data['patient']['name'], "John Doe")
        self.assertEqual(booking_data['appointment']['service'], "Teeth Cleaning")
        self.assertEqual(booking_data['language'], "en")


if __name__ == '__main__':
    unittest.main()
