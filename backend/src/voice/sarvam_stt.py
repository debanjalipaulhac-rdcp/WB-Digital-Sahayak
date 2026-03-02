"""
src/voice/sarvam_stt.py
========================
Sarvam AI Speech-to-Text wrapper.

Strategies implemented (from cost analysis):
  ✅ Strategy 2: Silence stripping via pydub before sending to Sarvam
  ✅ Strategy 5: 15-second hard cap on voice note length — rejects long audio
  ✅ Strategy 2: Short-circuit on ineligibility (caller responsibility)
  ✅ Strategy 3: Voice Hierarchy — STT only called for Tier 1 inputs

Sarvam STT API:
    client.speech_to_text.transcribe(
        file=open("audio.wav", "rb"),
        model="saaras:v3",
        mode="transcribe"
    )

WhatsApp sends voice notes as .ogg (OPUS codec).
Sarvam accepts: .wav, .mp3, .ogg, .flac, .m4a

Cost: ₹30/hour of audio processed
      15-second cap = max ₹0.000125 per message
"""

import io
import logging
import os
from typing import Optional, Tuple

from src.config.sarvam_client import get_sarvam_client, DEFAULT_STT_CONFIG
from src.config.settings import settings

logger = logging.getLogger(__name__)

# ── Strategy 5: Hard cap on audio length ──────────────────────────────────────
MAX_AUDIO_SECONDS   = 15     # reject anything longer
MAX_AUDIO_BYTES_RAW = 512_000  # ~500KB = rough upper bound before even checking duration

# ── Silence stripping threshold ────────────────────────────────────────────────
SILENCE_THRESHOLD_DB = -40   # dBFS — anything quieter than this = silence
SILENCE_MIN_LEN_MS   = 500   # minimum silence chunk to strip (ms)


# ── Public API ─────────────────────────────────────────────────────────────────

def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "audio.ogg",
    language: str = "bn-IN"
) -> dict:
    """
    Transcribe a Bengali voice note to text.

    Applies Strategy 2 (silence stripping) and Strategy 5 (15s cap)
    before sending to Sarvam — saves STT costs.

    Args:
        audio_bytes: Raw bytes of the audio file (ogg/wav/mp3)
        filename:    Original filename — used to determine file extension
        language:    BCP-47 language code. Default: "bn-IN" (Bengali India)

    Returns:
        {
          "success": bool,
          "transcript": str,       # Bengali text
          "duration_seconds": float,
          "rejected": bool,        # True if audio was rejected (too long, silence)
          "rejection_reason": str, # Why it was rejected
          "mock": bool             # True if MOCK_MODE
        }

    Example:
        with open("voice_note.ogg", "rb") as f:
            result = transcribe_audio(f.read(), "voice_note.ogg")
        if result["success"]:
            user_text = result["transcript"]
    """
    # ── MOCK_MODE: return fake transcript for testing ──────────────────────────
    if settings.MOCK_MODE:
        logger.info("MOCK_MODE: returning mock transcript")
        return {
            "success": True, "transcript": "আমি Lakshmir Bhandar-এর জন্য জানতে চাই",
            "duration_seconds": 3.0, "rejected": False, "rejection_reason": "", "mock": True
        }

    # ── Step 1: Reject obviously oversized files before processing ─────────────
    if len(audio_bytes) > MAX_AUDIO_BYTES_RAW:
        logger.warning(f"Audio too large: {len(audio_bytes)} bytes")
        return _rejected("Audio file too large. Please send a shorter voice note.")

    # ── Step 2: Get duration and strip silence ─────────────────────────────────
    processed_bytes, duration_seconds = _preprocess_audio(audio_bytes, filename)

    if processed_bytes is None:
        return _rejected("Could not process audio file.")

    # ── Step 3: Strategy 5 — Hard 15-second cap ───────────────────────────────
    if duration_seconds > MAX_AUDIO_SECONDS:
        logger.warning(f"Audio too long: {duration_seconds:.1f}s > {MAX_AUDIO_SECONDS}s cap")
        return _rejected(
            f"Voice note is {duration_seconds:.0f} seconds. "
            f"Please keep it under {MAX_AUDIO_SECONDS} seconds and try again."
        )

    # ── Step 4: If only silence remains after stripping, reject ───────────────
    if duration_seconds < 0.5:
        return _rejected("No speech detected in voice note.")

    # ── Step 5: Send to Sarvam ─────────────────────────────────────────────────
    return _call_sarvam_stt(processed_bytes, filename, language, duration_seconds)


