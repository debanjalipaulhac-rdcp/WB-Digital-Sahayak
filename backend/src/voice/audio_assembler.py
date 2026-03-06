"""
src/voice/audio_assembler.py
Downloads .ogg chunks from S3 via boto3, concatenates raw bytes, uploads combined.

OGG streams are byte-concatenable — no re-encoding needed.
Chunks are already OGG/Vorbis (converted by tts_generator at generation time).
DO NOT run wav_to_ogg here — chunks are already OGG, not WAV.
"""

import logging
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
from urllib.parse import urlparse

from src.storage.s3 import upload_audio, get_s3_client
from src.config.settings import settings

logger = logging.getLogger(__name__)

COMBINED_AUDIO_PREFIX = "combined/"
MAX_WORKERS           = 5


def _s3_key_from_url(url: str) -> str:
    return urlparse(url).path.lstrip("/")


def _download_one(url: str) -> tuple[str, Optional[bytes]]:
    """Download one S3 object via boto3 — no public access needed."""
    try:
        key    = _s3_key_from_url(url)
        client = get_s3_client()
        resp   = client.get_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
        return url, resp["Body"].read()
    except Exception as e:
        logger.error(f"Failed to download chunk '{url}': {e}")
        return url, None


def _make_combined_key(chunk_urls: list[str]) -> str:
    hash_val = hashlib.md5("|".join(chunk_urls).encode()).hexdigest()[:16]
    return f"{COMBINED_AUDIO_PREFIX}{hash_val}.ogg"


def assemble_audio(chunk_urls: list[str]) -> Optional[str]:
    """
    Download .ogg chunks, concatenate bytes, upload combined .ogg.

    IMPORTANT: chunks are already OGG/Vorbis from tts_generator.
    Raw OGG byte concatenation is valid for the OGG container format.
    Do NOT call wav_to_ogg here — that corrupts the already-converted audio.
    """
    if not chunk_urls:
        logger.error("assemble_audio: empty chunk_urls")
        return None

    # Single chunk — return directly, no assembly needed
    if len(chunk_urls) == 1:
        return chunk_urls[0]

    # Download all in parallel
    url_to_bytes: dict[str, Optional[bytes]] = {}
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(chunk_urls))) as pool:
        futures = {pool.submit(_download_one, url): url for url in chunk_urls}
        for future in as_completed(futures):
            url, data = future.result()
            url_to_bytes[url] = data

    # Preserve original order
    ordered_bytes = []
    failed        = []
    for url in chunk_urls:
        data = url_to_bytes.get(url)
        if data:
            ordered_bytes.append(data)
        else:
            failed.append(url)

    if failed:
        logger.warning(f"assemble_audio: {len(failed)}/{len(chunk_urls)} chunks failed")

    if not ordered_bytes:
        logger.error("assemble_audio: all chunks failed — cannot assemble")
        return None

    # Concatenate raw OGG bytes — valid for OGG container format
    combined = b"".join(ordered_bytes)

    combined_key = _make_combined_key(chunk_urls)
    url = upload_audio(combined, combined_key)

    if url:
        logger.info(
            f"assemble_audio: {len(chunk_urls)} chunks → "
            f"{len(combined):,}B → {combined_key}"
        )
    else:
        logger.error("assemble_audio: S3 upload failed")

    return url