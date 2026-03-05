"""
src/voice/audio_assembler.py
Combines ordered list of S3 audio chunk URLs into a single audio file.

Downloads via boto3 (not public HTTP) — avoids S3 403 ACL issues entirely.
Parallelism via ThreadPoolExecutor (consistent with tts_generator.py).
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
MAX_WORKERS = 5


def _s3_key_from_url(url: str) -> str:
    """
    Extract S3 key from a full S3 URL.
    "https://bucket.s3.region.amazonaws.com/chunks/en_IN/abc123.ogg"
    → "chunks/en_IN/abc123.ogg"
    """
    parsed = urlparse(url)
    # path starts with "/" — strip it
    return parsed.path.lstrip("/")


def _download_one(url: str) -> tuple[str, Optional[bytes]]:
    """
    Download a single S3 object via boto3 (authenticated).
    Returns (url, bytes) or (url, None) on failure.
    Uses IAM credentials — no public access needed.
    """
    try:
        key    = _s3_key_from_url(url)
        client = get_s3_client()
        resp   = client.get_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
        data   = resp["Body"].read()
        logger.debug(f"Downloaded {len(data)} bytes: {key}")
        return url, data
    except Exception as e:
        logger.error(f"Failed to download chunk '{url}': {e}")
        return url, None


def _make_combined_key(chunk_urls: list[str]) -> str:
    """Deterministic S3 key — same chunks in same order → same key."""
    combined = "|".join(chunk_urls)
    hash_val = hashlib.md5(combined.encode()).hexdigest()[:16]
    return f"{COMBINED_AUDIO_PREFIX}{hash_val}.ogg"


def assemble_audio(chunk_urls: list[str]) -> Optional[str]:
    """
    Download all chunks (in parallel via ThreadPoolExecutor),
    concatenate bytes, upload combined file to S3.
    Returns single public S3 URL or None on failure.
    """
    if not chunk_urls:
        logger.error("assemble_audio called with empty chunk_urls list")
        return None

    # Single chunk — return directly
    if len(chunk_urls) == 1:
        return chunk_urls[0]

    combined_key = _make_combined_key(chunk_urls)

    # Download all in parallel
    url_to_bytes: dict[str, Optional[bytes]] = {}
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(chunk_urls))) as pool:
        futures = {pool.submit(_download_one, url): url for url in chunk_urls}
        for future in as_completed(futures):
            url, data = future.result()
            url_to_bytes[url] = data

    # Preserve original order when assembling
    ordered_bytes = []
    failed = []
    for url in chunk_urls:
        data = url_to_bytes.get(url)
        if data:
            ordered_bytes.append(data)
        else:
            failed.append(url)

    if failed:
        logger.warning(
            f"assemble_audio: {len(failed)}/{len(chunk_urls)} chunks failed — "
            f"assembling partial audio"
        )

    if not ordered_bytes:
        logger.error("All chunks failed to download — cannot assemble audio")
        return None

    combined_bytes = b"".join(ordered_bytes)
    url = upload_audio(combined_bytes, combined_key, content_type="audio/opus")

    if url:
        logger.info(
            f"Combined audio assembled: {len(chunk_urls)} chunks "
            f"({len(combined_bytes)} bytes) → {combined_key}"
        )
    else:
        logger.error("Failed to upload combined audio to S3")

    return url