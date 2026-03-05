"""
src/voice/chunk_splitter.py
Splits response text into audio chunks for DynamoDB cache lookup.
Pure Python. Zero external calls.
"""

import re
import string


# FIX: Bengali danda ।  is not in string.punctuation (ASCII only)
# Add it explicitly so Bengali sentences are cleaned correctly
_EXTRA_PUNCTUATION = "।"
_STRIP_CHARS = string.punctuation + _EXTRA_PUNCTUATION


def split_into_chunks(text: str) -> list[str]:
    """
    Split on sentence boundaries: . ! ? \\n and Bengali danda ।
    Strip whitespace from each chunk.
    Filter chunks < 3 words (too small to cache usefully).
    Returns ordered list of clean chunk strings.

    Example:
      Input:  "আপনি যোগ্য। আধার কার্ড লাগবে। ব্যাংক পাসবুক লাগবে।"
      Output: ["আপনি যোগ্য", "আধার কার্ড লাগবে", "ব্যাংক পাসবুক লাগবে"]
    """
    if not text or not text.strip():
        return []

    # FIX: include ।  (Bengali danda) in split pattern
    chunks = re.split(r'[.!?\n।]+', text)

    result = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        if len(chunk.split()) < 3:
            continue
        result.append(chunk)

    return result


def normalize_chunk(chunk: str) -> str:
    """
    Normalizes a chunk for use as a DynamoDB cache key.
    Must be called consistently on BOTH store and lookup sides.

    Steps:
      1. Strip surrounding whitespace
      2. Strip punctuation from edges (including Bengali danda ।)
      3. Lowercase (harmless for Bengali, needed for English consistency)
      4. Collapse multiple spaces → single space
      5. Strip again

    Example: "  আধার কার্ড লাগবে।  " → "আধার কার্ড লাগবে"
    Example: "  Aadhaar Card Required.  " → "aadhaar card required"
    """
    chunk = chunk.strip()
    chunk = chunk.strip(_STRIP_CHARS)
    chunk = chunk.strip()
    chunk = chunk.lower()
    chunk = re.sub(r'\s+', ' ', chunk)
    chunk = chunk.strip()
    return chunk


def estimate_audio_duration(chunks: list[str]) -> float:
    """
    Rough estimate of total audio duration for a list of chunks.
    Bengali TTS: ~0.08 seconds per character (Sarvam empirical average).
    Returns total estimated seconds.
    Use to warn if response will breach the 50s delivery SLA.
    """
    total_chars = sum(len(chunk) for chunk in chunks)
    return total_chars * 0.08