"""
src/voice/stt.py
Sarvam AI Speech-to-Text wrapper.
Converts audio bytes → transcript + detected language code.
Called ONLY when user sends a voice message (not text).
"""

import os
import logging
import base64
from dataclasses import dataclass
from src.config.sarvam_client import get_sarvam_client
import requests
import io
logger = logging.getLogger(__name__)
from .transcript_normalizer import normalize_transcript
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"

# Languages Sarvam STT can detect and return
SUPPORTED_LANGUAGES = {"bn-IN", "hi-IN", "en-IN", "te-IN", "ta-IN", "mr-IN"}
DEFAULT_LANGUAGE    = "bn-IN"   # WB context — Bengali is most likely


@dataclass
class STTResult:
    transcript:    str            # Raw transcript text
    language_code: str            # e.g. "bn-IN" — from stt_response.language_code
    confidence:    float          # 0.0–1.0, if available
    is_fallback:   bool           # True if STT failed and we returned empty


def transcribe_audio(audio_bytes: bytes, hint_language: str = "bn-IN") -> STTResult:
    """
    Send audio bytes to Sarvam STT.
    Returns STTResult with transcript + detected language.

    audio_bytes: raw audio (ogg, mp3, wav — Sarvam accepts all)
    hint_language: language hint to improve accuracy (from user profile if known)

    On failure: returns STTResult with empty transcript and is_fallback=True
    so upstream can handle gracefully (ask user to re-send or switch to text).
    """

    try:
        # Sarvam accepts base64-encoded audio in JSON body
        # audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.ogg"
        # print("audio_b64:", audio_file)
        client= get_sarvam_client()
        data = client.speech_to_text.transcribe(
                file=audio_file,
                model="saaras:v3",
                mode="translate",
            )
        print(data.transcript)
        transcript    = (getattr(data, "transcript", "") or "").strip()
        language_code = getattr(data, "language_code","")
        confidence    = float(getattr(data, "confidence", 1.0) or 1.0)

        print(language_code,data.language_code)
        # Normalize language code — Sarvam sometimes returns just "bn"
        # language_code = _normalize_language_code(language_code)
        transcript=normalize_transcript(transcript)
        logger.info(f"STT success: lang={language_code}, confidence={confidence:.2f}, "
                    f"transcript='{transcript[:60]}'")

        return STTResult(
            transcript=transcript,
            language_code=language_code,
            confidence=confidence,
            is_fallback=False
        )

    except requests.Timeout:
        logger.error("Sarvam STT timed out (>15s)")
        return STTResult(transcript="", language_code=hint_language,
                         confidence=0.0, is_fallback=True)

    except requests.RequestException as e:
        logger.error(f"Sarvam STT request failed: {e}")
        return STTResult(transcript="", language_code=hint_language,
                         confidence=0.0, is_fallback=True)

    except (KeyError, ValueError) as e:
        logger.error(f"Sarvam STT unexpected response format: {e}")
        return STTResult(transcript="", language_code=hint_language,
                         confidence=0.0, is_fallback=True)


# def _normalize_language_code(code: str) -> str:
    """
    Normalize Sarvam language codes to our standard format.
    "bn" → "bn-IN", "hi" → "hi-IN", "en" → "en-IN"
    Already-normalized codes like "bn-IN" pass through unchanged.
    Unknown codes → DEFAULT_LANGUAGE.
    """
    code = code.strip().lower()

    # Already full format
    if code in SUPPORTED_LANGUAGES:
        return code

    # Short code → expand
    short_to_full = {
        "bn": "bn-IN",
        "hi": "hi-IN",
        "en": "en-IN",
        "te": "te-IN",
        "ta": "ta-IN",
        "mr": "mr-IN",
    }
    if code in short_to_full:
        return short_to_full[code]

    logger.warning(f"Unknown language code from STT: '{code}' — defaulting to {DEFAULT_LANGUAGE}")
    return DEFAULT_LANGUAGE