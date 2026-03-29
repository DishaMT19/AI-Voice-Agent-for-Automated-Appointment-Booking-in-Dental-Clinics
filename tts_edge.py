# tts_edge.py - Enhanced TTS with multilingual support
"""
Text-to-Speech implementation using Edge TTS (Microsoft).
Supports multiple languages and voices for professional dental receptionist audio.
"""

import os
import uuid
import asyncio
import logging
import edge_tts  # pip install edge-tts

# Logging
logger = logging.getLogger(__name__)

# Output directory for generated audio
OUT_DIR = "generated_audio"
os.makedirs(OUT_DIR, exist_ok=True)

# Supported voices by language
VOICES = {
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

def get_voice(language: str = 'en', gender: str = 'female') -> str:
    """
    Get the appropriate voice for the specified language and gender.
    
    Args:
        language: Language code (en, hi, kn, te, ta, ml, mr)
        gender: 'male' or 'female' (default: female)
    
    Returns:
        Voice name for edge-tts
    """
    lang = language.lower()
    gender_key = 'female' if gender.lower() != 'male' else 'male'
    
    if lang not in VOICES:
        logger.warning(f"Unsupported language: {lang}. Using English.")
        lang = 'en'
    
    return VOICES[lang].get(gender_key, VOICES['en']['female'])

async def _speak_to_file(text: str, filename: str, voice: str = 'en-US-JennyNeural') -> None:
    """
    Generate speech audio file from text.
    
    Args:
        text: Text to convert to speech
        filename: Output filename
        voice: Voice name (default: English female)
    """
    try:
        logger.debug(f"Generating TTS: voice={voice}, text_length={len(text)}")
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(filename)
        logger.info(f"TTS file generated: {filename}")
    except Exception as e:
        logger.error(f"TTS generation failed: {str(e)}")
        raise

def ensure_mp3_name() -> str:
    """Generate a unique output filename for audio."""
    return os.path.join(OUT_DIR, f"{uuid.uuid4().hex}.mp3")

async def _speak_async(text: str, language: str = 'en', gender: str = 'female') -> str:
    """
    Generate speech asynchronously.
    
    Args:
        text: Text to convert to speech
        language: Language code for voice selection
        gender: Voice gender ('male' or 'female')
    
    Returns:
        Path to generated audio file
    """
    voice = get_voice(language, gender)
    output_path = ensure_mp3_name()
    await _speak_to_file(text, output_path, voice)
    return output_path.replace("\\", "/")

def speak_edge_sync(text: str, language: str = 'en', gender: str = 'female') -> str:
    """
    Generate speech synchronously (blocking).
    
    Args:
        text: Text to convert to speech
        language: Language code for voice selection
        gender: Voice gender ('male' or 'female')
    
    Returns:
        Path to generated audio file
    """
    return asyncio.run(_speak_async(text, language, gender))

async def speak_edge(text: str, language: str = 'en', gender: str = 'female') -> str:
    """
    Generate speech asynchronously.
    Preferred method for Flask/async applications.
    
    Args:
        text: Text to convert to speech
        language: Language code for voice selection
        gender: Voice gender ('male' or 'female')
    
    Returns:
        Path to generated audio file
    """
    return await _speak_async(text, language, gender)

async def generate_welcome_audio(welcome_message: str, language: str = 'en') -> str:
    """
    Generate professional welcome message audio.
    Optimized for dental receptionist context.
    
    Args:
        welcome_message: Welcome text to speak
        language: Language code
    
    Returns:
        Path to generated audio file
    """
    # Use female voice for welcome message (professional and friendly)
    return await speak_edge(welcome_message, language, gender='female')

