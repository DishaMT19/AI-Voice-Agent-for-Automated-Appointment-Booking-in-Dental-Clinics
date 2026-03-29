# backend/nlp.py - NLP, entity extraction, and intent classification
"""
Natural Language Processing layer for entity extraction and intent detection.
Handles multi-language support and confidence scoring.
"""

import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from config import SERVICES, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE
from validation import (
    clean_input_text, validate_name, validate_phone, validate_email,
    validate_date, validate_time, validate_language, ValidationResult
)
from logging_config import logger_nlp, audit_logger, log_operation

# ============================================================================
# ENTITY EXTRACTION
# ============================================================================

class EntityExtractor:
    """Extracts named entities from conversational input."""
    
    @staticmethod
    @log_operation("extract_service")
    def extract_service(text: str) -> Tuple[Optional[str], float]:
        """Extract service name from text with confidence score."""
        if not text:
            return None, 0.0
        
        text_lower = clean_input_text(text).lower()
        
        # Exact match first
        for service in SERVICES:
            service_name_lower = service['name'].lower()
            if service_name_lower in text_lower:
                confidence = 0.95 if service_name_lower == text_lower else 0.85
                logger_nlp.debug("Service extracted (exact)", service=service['name'], confidence=confidence)
                audit_logger.log_entity_extraction("service", text, service['name'], confidence)
                return service['name'], confidence
        
        # Keyword matching
        keywords = {
            'cleaning': 'Teeth Cleaning',
            'clean': 'Teeth Cleaning',
            'checkup': 'Dental Checkup',
            'check': 'Dental Checkup',
            'filling': 'Tooth Filling',
            'fill': 'Tooth Filling',
            'root': 'Root Canal Treatment',
            'extraction': 'Tooth Extraction',
            'remove': 'Tooth Extraction',
            'emergency': 'Emergency Care',
            'urgent': 'Emergency Care',
            'consult': 'General Consultation',
            'whitening': 'Teeth Whitening',
            'white': 'Teeth Whitening',
            'crown': 'Dental Crown',
            'bridge': 'Dental Bridge',
            'dentures': 'Dentures',
            'gum': 'Gum Treatment',
            'xray': 'Dental X-Ray',
            'x-ray': 'Dental X-Ray',
            'implant': 'Implant Consultation',
            'braces': 'Braces Consultation',
        }
        
        for keyword, service_name in keywords.items():
            if keyword in text_lower:
                confidence = 0.75
                logger_nlp.debug("Service extracted (keyword)", keyword=keyword, service=service_name, confidence=confidence)
                audit_logger.log_entity_extraction("service", text, service_name, confidence)
                return service_name, confidence
        
        logger_nlp.debug("Service not extracted", text=text)
        return None, 0.0
    
    @staticmethod
    @log_operation("extract_patient_name")
    def extract_patient_name(text: str) -> Tuple[Optional[str], float]:
        """Extract patient name from text."""
        if not text:
            return None, 0.0
        
        cleaned = clean_input_text(text).strip()
        result = validate_name(cleaned)
        
        if result.valid:
            logger_nlp.debug("Name extracted", value=result.value, confidence=result.confidence)
            audit_logger.log_entity_extraction("name", text, result.value, result.confidence)
            return result.value, result.confidence
        
        return None, 0.0
    
    @staticmethod
    @log_operation("extract_phone")
    def extract_phone(text: str) -> Tuple[Optional[str], float]:
        """Extract phone number from text."""
        if not text:
            return None, 0.0
        
        result = validate_phone(text)
        
        if result.valid:
            logger_nlp.debug("Phone extracted", value=result.value, confidence=result.confidence)
            audit_logger.log_entity_extraction("phone", text, result.value, result.confidence)
            return result.value, result.confidence
        
        return None, 0.0
    
    @staticmethod
    @log_operation("extract_email")
    def extract_email(text: str) -> Tuple[Optional[str], float]:
        """Extract email from text with multi-pattern support."""
        if not text:
            return None, 0.0
        
        result = validate_email(text)
        
        if result.valid:
            logger_nlp.debug("Email extracted", value=result.value, confidence=result.confidence)
            audit_logger.log_entity_extraction("email", text, result.value, result.confidence)
            return result.value, result.confidence
        
        return None, 0.0
    
    @staticmethod
    @log_operation("extract_date")
    def extract_date(text: str) -> Tuple[Optional[str], float]:
        """Extract date from text."""
        if not text:
            return None, 0.0
        
        result = validate_date(text)
        
        if result.valid:
            logger_nlp.debug("Date extracted", value=result.value, confidence=result.confidence)
            audit_logger.log_entity_extraction("date", text, result.value, result.confidence)
            return result.value, result.confidence
        
        return None, 0.0
    
    @staticmethod
    @log_operation("extract_time")
    def extract_time(text: str) -> Tuple[Optional[str], float]:
        """Extract time from text."""
        if not text:
            return None, 0.0
        
        result = validate_time(text)
        
        if result.valid:
            logger_nlp.debug("Time extracted", value=result.value, confidence=result.confidence)
            audit_logger.log_entity_extraction("time", text, result.value, result.confidence)
            return result.value, result.confidence
        
        return None, 0.0