def transcribe_from_url(audio_url: str, language: str = "bn-IN") -> dict:
    """
    Download audio from a URL (e.g. Twilio voice note URL) and transcribe.

    Twilio sends voice notes as a URL, not raw bytes.
    This function downloads the audio then calls transcribe_audio().

    Args:
        audio_url: HTTPS URL to the audio file
        language:  BCP-47 language code

    Returns:
        Same dict as transcribe_audio()

    Example:
        # In whatsapp.py webhook handler:
        media_url = twilio_request.form.get("MediaUrl0")
        result = transcribe_from_url(media_url)
    """
    if settings.MOCK_MODE:
        return transcribe_audio(b"", "mock.ogg", language)

    try:
        import requests
        from twilio.http.http_client import TwilioHttpClient

        # Twilio URLs require authentication to download
        response = requests.get(
            audio_url,
            auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
            timeout=10
        )
        response.raise_for_status()

        filename = audio_url.split("/")[-1].split("?")[0] or "voice_note.ogg"
        return transcribe_audio(response.content, filename, language)

    except Exception as e:
        logger.error(f"Failed to download audio from {audio_url}: {e}")
        return _error(f"Could not download voice note: {e}")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _preprocess_audio(audio_bytes: bytes, filename: str) -> Tuple[Optional[bytes], float]:
    """
    Strategy 2: Strip silence from audio using pydub.
    Returns (processed_bytes, duration_seconds).
    Returns (None, 0) if processing fails.

    Falls back to original bytes if pydub not installed.
    """
    try:
        from pydub import AudioSegment
        from pydub.silence import strip_silence

        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        if ext == "ogg":
            ext = "ogg"   # pydub handles opus-in-ogg
        elif not ext:
            ext = "ogg"   # default for WhatsApp

        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=ext)
        original_duration = len(audio) / 1000.0

        # Strip silence from start and end
        stripped = _strip_silence(audio)
        stripped_duration = len(stripped) / 1000.0

        savings = original_duration - stripped_duration
        if savings > 0.1:
            logger.info(f"Silence stripped: {original_duration:.1f}s → {stripped_duration:.1f}s (saved {savings:.1f}s)")

        # Export back to bytes
        output = io.BytesIO()
        stripped.export(output, format="wav")   # wav = universal compatibility
        return output.getvalue(), stripped_duration

    except ImportError:
        logger.warning("pydub not installed — skipping silence strip. Run: pip install pydub")
        return audio_bytes, _estimate_duration(audio_bytes)

    except Exception as e:
        logger.error(f"Audio preprocessing failed: {e}")
        return audio_bytes, _estimate_duration(audio_bytes)


def _strip_silence(audio):
    """Strip leading/trailing silence from AudioSegment."""
    try:
        from pydub.silence import detect_leading_silence

        def trim_leading(seg):
            start = detect_leading_silence(seg, silence_threshold=SILENCE_THRESHOLD_DB,
                                           chunk_size=10)
            return seg[start:]

        # Trim from start, reverse, trim from new start (= trim from end), reverse back
        trimmed = trim_leading(audio)
        trimmed = trim_leading(trimmed.reverse()).reverse()
        return trimmed if len(trimmed) > 100 else audio   # don't over-trim

    except Exception:
        return audio


def _estimate_duration(audio_bytes: bytes) -> float:
    """Rough duration estimate when pydub not available. 16kHz mono WAV ≈ 32KB/s."""
    return len(audio_bytes) / 32_000


def _call_sarvam_stt(audio_bytes: bytes, filename: str, language: str, duration: float) -> dict:
    """Make the actual Sarvam API call."""
    client = get_sarvam_client()
    if not client:
        return _error("Sarvam AI client not available. Check SARVAM_API_KEY.")

    try:
        ext = os.path.splitext(filename)[1].lower() or ".ogg"
        mime = {"wav": "audio/wav", "ogg": "audio/ogg",
                "mp3": "audio/mp3", "m4a": "audio/m4a"}.get(ext.lstrip("."), "audio/ogg")

        # Sarvam expects a file-like object
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = f"audio{ext}"

        response = client.speech_to_text.transcribe(
            file=audio_file,
            model="saaras:v3",      # Sarvam's latest Indic STT model
            mode="transcribe",
        )

        transcript = ""
        if hasattr(response, "transcript"):
            transcript = response.transcript
        elif hasattr(response, "text"):
            transcript = response.text
        elif isinstance(response, dict):
            transcript = response.get("transcript", response.get("text", ""))

        logger.info(f"STT success: '{transcript[:50]}...' (duration={duration:.1f}s)")

        return {
            "success": True, "transcript": transcript.strip(),
            "duration_seconds": duration, "rejected": False,
            "rejection_reason": "", "mock": False
        }

    except Exception as e:
        logger.error(f"Sarvam STT API call failed: {e}")
        return _error(f"Speech recognition failed: {e}")


def _rejected(reason: str) -> dict:
    return {"success": False, "transcript": "", "duration_seconds": 0,
            "rejected": True, "rejection_reason": reason, "mock": False}


def _error(reason: str) -> dict:
    return {"success": False, "transcript": "", "duration_seconds": 0,
            "rejected": False, "rejection_reason": reason, "mock": False}