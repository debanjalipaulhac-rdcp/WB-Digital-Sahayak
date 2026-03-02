"""
config/sarvam_client.py
========================
Sarvam AI client for Bengali STT and TTS.

Sarvam AI is an Indian AI company that builds
models specifically for Indic languages.
We use it because Google TTS sounds robotic in Bengali.
Sarvam handles rural Bengali dialect naturally.

Services we use:
  - STT (Speech-to-Text): Convert Bengali voice notes to text
  - TTS (Text-to-Speech): Convert Bengali text to voice notes
  - Translate: Translate between languages (bonus feature)

Docs: https://docs.sarvam.ai
API Key: https://www.sarvam.ai → Dashboard → API Keys

Usage:
    from config.sarvam_client import get_sarvam_client
    client = get_sarvam_client()

    # STT
    result = client.speech.to_text(audio_file, language="bn-IN")

    # TTS
    audio = client.text.to_speech(text="আপনার নামে গরমিল আছে", language="bn-IN")

    # Translate
    translated = client.text.translate(
        input="Fix your name mismatch",
        source_language_code="en-IN",
        target_language_code="bn-IN"
    )
"""

import logging
from src.config.settings import settings

logger = logging.getLogger(__name__)


def get_sarvam_client():
    """
    Returns an initialised Sarvam AI client.

    Requires: pip install sarvamai
    API key must be set in .env.local as SARVAM_API_KEY

    Returns None in MOCK_MODE so voice pipeline
    can fall back to text without crashing.

    Example:
        client = get_sarvam_client()
        if client is None:
            return "Mock TTS response"  # MOCK_MODE fallback
    """
    if settings.MOCK_MODE:
        logger.warning("MOCK_MODE=true — Sarvam AI client not initialised. Voice will use fallback.")
        return None

    if not settings.SARVAM_API_KEY:
        logger.error("SARVAM_API_KEY is not set. Voice pipeline will fail.")
        return None

    try:
        from sarvamai import SarvamAI
        client = SarvamAI(api_subscription_key=settings.SARVAM_API_KEY)
        logger.info("✅ Sarvam AI client initialised")
        return client

    except ImportError:
        logger.error("sarvamai package not installed. Run: pip install sarvamai")
        return None

    except Exception as e:
        logger.error(f"Failed to initialise Sarvam AI client: {e}")
        return None


def get_sarvam_headers() -> dict:
    """
    Returns HTTP headers for direct Sarvam API calls (requests library).
    Used in sarvam_stt.py and sarvam_tts.py as a fallback
    if the sarvamai SDK is not available.

    Example:
        import requests
        headers = get_sarvam_headers()
        response = requests.post(
            settings.SARVAM_STT_ENDPOINT,
            headers=headers,
            files={"file": audio_bytes}
        )
    """
    return {
        "api-subscription-key": settings.SARVAM_API_KEY,
        "Content-Type": "application/json",
    }


# ── Language code constants ────────────────────────────────────────────────────
# Use these instead of raw strings to avoid typos
BENGALI    = "bn-IN"
HINDI      = "hi-IN"
ENGLISH_IN = "en-IN"
ODIA       = "or-IN"
SANTALI    = "sat-IN"   # Phase 3 — tribal dialect support

# ── Speaker gender options ─────────────────────────────────────────────────────
GENDER_FEMALE = "Female"
GENDER_MALE   = "Male"

# ── Default config for our use case ───────────────────────────────────────────
DEFAULT_TTS_CONFIG = {
    "target_language_code": BENGALI,
    "speaker_gender": GENDER_FEMALE,    # Most Lakshmir Bhandar users are women
    "pitch": 0,                          # 0 = natural pitch
    "pace": 1.0,                         # 1.0 = normal speed
    "loudness": 1.0,
    "speech_sample_rate": 8000,          # 8kHz = WhatsApp voice note compatible
    "enable_preprocessing": True,        # Handles mixed Bengali-English text
    "model": "bulbul:v1",               # Sarvam's Indic TTS model
}

DEFAULT_STT_CONFIG = {
    "language_code": BENGALI,
    "model": "saarika:v2",              # Sarvam's Indic STT model
    "with_timestamps": False,
    "with_disfluencies": False,         # Remove "um", "uh" from transcript
}

DEFAULT_TRANSLATE_CONFIG = {
    "source_language_code": "auto",     # Auto-detect source language
    "target_language_code": BENGALI,
    "speaker_gender": GENDER_FEMALE,
    "enable_preprocessing": True,
    "numerals_format": "international",
}