# ============================================================================
# INTENT CLASSIFICATION
# ============================================================================

class IntentClassifier:
    """Classifies user intent from conversational input."""
    
    INTENTS = {
        'book_appointment': [
            'book', 'schedule', 'appointment', 'appt', 'meeting', 'dental',
            'reserve', 'slot', 'time', 'date', 'when', 'क्या मैं अपॉइंटमेंट बुक कर सकता हूँ'
        ],
        'cancel_appointment': [
            'cancel', 'delete', 'remove', 'postpone', 'reschedule', 'change',
            'later', 'nope', 'no', 'cancel it', 'not interested'
        ],
        'check_availability': [
            'available', 'free', 'slots', 'when', 'time', 'date', 'check',
            'is there', 'do you have', 'when can'
        ],
        'get_info': [
            'info', 'information', 'tell', 'what', 'how', 'why', 'where',
            'who', 'which', 'price', 'cost', 'duration', 'treatment'
        ],
        'confirm': [
            'yes', 'confirm', 'correct', 'right', 'ok', 'okay', 'sure',
            'haan', 'sahi', 'theek', 'yes please'
        ],
        'deny': [
            'no', 'nope', 'not', 'don\'t', 'dont', 'skip', 'no thanks',
            'nahi', 'mat', 'skip it', 'later'
        ]
    }
    
    @classmethod
    @log_operation("classify_intent")
    def classify(cls, text: str) -> Tuple[str, float]:
        """Classify user intent with confidence score."""
        if not text:
            return 'unknown', 0.0
        
        text_lower = clean_input_text(text).lower()
        scores = {}
        
        for intent, keywords in cls.INTENTS.items():
            matches = sum(1 for kw in keywords if kw in text_lower)
            score = min(1.0, matches / len(keywords)) if keywords else 0.0
            scores[intent] = score
        
        if max(scores.values()) > 0:
            best_intent = max(scores.items(), key=lambda x: x[1])
            logger_nlp.debug("Intent classified", intent=best_intent[0], confidence=best_intent[1])
            return best_intent[0], best_intent[1]
        
        return 'unknown', 0.0

# ============================================================================
# DIALOGUE STATE TRACKER
# ============================================================================

class DialogueState:
    """Tracks state during conversation."""
    
    def __init__(self):
        self.turn_count = 0
        self.extracted_entities = {
            'name': None,
            'phone': None,
            'email': None,
            'service': None,
            'date': None,
            'time': None,
            'language': DEFAULT_LANGUAGE,
        }
        self.confidence_scores = {}
        self.intents = []
        self.conversation_log = []
    
    def update_entity(self, entity_type: str, value: str, confidence: float):
        """Update extracted entity."""
        self.extracted_entities[entity_type] = value
        self.confidence_scores[entity_type] = confidence
        logger_nlp.debug("Entity updated", type=entity_type, value=value, confidence=confidence)
    
    def add_intent(self, intent: str, confidence: float):
        """Add classified intent."""
        self.intents.append({
            'intent': intent,
            'confidence': confidence,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def add_turn(self, user_input: str, bot_response: str, entities_extracted: Dict = None):
        """Add conversation turn."""
        self.turn_count += 1
        self.conversation_log.append({
            'turn': self.turn_count,
            'user_input': user_input,
            'bot_response': bot_response,
            'entities': entities_extracted or {}
        })
    
    def get_missing_entities(self) -> List[str]:
        """Get list of required entities that haven't been extracted."""
        required = ['name', 'phone', 'service', 'date', 'time']
        missing = []
        
        for entity in required:
            if not self.extracted_entities.get(entity):
                missing.append(entity)
        
        return missing
    
    def is_complete(self) -> bool:
        """Check if all required entities are extracted."""
        return len(self.get_missing_entities()) == 0
    
    def get_state_summary(self) -> Dict:
        """Get current state summary."""
        return {
            'turn_count': self.turn_count,
            'entities': self.extracted_entities,
            'confidence_scores': self.confidence_scores,
            'missing_entities': self.get_missing_entities(),
            'is_complete': self.is_complete(),
            'intents': self.intents[-3:] if self.intents else [],
            'turns': len(self.conversation_log)
        }

# ============================================================================
# SINGLETON INSTANCES
# ============================================================================

entity_extractor = EntityExtractor()
intent_classifier = IntentClassifier()
