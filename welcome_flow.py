# welcome_flow.py - Language-aware welcome message generation
"""
Welcome flow module for generating professional, language-appropriate
welcome messages that guide users to state their required dental service.
Designed specifically for text-to-speech output.
"""

from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)

# Language codes
LANGUAGE_CODES = {
    'en': 'en-US',
    'hi': 'hi-IN',
    'kn': 'kn-IN',
    'te': 'te-IN',
    'ta': 'ta-IN',
    'ml': 'ml-IN',
    'mr': 'mr-IN'
}

class WelcomeFlowGenerator:
    """Generate language-aware welcome messages for dental clinic."""
    
    # Welcome messages in different languages
    WELCOME_MESSAGES = {
        'en': {
            'welcome': "Welcome to Smile Dental Clinic.",
            'assistance': "I will assist you in booking your appointment.",
            'guidance': "Please tell me the dental service you require.",
            'full': "Welcome to Smile Dental Clinic. I will assist you in booking your appointment. Please tell me the dental service you require."
        },
        'hi': {
            'welcome': "स्माइल डेंटल क्लिनिक में आपका स्वागत है।",
            'assistance': "मैं आपकी appointment बुक करने में आपकी सहायता करूंगा।",
            'guidance': "कृपया बताएं कि आपको कौन सी दंत सेवा की आवश्यकता है।",
            'full': "स्माइल डेंटल क्लिनिक में आपका स्वागत है। मैं आपकी appointment बुक करने में आपकी सहायता करूंगा। कृपया बताएं कि आपको कौन सी दंत सेवा की आवश्यकता है।"
        },
        'kn': {
            'welcome': "ಸ್ಮೈಲ್ ಡೆಂಟಲ್ ಕ್ಲಿನಿಕ್‌ಗೆ ಸ್ವಾಗತ.",
            'assistance': "ನಿಮ್ಮ appointment ಬುಕ್ ಮಾಡಲು ನಾನು ನಿಮ್ಮನ್ನು ಸಹಾಯ ಮಾಡುತ್ತೇನೆ.",
            'guidance': "ನೀವು ಯಾವ ಹಲ್ಲಿನ ಸೇವೆ ಬಯಸುತ್ತೀರಿ ಎಂದು ದಯವಿಟ್ಟು ತಿಳಿಸಿ.",
            'full': "ಸ್ಮೈಲ್ ಡೆಂಟಲ್ ಕ್ಲಿನಿಕ್‌ಗೆ ಸ್ವಾಗತ. ನಿಮ್ಮ appointment ಬುಕ್ ಮಾಡಲು ನಾನು ನಿಮ್ಮನ್ನು ಸಹಾಯ ಮಾಡುತ್ತೇನೆ. ನೀವು ಯಾವ ಹಲ್ಲಿನ ಸೇವೆ ಬಯಸುತ್ತೀರಿ ಎಂದು ದಯವಿಟ್ಟು ತಿಳಿಸಿ."
        },
        'te': {
            'welcome': "స్మైల్ డెంటల్ క్లినిక్‌కు స్వాగతం.",
            'assistance': "నిన్ను appointment బుక్ చేయడానికి నేను సహాయం చేస్తాను.",
            'guidance': "దయచేసి మీకు కావలసిన దంత సేవ గురించి చెప్పండి.",
            'full': "స్మైల్ డెంటల్ క్లినిక్‌కు స్వాగతం. నిన్ను appointment బుక్ చేయడానికి నేను సహాయం చేస్తాను. దయచేసి మీకు కావలసిన దంత సేవ గురించి చెప్పండి."
        },
        'ta': {
            'welcome': "Smile Dental Clinic க்கு வரவேற்கிறோம்.",
            'assistance': "உங்கள் appointment ஐ பதிவு செய்ய நான் உங்களுக்கு உதவிய்யுகிறேன்.",
            'guidance': "தயவுசெய்து நீங்கள் தேவைப்படும் பல் சேவை பற்றி சொல்லுங்கள்.",
            'full': "Smile Dental Clinic க்கு வரவேற்கிறோம். உங்கள் appointment ஐ பதிவு செய்ய நான் உங்களுக்கு உதவிய்யுகிறேன். தயவுசெய்து நீங்கள் தேவைப்படும் பல் சேவை பற்றி சொல்லுங்கள்."
        },
        'ml': {
            'welcome': "സ്മൈൽ ഡെന്റൽ ക്ലിനിക്കിലേക്ക് സ്വാഗതം.",
            'assistance': "നിങ്ങളുടെ appointment ബുക്ക് ചെയ്യാൻ ഞാൻ നിങ്ങളെ സഹായിക്കും.",
            'guidance': "നിങ്ങൾക്ക് ആവശ്യമായ ദന്ത സേവയെ കുറിച്ച് പറയുക.",
            'full': "സ്മൈൽ ഡെന്റൽ ക്ലിനിക്കിലേക്ക് സ്വാഗതം. നിങ്ങളുടെ appointment ബുക്ക് ചെയ്യാൻ ഞാൻ നിങ്ങളെ സഹായിക്കും. നിങ്ങൾക്ക് ആവശ്യമായ ദന്ത സേവയെ കുറിച്ച് പറയുക."
        },
        'mr': {
            'welcome': "स्माईल डेंटल क्लिनिकला स्वागत आहे.",
            'assistance': "आपली appointment बुक करण्यात मी आपल्याला मदत करीन.",
            'guidance': "कृपया आपल्याला आवश्यक असलेल्या दंत सेवेबद्दल सांगा.",
            'full': "स्माईल डेंटल क्लिनिकला स्वागत आहे. आपली appointment बुक करण्यात मी आपल्याला मदत करीन. कृपया आपल्याला आवश्यक असलेल्या दंत सेवेबद्दल सांगा."
        }
    }
    
    # Alternative friendly messages
    ALTERNATIVE_MESSAGES = {
        'en': [
            "Welcome to Smile Dental Clinic. How can I help you book an appointment today?",
            "Hello! Welcome to our dental clinic. What service are you interested in?",
            "Hi there! I'm here to help you schedule a dental appointment. What brings you in?"
        ],
        'hi': [
            "स्माइल डेंटल क्लिनिक में आपका स्वागत है। आप आज कौन सी सेवा लेना चाहते हैं?",
            "नमस्ते! हमारे दंत क्लिनिक में आपका स्वागत है। आप कौन सी सेवा लेना चाहते हैं?"
        ],
        'kn': [
            "ಸ್ಮೈಲ್ ಡೆಂಟಲ್ ಕ್ಲಿನಿಕ್‌ಗೆ ಸ್ವಾಗತ. ನೀವು ಯಾವ ಸೇವೆ ಬಯಸುತ್ತೀರಿ?",
            "ನಮಸ್ತೆ! ಯಾವ ಸೇವೆಯ ಬೆಳೆಯನ್ನು ನೀವು ಬಯಸುತ್ತೀರಿ?"
        ],
        'te': [
            "స్మైల్ డెంటల్ క్లినిక్‌కు స్వాగతం. ఏ సేవ పాలిచ్చుకోవాలి?",
            "హలో! మీకు ఏ దంత సేవ కావాలి?"
        ],
        'ta': [
            "Smile Dental Clinic க்கு வரவேற்கிறோம். நீங்கள் என்ன சேவை வேண்டும்?",
            "வணக்கம்! நீங்கள் என்ன பல் சேவை வேண்டுகிறீர்கள்?"
        ],
        'ml': [
            "സ്മൈൽ ഡെന്റൽ ക്ലിനിക്കിലേക്ക് സ്വാഗതം. നിങ്ങൾക്ക് ഏത് സേവ വേണ്ടത്?",
            "നിങ്ങൾക്ക് ഏത് ദന്ത സേവ വേണ്ടത്?"
        ],
        'mr': [
            "स्माईल डेंटल क्लिनिकला स्वागत आहे. आपल्याला कोणती सेवा हवी आहे?",
            "नमस्ते! आपल्याला कोणती दंत सेवा हवी आहे?"
        ]
    }
    
    @staticmethod
    def get_welcome_message(language: str, style: str = 'full') -> str:
        """
        Get welcome message for the specified language.
        
        Args:
            language: Language code (en, hi, kn, te, ta, ml, mr)
            style: 'full' (complete message), 'alternative' (friendly variant), 
                   or specific part ('welcome', 'assistance', 'guidance')
        
        Returns:
            Welcome message text suitable for TTS output
        """
        language = language.lower()
        
        # Validate language
        if language not in WelcomeFlowGenerator.WELCOME_MESSAGES:
            logger.warning(f"Unsupported language: {language}. Using English.")
            language = 'en'
        
        if style == 'alternative':
            messages = WelcomeFlowGenerator.ALTERNATIVE_MESSAGES.get(language, [])
            return messages[0] if messages else WelcomeFlowGenerator.WELCOME_MESSAGES[language]['full']
        
        if style in ['welcome', 'assistance', 'guidance']:
            return WelcomeFlowGenerator.WELCOME_MESSAGES[language][style]
        
        # Default to full message
        return WelcomeFlowGenerator.WELCOME_MESSAGES[language]['full']
    
    @staticmethod
    def get_language_code(language: str) -> str:
        """Get TTS language code for the specified language."""
        return LANGUAGE_CODES.get(language.lower(), 'en-US')
    
    @staticmethod
    def get_language_voice(language: str, gender: str = 'female') -> str:
        """
        Get appropriate voice for TTS based on language.
        
        Args:
            language: Language code
            gender: 'male' or 'female' (default: female)
        
        Returns:
            Voice name for edge-tts
        """
        voices = {
            'en': {
                'female': 'en-US-JennyNeural',
                'male': 'en-US-GuyNeural'
            },
            'hi': {
                'female': 'hi-IN-SwaraNeural',
                'male': 'hi-IN-ManishNeural'
            },
            'kn': {
                'female': 'kn-IN-GaganNeural',
                'male': 'kn-IN-GaganNeural'
            },
            'te': {
                'female': 'te-IN-ShrutiNeural',
                'male': 'te-IN-MohanNeural'
            },
            'ta': {
                'female': 'ta-IN-PallaviNeural',
                'male': 'ta-IN-ValluvarNeural'
            },
            'ml': {
                'female': 'ml-IN-AadhaNeural',
                'male': 'ml-IN-MidhunNeural'
            },
            'mr': {
                'female': 'mr-IN-AarohiNeural',
                'male': 'mr-IN-ManoharNeural'
            }
        }
        
        lang = language.lower()
        if lang not in voices:
            lang = 'en'
        
        gender_key = 'female' if gender.lower() != 'male' else 'male'
        return voices[lang].get(gender_key, voices['en']['female'])
    
    @staticmethod
    def get_next_guidance_prompt(language: str) -> str:
        """Get the guidance prompt after welcome message."""
        guidance = {
            'en': 'What dental service do you need?',
            'hi': 'आप कौन सी दंत सेवा चाहते हैं?',
            'kn': 'ನೀವು ಯಾವ ಹಲ್ಲಿನ ಸೇವೆ ಚಾಹುತ್ತೀರಿ?',
            'te': 'మీరు ఏ దంత సేవ కావాలి?',
            'ta': 'நீங்கள் என்ன பல் சேவை வேண்டும்?',
            'ml': 'നിങ്ങൾക്ക് ഏത് ദന്ത സേവ വേണ്ടത്?',
            'mr': 'आपल्याला कोणती दंत सेवा हवी आहे?'
        }
        return guidance.get(language.lower(), guidance['en'])
    
    @staticmethod
    def get_service_prompt_examples(language: str) -> Dict[str, str]:
        """Get service prompt examples for the selected language."""
        examples = {
            'en': {
                'cleaning': 'teeth cleaning or checkup',
                'filling': 'filling',
                'extraction': 'tooth extraction',
                'emergency': 'emergency care',
                'consultation': 'general consultation'
            },
            'hi': {
                'cleaning': 'दांत की सफाई या चेकअप',
                'filling': 'फिलिंग',
                'extraction': 'दांत निकालना',
                'emergency': 'आपातकालीन देखभाल',
                'consultation': 'सामान्य परामर्श'
            },
            'kn': {
                'cleaning': 'ಹಲ್ಲಿನ ಸಫಾಈ ಅಥವಾ ಪರೀಕ್ಷೆ',
                'filling': 'ಫಿಲಿಂಗ್',
                'extraction': 'ಹಲ್ಲು ಹೊರಹಾಕುವುದು',
                'emergency': 'ತುರ್ತು ಸೇವೆ',
                'consultation': 'ಸಾಮಾನ್ಯ ಸಲಹೆ'
            },
            'te': {
                'cleaning': 'పళ్ల శుభ్రపరచడం లేదా తనిఖీ',
                'filling': 'ఫిల్లింగ్',
                'extraction': 'పళ్ల తొలుత',
                'emergency': 'అత్యవసర సేవ',
                'consultation': 'సాధారణ సలహా'
            },
            'ta': {
                'cleaning': 'பற் சுத்தம் அல்லது பரிசோதனை',
                'filling': 'நிரப்புதல்',
                'extraction': 'பல் எடுத்தல்',
                'emergency': 'அவசர சேவை',
                'consultation': 'பொதுவான ஆலோசனை'
            },
            'ml': {
                'cleaning': 'പല് വൃത്തിയാക്കൽ അല്ലെങ്കിൽ പരിശോധന',
                'filling': 'നിരത്തൽ',
                'extraction': 'പല് പറിച്ചെടുക്കൽ',
                'emergency': 'അടിയന്തര സേവന',
                'consultation': 'പൊതു ആലോചന'
            },
            'mr': {
                'cleaning': 'दांतांची स्वच्छता किंवा तपासणी',
                'filling': 'भरणे',
                'extraction': 'दाता हटवणे',
                'emergency': 'आपातकालीन सेवा',
                'consultation': 'सामान्य परामर्श'
            }
        }
        return examples.get(language.lower(), examples['en'])
    
    @staticmethod
    def generate_conversation_context(language: str) -> Dict:
        """
        Generate full conversation context for a language-aware session.
        This includes welcome message and next steps.
        """
        lang = language.lower()
        if lang not in WelcomeFlowGenerator.WELCOME_MESSAGES:
            lang = 'en'
        
        return {
            'language': lang,
            'tts_voice': WelcomeFlowGenerator.get_language_voice(lang),
            'welcome_message': WelcomeFlowGenerator.get_welcome_message(lang, 'full'),
            'next_guidance': WelcomeFlowGenerator.get_next_guidance_prompt(lang),
            'service_examples': WelcomeFlowGenerator.get_service_prompt_examples(lang),
            'is_welcome_complete': False
        }
