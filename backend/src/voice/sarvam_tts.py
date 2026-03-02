"""
src/voice/sarvam_tts.py
========================
Sarvam AI Text-to-Speech wrapper.

Strategies implemented:
  ✅ Strategy 1: Cache-first — check S3 before calling Sarvam API
  ✅ Strategy 1: Static phrases pre-generated and served from S3
  ✅ Strategy 3: Voice Hierarchy — only Tier 1 messages use TTS
  ✅ Strategy 3: Tier 2 messages return text only (free)

Sarvam TTS API:
    response = client.text_to_speech.convert(
        text="Hello, how are you today?",
        target_language_code="en-IN",
        model="bulbul:v3"
    )

Cost: ₹20 per 10,000 characters of TTS
      With caching, most requests cost ₹0 (served from S3)
"""

import logging
from typing import Optional, Tuple

from src.config.sarvam_client import (
    get_sarvam_client, DEFAULT_TTS_CONFIG,
    BENGALI, GENDER_FEMALE
)
from src.config.settings import settings
from src.storage.s3 import audio_exists, upload_audio, get_audio_url

logger = logging.getLogger(__name__)

# ── Voice Hierarchy (Strategy 3) ──────────────────────────────────────────────
# Tier 1: High importance — use TTS (voice)
# Tier 2: Low importance — use text only (free)

TIER_1_MESSAGE_TYPES = {
    "score_reveal",      # "Your score is 42/100 — RED"
    "mismatch_alert",    # "Name mismatch detected on Aadhaar and Bank"
    "office_script",     # "Go to the bank and say: ..."
    "welcome",           # First message in conversation
    "result_summary",    # Full eligibility result
}

TIER_2_MESSAGE_TYPES = {
    "confirmation",      # "Got it. Processing..."
    "prompt",            # "What is your age?"
    "acknowledgement",   # "Thank you"
    "error",             # "Sorry, I didn't understand"
}

# ── Character limit per TTS call ───────────────────────────────────────────────
MAX_TTS_CHARS = 500   # Sarvam API limit per call; split longer text


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_audio(
    text: str,
    cache_key: str = None,
    language: str = BENGALI,
    gender: str = GENDER_FEMALE,
    message_type: str = "score_reveal",
) -> Tuple[Optional[str], Optional[bytes]]:
    """
    Generate Bengali audio for a text string.
    Implements Strategy 1: cache-first — S3 before Sarvam.
    Implements Strategy 3: only Tier 1 messages get audio.

    Args:
        text:         Bengali text to convert to speech
        cache_key:    S3 filename for caching e.g. "name_mismatch_bn.ogg"
                      If None, audio is generated but NOT cached (for dynamic text)
        language:     BCP-47 language code (default: "bn-IN")
        gender:       "Female" | "Male" (default: "Female")
        message_type: Tier classification — determines if TTS is used

    Returns:
        Tuple of (s3_url_or_none, audio_bytes_or_none)
        - If cached: (presigned_url, None)  — serve URL to Twilio
        - If generated: (presigned_url, bytes) — after uploading to S3
        - If Tier 2: (None, None) — use text message instead
        - If error: (None, None)

    Example:
        url, _ = generate_audio(
            text="আপনার নামে গরমিল আছে।",
            cache_key="name_mismatch_bn.ogg",
            message_type="mismatch_alert"
        )
        if url:
            send_voice_note(url)   # Twilio fetches this URL
        else:
            send_text_message(text)  # fallback to text
    """
    # ── Strategy 3: Tier 2 messages → text only, skip TTS ────────────────────
    if message_type in TIER_2_MESSAGE_TYPES:
        logger.debug(f"Tier 2 message ({message_type}) — skipping TTS, use text")
        return None, None

    # ── MOCK_MODE ─────────────────────────────────────────────────────────────
    if settings.MOCK_MODE:
        logger.info(f"MOCK_MODE: returning mock audio URL for '{text[:30]}...'")
        return f"https://mock-s3.example.com/{cache_key or 'mock.ogg'}", None

    # ── Strategy 1: Check S3 cache first ─────────────────────────────────────
    if cache_key and audio_exists(cache_key):
        logger.debug(f"TTS cache hit: {cache_key}")
        url = get_audio_url(cache_key)
        return url, None

    # ── Generate via Sarvam ───────────────────────────────────────────────────
    if not settings.SARVAM_API_KEY:
        logger.error("SARVAM_API_KEY not set — TTS unavailable")
        return None, None

    audio_bytes = _call_sarvam_tts(text, language, gender)
    if not audio_bytes:
        return None, None

    # ── Upload to S3 cache if cache_key provided ───────────────────────────────
    if cache_key:
        uploaded = upload_audio(audio_bytes, cache_key)
        if uploaded:
            url = get_audio_url(cache_key)
            logger.info(f"TTS generated + cached: {cache_key}")
            return url, audio_bytes
        else:
            logger.warning(f"TTS generated but S3 upload failed for {cache_key}")

    # Return bytes directly if no cache_key or upload failed
    return None, audio_bytes


