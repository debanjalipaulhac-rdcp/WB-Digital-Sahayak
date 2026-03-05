"""
src/cache/audio_cache.py
Audio chunk cache lookup — the cost savings core.
ONE DynamoDB BatchGetItem call for all chunks in a response.
Returns hits (URL ready) and misses (need TTS generation).
"""

import logging
from dataclasses import dataclass

from src.storage.dynamo import batch_get_audio_chunks
from src.voice.chunk_splitter import normalize_chunk

logger = logging.getLogger(__name__)


@dataclass
class CacheResolution:
    """
    Result of resolving a list of text chunks against the audio cache.

    chunk_urls:  ordered list — each element is EITHER a cached S3 URL
                 OR None (cache miss, needs TTS generation)
    hits:        {chunk_text: s3_url}  — chunks found in cache
    misses:      [chunk_text]          — chunks NOT in cache, need TTS
    hit_rate:    float 0.0–1.0
    """
    chunk_urls:  list               # len == len(input chunks), preserves order
    hits:        dict[str, str]     # chunk_text → s3_url
    misses:      list[str]          # chunk_text list
    hit_rate:    float


def resolve_chunks(chunks: list[str], language_code: str) -> CacheResolution:
    """
    Given ordered list of text chunks and language, check DynamoDB cache.

    Steps:
      1. Normalize all chunks (same normalization used at save time)
      2. Batch GET from DynamoDB — 1 API call regardless of chunk count
      3. Build ordered chunk_urls preserving original order
      4. Separate hits from misses

    Args:
        chunks:        Raw text chunks from chunk_splitter.split_into_chunks()
        language_code: "bn-IN" | "hi-IN" | "en-IN"

    Returns CacheResolution with hits, misses, and ordered URL list.
    """
    if not chunks:
        return CacheResolution(chunk_urls=[], hits={}, misses=[], hit_rate=0.0)

    # Normalize — MUST use same normalization as save path
    normalized_chunks = [normalize_chunk(c) for c in chunks]

    # Single DynamoDB batch call
    cache_result = batch_get_audio_chunks(normalized_chunks, language_code)

    # Build output preserving original chunk order
    hits   = {}
    misses = []
    chunk_urls = []

    for norm_chunk in normalized_chunks:
        url = cache_result.get(norm_chunk)
        if url:
            hits[norm_chunk] = url
            chunk_urls.append(url)
        else:
            misses.append(norm_chunk)
            chunk_urls.append(None)   # placeholder — filled by tts_generator

    total     = len(normalized_chunks)
    hit_count = len(hits)
    hit_rate  = hit_count / total if total > 0 else 0.0

    logger.info(
        f"Cache resolution [{language_code}]: "
        f"{hit_count}/{total} hits ({hit_rate:.0%}) — "
        f"{len(misses)} need TTS"
    )

    return CacheResolution(
        chunk_urls=chunk_urls,
        hits=hits,
        misses=misses,
        hit_rate=hit_rate
    )


def fill_misses(resolution: CacheResolution, generated: dict[str, str]) -> list[str]:
    """
    After tts_generator generates audio for all misses,
    fill the None placeholders in chunk_urls with real URLs.

    generated: {normalized_chunk_text: s3_url}
    Returns complete ordered URL list with no None values.

    Any chunk that still has no URL (TTS also failed) is skipped —
    we deliver partial audio rather than failing completely.
    """
    filled = []
    for url in resolution.chunk_urls:
        if url is not None:
            filled.append(url)
        # url is None → this was a miss, find it in generated
        # We iterate generated in miss order to match positions
    
    # Rebuild properly using miss order
    filled_urls = list(resolution.chunk_urls)  # copy
    miss_index  = 0

    for i, url in enumerate(filled_urls):
        if url is None:
            if miss_index < len(resolution.misses):
                miss_chunk = resolution.misses[miss_index]
                generated_url = generated.get(miss_chunk)
                if generated_url:
                    filled_urls[i] = generated_url
                miss_index += 1

    # Filter out any remaining None (TTS failures) — partial audio better than none
    result = [u for u in filled_urls if u is not None]

    if len(result) < len(filled_urls):
        dropped = len(filled_urls) - len(result)
        logger.warning(f"fill_misses: dropped {dropped} chunks due to TTS failure")

    return result