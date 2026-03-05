"""
src/cache/tts_generator.py
Generates TTS audio for cache-miss chunks ONLY.
Never called for chunks already in S3/DynamoDB.
Runs in parallel for multiple misses using asyncio.
"""

import os
import asyncio
import base64
import logging
from typing import Optional

import aiohttp

from src.storage.s3 import upload_audio, get_audio_url

logger = logging.getLogger(__name__)

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"

VOICE_MAP = {
    "bn-IN": "kavitha",   # Bengali female voice
    "hi-IN": "suhani",     # Hindi female voice
    "en-IN": "shruti"       # English Indian accent
}

CHUNK_S3_PREFIX = "chunks/"
from src.voice.audio_converter import wav_to_ogg

def _chunk_s3_key(chunk_text: str, language_code: str) -> str:
    import hashlib
    chunk_hash = hashlib.md5(chunk_text.encode("utf-8")).hexdigest()[:8]
    lang_short = language_code.replace("-", "_")
    return f"{CHUNK_S3_PREFIX}{lang_short}/{chunk_hash}.ogg"

from src.config.sarvam_client import get_sarvam_client

async def _generate_single(
    session: aiohttp.ClientSession,
    chunk_text: str,
    language_code: str
) -> tuple[str, Optional[bytes]]:
    """
    Generate TTS for one chunk. Returns (chunk_text, audio_bytes or None).
    """
    client =get_sarvam_client()
    try:
        VOICE_MAP = {
            "bn-IN": "kavitha",   # Bengali female voice
            "hi-IN": "suhani",     # Hindi female voice
            "en-IN": "shruti"       # English Indian accent
        }
        voice = VOICE_MAP.get(language_code, "maya")
        response = client.text_to_speech.convert(
                        text=chunk_text,
                        model="bulbul:v3",
                        target_language_code=language_code,
                        speaker=voice,
                        speech_sample_rate=16000,
                        pace=1.2
                    )
        combined_audio = "".join(response.audios)
        wav_bytes =base64.b64decode(combined_audio) if isinstance(combined_audio, str) else combined_audio
        ogg_bytes = wav_to_ogg(wav_bytes)
        if not ogg_bytes:
            logger.warning(f"OGG conversion failed for '{chunk_text[:40]}' - using WAV fallback")
            return chunk_text, combined_audio
        
        # b64_file = base64.b64decode(combined_audio)
        return chunk_text, ogg_bytes

    except asyncio.TimeoutError:
        logger.error(f"TTS timeout for chunk: '{chunk_text[:40]}'")
        return chunk_text, None
    except aiohttp.ClientError as e:
        logger.error(f"TTS request failed for '{chunk_text[:40]}': {e}")
        return chunk_text, None
    except (KeyError, IndexError) as e:
        logger.error(f"TTS unexpected response for '{chunk_text[:40]}': {e}")
        return chunk_text, None


async def _generate_all_async(
    miss_chunks: list[str],
    language_code: str
) -> dict[str, Optional[bytes]]:
    """Generate TTS for all miss chunks in parallel."""
    async with aiohttp.ClientSession() as session:
        tasks = [
            _generate_single(session, chunk, language_code)
            for chunk in miss_chunks
        ]
        results = await asyncio.gather(*tasks)
    return dict(results)


def generate_for_misses(
    miss_chunks: list[str],
    language_code: str
) -> dict[str, str]:
    """
    Generate TTS audio for all cache-miss chunks.
    Runs all TTS calls in parallel.
    Uploads to S3 immediately so URLs are available for assembly.
    Background saving to DynamoDB is handled by background_saver.py separately.

    Returns: {normalized_chunk_text: s3_url}
    Only includes chunks that generated successfully.
    """
    if not miss_chunks:
        return {}

    logger.info(f"Generating TTS for {len(miss_chunks)} cache misses [{language_code}]")

    # Run all TTS calls in parallel
    try:
        audio_map = asyncio.run(_generate_all_async(miss_chunks, language_code))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_map = loop.run_until_complete(
            _generate_all_async(miss_chunks, language_code)
        )

    # Upload to S3 — must happen before assembly
    result: dict[str, str] = {}
    to_save_later: list[dict] = []   # handed to background_saver

    for chunk_text, audio_bytes in audio_map.items():
        if audio_bytes is None:
            logger.warning(f"TTS failed for chunk: '{chunk_text[:40]}'")
            continue

        s3_key = _chunk_s3_key(chunk_text, language_code)
        url = upload_audio(audio_bytes, s3_key)

        if url:
            result[chunk_text] = url
            to_save_later.append({"chunk_text": chunk_text, "audio_url": url})
            logger.info(f"  ✅ Generated+uploaded: '{chunk_text[:40]}'")
        else:
            logger.error(f"  ❌ S3 upload failed for: '{chunk_text[:40]}'")

    # Attach to_save_later as attribute so caller can pass to background_saver
    # without creating a circular import
    generate_for_misses._last_generated = to_save_later

    logger.info(
        f"TTS generation complete: {len(result)}/{len(miss_chunks)} succeeded"
    )
    return result