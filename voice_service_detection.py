# voice_service_detection.py - Voice-based service detection and selection
"""
Service detection and selection module for voice-based dental service booking.
Detects dental services from spoken input, matches them to the service catalog,
and generates verbal confirmations with duration information.
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Service catalog matching
SERVICE_CATALOG = [
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

# Keywords and aliases for service detection
SERVICE_KEYWORDS = {
    "cleaning": {
        "keywords": ["clean", "cleaning", "cleanings", "scale", "scaling", "prophylaxis", "prophy"],
        "aliases": ["teeth clean", "tooth clean", "dental clean", "professional cleaning"],
        "patterns": ["i need.*cleaning", "i want.*cleaning", "cleaning please", "clean my teeth"]
    },
    "checkup": {
        "keywords": ["check", "checkup", "check-up", "exam", "examination", "visit", "appointment"],
        "aliases": ["dental exam", "routine exam", "regular checkup", "general exam"],
        "patterns": ["i need.*check", "i want.*checkup", "just a checkup", "routine exam"]
    },
    "filling": {
        "keywords": ["fill", "filling", "fillings", "cavity", "cavities", "composite", "amalgam"],
        "aliases": ["tooth filling", "cavity filling", "composite filling"],
        "patterns": ["i need.*fill", "i have.*cavity", "tooth filling"]
    },
    "root_canal": {
        "keywords": ["root", "root canal", "root canal treatment", "endodontic", "endodontia", "endo"],
        "aliases": ["root canal therapy", "rct", "canal treatment"],
        "patterns": ["root canal", "i need.*root", "canal treatment"]
    },
    "extraction": {
        "keywords": ["extract", "extraction", "pull", "pulling", "remove", "removal", "tooth removal"],
        "aliases": ["tooth extraction", "tooth pulling", "tooth removal", "extract tooth"],
        "patterns": ["extract.*tooth", "pull.*tooth", "tooth removal", "need.*extraction"]
    },
    "braces_consult": {
        "keywords": ["brace", "braces", "orthodont", "alignment", "straighten", "alignment consultation"],
        "aliases": ["braces consultation", "orthodontic consultation", "alignment check"],
        "patterns": ["i want.*braces", "braces consultation", "need.*braces"]
    },
    "whitening": {
        "keywords": ["whiten", "whitening", "bleach", "bleaching", "bright", "whiter", "teeth whitening"],
        "aliases": ["teeth whitening", "tooth whitening", "cosmetic whitening", "teeth bleaching"],
        "patterns": ["teeth whiten", "want.*whiten", "whiten my teeth", "teeth bleaching"]
    },
    "implant_consult": {
        "keywords": ["implant", "implants", "dental implant", "implant consultation", "implantology"],
        "aliases": ["implant consultation", "implant surgery consultation", "dental implant"],
        "patterns": ["implant consult", "need.*implant", "implant consultation"]
    },
    "emergency": {
        "keywords": ["emergency", "urgent", "pain", "ache", "severe", "problem", "help", "emergency care"],
        "aliases": ["emergency dental care", "urgent care", "emergency appointment"],
        "patterns": ["emergency", "urgent", "severe pain", "dental emergency", "i'm in pain"]
    },
    "consultation": {
        "keywords": ["consult", "consultation", "advice", "general", "advice needed", "talk"],
        "aliases": ["general consultation", "dental consultation", "consultation only"],
        "patterns": ["consultation", "i need.*advice", "general consultation"]
    }
}

@dataclass
class ServiceDetectionResult:
    """Result of service detection from voice input."""
    success: bool
    service_id: Optional[str] = None
    service_name: Optional[str] = None
    confidence: float = 0.0
    duration_minutes: Optional[int] = None
    price: Optional[int] = None
    category: Optional[str] = None
    detected_keyword: Optional[str] = None
    error_message: Optional[str] = None


class VoiceServiceDetector:
    """Detects dental services from voice input with high accuracy."""
    
    @staticmethod
    def detect_service(voice_input: str, language: str = 'en') -> ServiceDetectionResult:
        """
        Detect service from voice input.
        
        Args:
            voice_input: Spoken text from user
            language: Language code (en, hi, kn, etc.)
        
        Returns:
            ServiceDetectionResult with detected service or error
        """
        if not voice_input or len(voice_input.strip()) == 0:
            return ServiceDetectionResult(
                success=False,
                error_message="No voice input provided"
            )
        
        # Clean and normalize input
        cleaned_input = voice_input.lower().strip()
        
        # Try to detect service
        best_match = None
        best_confidence = 0.0
        matched_keyword = None
        
        # Search through all services
        for service_id, keywords_dict in SERVICE_KEYWORDS.items():
            # Check exact keywords
            for keyword in keywords_dict.get("keywords", []):
                if keyword in cleaned_input:
                    confidence = 0.95
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = service_id
                        matched_keyword = keyword
                        logger.debug(f"Service detected: {service_id} with keyword '{keyword}'")
            
            # Check aliases
            for alias in keywords_dict.get("aliases", []):
                if alias in cleaned_input:
                    confidence = 0.85
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = service_id
                        matched_keyword = alias
                        logger.debug(f"Service detected: {service_id} with alias '{alias}'")
            
            # Check patterns (basic regex-like matching)
            import re
            for pattern in keywords_dict.get("patterns", []):
                if re.search(pattern, cleaned_input):
                    confidence = 0.80
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = service_id
                        matched_keyword = pattern
                        logger.debug(f"Service detected: {service_id} with pattern '{pattern}'")
        
        # If service was detected, get full details
        if best_match:
            service_details = VoiceServiceDetector._get_service_details(best_match)
            if service_details:
                return ServiceDetectionResult(
                    success=True,
                    service_id=service_details["id"],
                    service_name=service_details["name"],
                    confidence=best_confidence,
                    duration_minutes=service_details["duration_minutes"],
                    price=service_details["price"],
                    category=service_details["category"],
                    detected_keyword=matched_keyword
                )
        
        # No service detected
        logger.warning(f"Could not detect service from input: {voice_input}")
        return ServiceDetectionResult(
            success=False,
            error_message="Could not identify the requested dental service. Please try again."
        )
    
    @staticmethod
    def _get_service_details(service_id: str) -> Optional[Dict]:
        """Get service details from catalog."""
        for service in SERVICE_CATALOG:
            if service["id"] == service_id:
                return service
        return None
    
    @staticmethod
    def get_all_services() -> List[Dict]:
        """Get complete service catalog."""
        return SERVICE_CATALOG


class ServiceConfirmationGenerator:
    """Generates verbal confirmations for selected services."""
    
    # Duration descriptions in different languages
    DURATION_DESCRIPTIONS = {
        'en': {
            15: "approximately 15 minutes",
            20: "about 20 minutes",
            30: "roughly 30 minutes",
            45: "around 45 minutes",
            60: "about an hour",
            90: "approximately an hour and a half"
        },
        'hi': {
            15: "लगभग 15 मिनट",
            20: "करीब 20 मिनट",
            30: "लगभग 30 मिनट",
            45: "करीब 45 मिनट",
            60: "लगभग एक घंटा",
            90: "लगभग डेढ़ घंटा"
        },
        'kn': {
            15: "ಸುಮಾರು 15 ನಿಮಿಷ",
            20: "ಸುಮಾರು 20 ನಿಮಿಷ",
            30: "ಸುಮಾರು 30 ನಿಮಿಷ",
            45: "ಸುಮಾರು 45 ನಿಮಿಷ",
            60: "ಸುಮಾರು ಒಂದು ಗಂಟೆ",
            90: "ಸುಮಾರು ಒಂದೂವರೆ ಗಂಟೆ"
        },
        'te': {
            15: "సుమారు 15 నిమిషాలు",
            20: "సుమారు 20 నిమిషాలు",
            30: "సుమారు 30 నిమిషాలు",
            45: "సుమారు 45 నిమిషాలు",
            60: "సుమారు ఒక గంట",
            90: "సుమారు ఒంటిన్నర గంటలు"
        },
        'ta': {
            15: "சுமார் 15 நிமிடங்கள்",
            20: "சுமார் 20 நிமிடங்கள்",
            30: "சுமார் 30 நிமிடங்கள்",
            45: "சுமார் 45 நிமிடங்கள்",
            60: "சுமார் ஒரு மணி நேரம்",
            90: "சுமார் ஒன்றிரை மணி நேரம்"
        },
        'ml': {
            15: "ഏകദേശം 15 മിനിറ്റ്",
            20: "ഏകദേശം 20 മിനിറ്റ്",
            30: "ഏകദേശം 30 മിനിറ്റ്",
            45: "ഏകദേശം 45 മിനിറ്റ്",
            60: "ഏകദേശം ഒരു മണിക്കൂര്",
            90: "ഏകദേശം ഒന്നര മണിക്കൂര്"
        },
        'mr': {
            15: "सुमारे 15 मिनिटे",
            20: "सुमारे 20 मिनिटे",
            30: "सुमारे 30 मिनिटे",
            45: "सुमारे 45 मिनिटे",
            60: "सुमारे एक तास",
            90: "सुमारे डेढ तास"
        }
    }
    
    @staticmethod
    def generate_confirmation(
        service_name: str,
        duration_minutes: int,
        language: str = 'en'
    ) -> str:
        """
        Generate verbal confirmation for selected service.
        
        Args:
            service_name: Name of selected service
            duration_minutes: Duration in minutes
            language: Language code
        
        Returns:
            Verbal confirmation message
        """
        # Get duration description
        duration_desc = ServiceConfirmationGenerator._get_duration_description(
            duration_minutes, language
        )
        
        # Generate confirmation message based on language
        if language == 'en':
            return f"{service_name} has been selected. This procedure typically requires {duration_desc}."
        elif language == 'hi':
            return f"{service_name} को चुना गया है। यह प्रक्रिया आमतौर पर {duration_desc} लेती है।"
        elif language == 'kn':
            return f"{service_name} ಅನ್ನು ಆಯ್ಕೆ ಮಾಡಲಾಗಿದೆ. ಈ ಪ್ರಕ್ರಿಯೆಯು ಸಾಮಾನ್ಯವಾಗಿ {duration_desc} ತೆಗೆದುಕೊಳ್ಳುತ್ತದೆ."
        elif language == 'te':
            return f"{service_name} ఎంపిక చేయబడింది. ఈ విధానానికి సాధారణంగా {duration_desc} పట్టుకుంటుంది."
        elif language == 'ta':
            return f"{service_name} தேர்ந்தெடுக்கப்பட்டுள்ளது. இந்த செயல்முறை வழக்கமாக {duration_desc} எடுக்கும்."
        elif language == 'ml':
            return f"{service_name} തിരഞ്ഞെടുക്കപ്പെട്ടിരിക്കുന്നു. ഈ നടപടിക്രമം സാധാരണയായി {duration_desc} എടുക്കുന്നു."
        elif language == 'mr':
            return f"{service_name} निवडलेले आहे. ही प्रक्रिया सामान्यतः {duration_desc} घेते."
        else:
            # Default to English
            return f"{service_name} has been selected. This procedure typically requires {duration_desc}."
    
    @staticmethod
    def _get_duration_description(duration_minutes: int, language: str = 'en') -> str:
        """Get duration description in specified language."""
        lang = language.lower()
        if lang not in ServiceConfirmationGenerator.DURATION_DESCRIPTIONS:
            lang = 'en'
        
        durations = ServiceConfirmationGenerator.DURATION_DESCRIPTIONS[lang]
        
        # Find closest match
        if duration_minutes in durations:
            return durations[duration_minutes]
        
        # Find nearest duration
        closest_duration = min(durations.keys(), key=lambda x: abs(x - duration_minutes))
        return durations[closest_duration]
    
    @staticmethod
    def generate_service_list_prompt(language: str = 'en') -> str:
        """
        Generate a prompt listing available services.
        
        Args:
            language: Language code
        
        Returns:
            Service list prompt for voice guidance
        """
        services = VoiceServiceDetector.get_all_services()
        
        if language == 'en':
            prompt = "We offer the following services: "
            services_list = ", ".join([s["name"] for s in services])
            return prompt + services_list + ". Which service would you like?"
        elif language == 'hi':
            prompt = "हम निम्नलिखित सेवाएं प्रदान करते हैं: "
            services_list = ", ".join([s["name"] for s in services])
            return prompt + services_list + ". आप कौन सी सेवा चाहते हैं?"
        elif language == 'kn':
            prompt = "ನಾವು ಈ ಕೆಳಗಿನ ಸೇವೆಗಳನ್ನು ಪ್ರದಾನ ಮಾಡುತ್ತೇವೆ: "
            services_list = ", ".join([s["name"] for s in services])
            return prompt + services_list + ". ನೀವು ಯಾವ ಸೇವೆ ಬಯಸುತ್ತೀರಿ?"
        else:
            # Default to English
            prompt = "We offer the following services: "
            services_list = ", ".join([s["name"] for s in services])
            return prompt + services_list + ". Which service would you like?"


class VoiceServiceSelector:
    """Orchestrates voice-based service selection workflow."""
    
    @staticmethod
    def process_voice_service_selection(
        voice_input: str,
        language: str = 'en'
    ) -> Dict:
        """
        Complete workflow: detect service, confirm, and return selection.
        
        Args:
            voice_input: Voice input from user
            language: Language code
        
        Returns:
            Dictionary with selection result and confirmation message
        """
        # Step 1: Detect service from voice input
        detection = VoiceServiceDetector.detect_service(voice_input, language)
        
        if not detection.success:
            logger.warning(f"Service detection failed: {detection.error_message}")
            return {
                "success": False,
                "error": detection.error_message,
                "service_id": None,
                "confirmation_message": None,
                "tts_text": None
            }
        
        # Step 2: Generate verbal confirmation
        confirmation_msg = ServiceConfirmationGenerator.generate_confirmation(
            detection.service_name,
            detection.duration_minutes,
            language
        )
        
        # Log successful detection
        logger.info(
            f"Service selected via voice: {detection.service_id} "
            f"({detection.service_name}) - Confidence: {detection.confidence}"
        )
        
        # Step 3: Return complete result
        return {
            "success": True,
            "service_id": detection.service_id,
            "service_name": detection.service_name,
            "duration_minutes": detection.duration_minutes,
            "price": detection.price,
            "category": detection.category,
            "confidence": detection.confidence,
            "detected_keyword": detection.detected_keyword,
            "confirmation_message": confirmation_msg,
            "tts_text": confirmation_msg  # For text-to-speech output
        }
