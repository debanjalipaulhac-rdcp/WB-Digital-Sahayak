"""
src/cache/background_saver.py
Fire-and-forget async background task.
Saves newly generated audio chunk metadata to DynamoDB AFTER
the response has already been sent to the user.

NEVER blocks the main response path.
On Lambda: use threading.Thread (asyncio event loop is already busy).
"""

import logging
import threading
from typing import Optional

from src.storage.dynamo import batch_save_audio_chunks

logger = logging.getLogger(__name__)


def _save_worker(chunks_and_urls: list[dict], language_code: str) -> None:
    """
    Worker that runs in a background thread.
    Writes all new chunk URLs to DynamoDB audio_chunks table.
    Errors are logged but never raised — this is best-effort.
    """
    try:
        written = batch_save_audio_chunks(chunks_and_urls, language_code)
        logger.info(
            f"[background_saver] Saved {written}/{len(chunks_and_urls)} "
            f"chunk URLs to DynamoDB [{language_code}]"
        )
    except Exception as e:
        # Swallow — user already has their response, this is cache warming only
        logger.error(f"[background_saver] Failed to save chunks: {e}")


def save_new_chunks_async(
    chunks_and_urls: list[dict],
    language_code: str
) -> Optional[threading.Thread]:
    """
    Kick off background DynamoDB save. Returns immediately.
    
    chunks_and_urls: [{"chunk_text": "...", "audio_url": "s3://..."}]
    language_code:   "bn-IN" | "hi-IN" | "en-IN"

    Returns the Thread object (caller can .join() in tests, ignore in prod).
    Returns None if nothing to save.

    Usage in whatsapp.py:
        # After sending audio response to user:
        save_new_chunks_async(new_chunks, language_code)
        # Returns immediately — DynamoDB write happens in background
    """
    if not chunks_and_urls:
        return None

    thread = threading.Thread(
        target=_save_worker,
        args=(chunks_and_urls, language_code),
        daemon=True   # Dies with Lambda container — acceptable, S3 is already saved
    )
    thread.start()
    logger.info(
        f"[background_saver] Started background save for "
        f"{len(chunks_and_urls)} chunks [{language_code}]"
    )
    return thread