def generate_score_audio(score: int, band: str, scheme_name: str) -> Tuple[Optional[str], Optional[bytes]]:
    """
    Generate audio for score reveal.
    Score number is dynamic so NOT cached — called live each time.

    The text is short so cost is minimal (~₹0.001 per call).

    Example:
        url, _ = generate_score_audio(42, "RED", "Lakshmir Bhandar")
    """
    band_phrases = {
        "GREEN": "আপনি প্রস্তুত। আগামীকালই BDO office যেতে পারেন।",
        "AMBER": "কিছু সমস্যা আছে। আগে ঠিক করুন, তারপর যান।",
        "RED":   "এখনই যাবেন না। আগে roadmap অনুসরণ করুন।"
    }
    verdict = band_phrases.get(band, "")
    text = f"আপনার {scheme_name} Readiness Score {score} এর মধ্যে ১০০। {verdict}"

    return generate_audio(
        text=text,
        cache_key=None,       # dynamic — don't cache
        message_type="score_reveal"
    )


def generate_issue_audio(issue_code: str) -> Tuple[Optional[str], Optional[bytes]]:
    """
    Generate audio for a specific issue.
    Uses cached S3 file if available — matches AUDIO_CACHE_MANIFEST.

    Example:
        url, _ = generate_issue_audio("NAME_MISMATCH")
    """
    from src.storage.s3 import AUDIO_CACHE_MANIFEST
    entry = AUDIO_CACHE_MANIFEST.get(issue_code)
    if not entry:
        logger.warning(f"No audio manifest entry for issue: {issue_code}")
        return None, None

    text_bn, filename = entry
    return generate_audio(
        text=text_bn,
        cache_key=filename,
        message_type="mismatch_alert"
    )


def generate_welcome_audio() -> Tuple[Optional[str], Optional[bytes]]:
    """Generate or serve cached welcome message."""
    from src.storage.s3 import AUDIO_CACHE_MANIFEST
    text_bn, filename = AUDIO_CACHE_MANIFEST["WELCOME"]
    return generate_audio(text=text_bn, cache_key=filename, message_type="welcome")


def is_tier1(message_type: str) -> bool:
    """Check if a message type warrants TTS (Tier 1)."""
    return message_type in TIER_1_MESSAGE_TYPES


# ── Internal helpers ──────────────────────────────────────────────────────────

def _call_sarvam_tts(text: str, language: str, gender: str) -> Optional[bytes]:
    """
    Make the actual Sarvam TTS API call.
    Splits long text if it exceeds MAX_TTS_CHARS.
    Returns raw audio bytes or None.
    """
    client = get_sarvam_client()
    if not client:
        return None

    # Split long text into chunks
    chunks = _split_text(text, MAX_TTS_CHARS)
    all_audio = []

    for chunk in chunks:
        try:
            response = client.text_to_speech.convert(
                text=chunk,
                target_language_code=language,
                model="bulbul:v2",          # Sarvam's Indic TTS model
                speaker_gender=gender,
                speech_sample_rate=8000,    # 8kHz = WhatsApp voice note compatible
                enable_preprocessing=True,  # handles mixed Bengali-English text
                pitch=0,
                pace=1.0,
                loudness=1.0,
            )

            # Sarvam SDK returns audio bytes directly
            if hasattr(response, "audio_data") and response.audio_data:
                all_audio.append(response.audio_data)
            elif isinstance(response, bytes):
                all_audio.append(response)
            else:
                logger.error(f"Unexpected Sarvam TTS response type: {type(response)}")
                return None

        except Exception as e:
            logger.error(f"Sarvam TTS API call failed: {e}")
            return None

    if not all_audio:
        return None

    # Concatenate chunks if multiple
    return b"".join(all_audio)


def _split_text(text: str, max_chars: int) -> list[str]:
    """
    Split text into chunks at sentence boundaries.
    Sarvam has a per-call character limit.
    """
    if len(text) <= max_chars:
        return [text]

    chunks = []
    # Split on sentence endings first
    sentences = text.replace("।", "।|").replace(".", ".|").split("|")
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) <= max_chars:
            current += sentence
        else:
            if current:
                chunks.append(current.strip())
            current = sentence

    if current:
        chunks.append(current.strip())

    return chunks if chunks else [text[:max_chars]]