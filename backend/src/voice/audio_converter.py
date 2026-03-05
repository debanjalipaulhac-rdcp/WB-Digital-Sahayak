"""
src/voice/audio_converter.py
Converts WAV bytes (Sarvam TTS output) → OGG/Vorbis bytes for WhatsApp delivery.

Format chain:
  Sarvam SDK → WAV bytes (b'RIFF') → soundfile → OGG/Vorbis → S3 → Twilio → WhatsApp

WHY OGG/VORBIS not OGG/OPUS:
  soundfile can WRITE OGG/Vorbis natively (libsndfile always ships with Vorbis support).
  soundfile CANNOT reliably write OGG/Opus (libsndfile Opus write is broken in pip builds).
  WhatsApp accepts both OGG/Vorbis and OGG/Opus — Vorbis works fine.

COMPRESSION: WAV ~1.4MB/min → OGG ~120KB/min (~10x smaller)
"""
import io
import logging
from typing import Optional

import soundfile as sf

logger = logging.getLogger(__name__)


def wav_to_ogg(wav_bytes: bytes) -> Optional[bytes]:
    """
    Convert WAV bytes → OGG/Vorbis bytes.
    Returns OGG bytes on success, None on failure.
    Pure in-memory — no temp files, no disk I/O.
    """
    try:
        input_buf  = io.BytesIO(wav_bytes)
        output_buf = io.BytesIO()

        data, samplerate = sf.read(input_buf, dtype="float32")
        sf.write(output_buf, data, samplerate, format="OGG", subtype="VORBIS")

        output_buf.seek(0)
        ogg_bytes = output_buf.read()

        logger.debug(
            f"wav_to_ogg: {len(wav_bytes):,}B WAV → {len(ogg_bytes):,}B OGG "
            f"({100 * len(ogg_bytes) // len(wav_bytes)}% of original)"
        )
        return ogg_bytes

    except Exception as e:
        logger.error(f"wav_to_ogg failed: {e} — caller should fall back to raw WAV")
        return None


def verify_ogg(ogg_bytes: bytes) -> bool:
    """Quick sanity check — OGG files always start with 'OggS'."""
    return ogg_bytes[:4] == b"OggS"