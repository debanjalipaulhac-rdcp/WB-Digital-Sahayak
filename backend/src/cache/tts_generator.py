"""
src/cache/tts_generator.py
Generates TTS for cache-miss chunks via Sarvam SDK.

Uses ThreadPoolExecutor — NOT asyncio.
Reason: this runs inside a daemon thread (started by whatsapp.py).
asyncio.run() inside a thread causes RuntimeError on Windows and
unpredictable behavior on Lambda. ThreadPoolExecutor is safe anywhere.

Flow per chunk:
  Sarvam SDK → WAV bytes (b'RIFF') → wav_to_ogg() → OGG/Vorbis → S3
"""

import base64
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from src.storage.s3 import upload_audio
from src.voice.audio_converter import wav_to_ogg

logger = logging.getLogger(__name__)

CHUNK_S3_PREFIX = "chunks/"
AUDIO_EXT       = ".ogg"
CONTENT_TYPE    = "audio/ogg"
MAX_WORKERS     = 5   # stay under Sarvam rate limit

VOICE_MAP = {
    "bn-IN": "kavitha",
    "hi-IN": "suhani",
    "en-IN": "shruti"
}


def _chunk_s3_key(chunk_text: str, language_code: str) -> str:
    chunk_hash = hashlib.md5(chunk_text.encode("utf-8")).hexdigest()[:8]
    lang_short = language_code.replace("-", "_")
    return f"{CHUNK_S3_PREFIX}{lang_short}/{chunk_hash}{AUDIO_EXT}"


def _generate_single(chunk_text: str, language_code: str) -> tuple[str, Optional[bytes]]:
    """
    Generate TTS for one chunk. Runs in ThreadPoolExecutor worker.
    Returns (chunk_text, ogg_bytes) or (chunk_text, None) on any failure.
    """
    try:
        from src.config.sarvam_client import get_sarvam_client

        client = get_sarvam_client()
        voice  = VOICE_MAP.get(language_code, "maya")

        response = client.text_to_speech.convert(
            text=chunk_text,
            model="bulbul:v3",
            target_language_code=language_code,
            speaker=voice,
            speech_sample_rate=16000,
            pace=1.2
        )

        # SDK returns list of base64 strings or raw bytes — handle both
        raw = response.audios[0] if response.audios else None
        if raw is None:
            logger.error(f"Sarvam returned empty audio for '{chunk_text[:40]}'")
            return chunk_text, None

        wav_bytes = base64.b64decode(raw) if isinstance(raw, str) else raw

        # Convert WAV → OGG/Vorbis for WhatsApp
        ogg_bytes = wav_to_ogg(wav_bytes)
        if not ogg_bytes:
            logger.warning(f"wav_to_ogg failed for '{chunk_text[:40]}' — skipping")
            return chunk_text, None

        return chunk_text, ogg_bytes

    except Exception as e:
        logger.error(f"_generate_single failed for '{chunk_text[:40]}': {e}")
        return chunk_text, None


def generate_for_misses(miss_chunks: list[str], language_code: str) -> dict[str, str]:
    """
    Generate TTS + convert + upload for all cache-miss chunks.
    Returns {chunk_text: s3_url} for successful chunks only.

    Sets generate_for_misses._last_generated so whatsapp.py can
    pass it to save_new_chunks_async without circular imports.
    """
    if not miss_chunks:
        return {}

    logger.info(f"TTS: generating {len(miss_chunks)} misses [{language_code}]")

    result:        dict[str, str] = {}
    to_save_later: list[dict]     = []

    # ThreadPoolExecutor — safe inside daemon threads, no event loop issues
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(miss_chunks))) as pool:
        futures = {
            pool.submit(_generate_single, chunk, language_code): chunk
            for chunk in miss_chunks
        }
        for future in as_completed(futures):
            chunk_text, ogg_bytes = future.result()

            if ogg_bytes is None:
                logger.warning(f"  SKIP (TTS failed): '{chunk_text[:40]}'")
                continue

            s3_key = _chunk_s3_key(chunk_text, language_code)
            url    = upload_audio(ogg_bytes, s3_key)

            if url:
                result[chunk_text] = url
                to_save_later.append({"chunk_text": chunk_text, "audio_url": url})
                logger.info(f"  OK: '{chunk_text[:40]}' → {s3_key}")
            else:
                logger.error(f"  S3 FAIL: '{chunk_text[:40]}'")

    # Attach for whatsapp.py to pick up and pass to background_saver
    generate_for_misses._last_generated = to_save_later

    logger.info(f"TTS done: {len(result)}/{len(miss_chunks)} succeeded")
    return result