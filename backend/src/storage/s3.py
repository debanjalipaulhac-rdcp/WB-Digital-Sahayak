"""
src/storage/s3.py
==================
All S3 operations for WB Digital Sahayak.

What we store in S3:
  1. schemes.json + scripts.json  → source of truth backup in cloud
  2. Pre-generated audio cache    → Bengali voice responses as .ogg files

Audio cache strategy:
  Instead of calling Sarvam TTS on every request (slow, costs money),
  we pre-generate the most common responses once and cache them in S3.

  Common cached responses:
    audio-cache/name_mismatch_bn.ogg       → "আপনার নামে গরমিল আছে"
    audio-cache/dormant_account_bn.ogg     → "আপনার account dormant"
    audio-cache/aadhaar_unlinked_bn.ogg    → "Aadhaar link করুন"
    audio-cache/score_green_bn.ogg         → "আপনি প্রস্তুত"
    audio-cache/score_red_bn.ogg           → "এখনই যাবেন না"
    audio-cache/welcome_bn.ogg             → welcome message

  Dynamic responses (score number, person's name) → live Sarvam TTS call.
  Static responses (issue explanations, scripts) → serve from S3 cache.

S3 bucket setup:
  1. AWS Console → S3 → Create bucket
  2. Name: wb-sahayak-schemes  (must be globally unique — add suffix if taken)
  3. Region: ap-south-1 (Mumbai)
  4. Block all public access: ON  (we serve via pre-signed URLs, not public)
  5. Versioning: OFF (not needed for audio cache)

Usage:
    from src.storage.s3 import get_audio_url, upload_audio, upload_json
"""

import io
import json
import logging
from typing import Optional

from botocore.exceptions import ClientError

from config.aws_clients import get_s3_client
from config.settings import settings

logger = logging.getLogger(__name__)

# ── S3 key prefixes — all paths in the bucket ─────────────────────────────────
PREFIX_AUDIO  = settings.S3_AUDIO_CACHE_PREFIX      # "audio-cache/"
PREFIX_SCHEMES = "data/"                              # "data/schemes.json"

# Pre-signed URL expiry — how long download links are valid
PRESIGNED_URL_EXPIRY_SECONDS = 300   # 5 minutes — enough for WhatsApp to fetch


# ── Helpers ───────────────────────────────────────────────────────────────────

def _s3():
    """Get S3 client."""
    return get_s3_client()


def _audio_key(filename: str) -> str:
    """
    Build the S3 key for an audio file.
    e.g. "name_mismatch_bn.ogg" → "audio-cache/name_mismatch_bn.ogg"
    """
    if not filename.startswith(PREFIX_AUDIO):
        return f"{PREFIX_AUDIO}{filename}"
    return filename


# ── Audio cache operations ────────────────────────────────────────────────────

def audio_exists(filename: str) -> bool:
    """
    Check if an audio file exists in the S3 cache.
    Uses head_object — just checks metadata, doesn't download.
    Cost: ~$0.000004 per check. Basically free.

    Args:
        filename: e.g. "name_mismatch_bn.ogg"

    Returns:
        True if file exists in cache.

    Example:
        if audio_exists("name_mismatch_bn.ogg"):
            url = get_audio_url("name_mismatch_bn.ogg")
        else:
            audio = generate_via_sarvam(text)
            upload_audio(audio, "name_mismatch_bn.ogg")
            url = get_audio_url("name_mismatch_bn.ogg")
    """
    try:
        _s3().head_object(Bucket=settings.S3_BUCKET_NAME, Key=_audio_key(filename))
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        logger.error(f"S3 head_object failed for {filename}: {e}")
        return False


def get_audio_url(filename: str) -> Optional[str]:
    """
    Generate a pre-signed URL for an audio file.

    Pre-signed URL = temporary download link that expires after 5 minutes.
    We send this URL in the WhatsApp message — Twilio fetches the audio
    from this URL and sends it as a voice note to the user.

    Why pre-signed (not public URL):
      The bucket is private. Pre-signed URLs allow temporary access
      without making the whole bucket public. More secure.

    Args:
        filename: e.g. "name_mismatch_bn.ogg"

    Returns:
        A temporary https:// URL valid for 5 minutes, or None if error.

    Example:
        url = get_audio_url("name_mismatch_bn.ogg")
        # url = "https://wb-sahayak-schemes.s3.ap-south-1.amazonaws.com/audio-cache/name_mismatch_bn.ogg?X-Amz-Signature=..."
        twilio_client.messages.create(media_url=[url], ...)
    """
    if settings.MOCK_MODE:
        logger.debug(f"MOCK_MODE — returning fake URL for {filename}")
        return f"https://mock-s3.example.com/{filename}"

    try:
        key = _audio_key(filename)
        url = _s3().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET_NAME, "Key": key},
            ExpiresIn=PRESIGNED_URL_EXPIRY_SECONDS,
        )
        logger.debug(f"Pre-signed URL generated for {filename}")
        return url

    except Exception as e:
        logger.error(f"get_audio_url failed for {filename}: {e}")
        return None


def upload_audio(audio_bytes: bytes, filename: str, content_type: str = "audio/ogg") -> bool:
    """
    Upload an audio file to the S3 cache.

    Called by the TTS pipeline after generating a new audio file via Sarvam.
    Once uploaded, future requests serve from cache instead of calling Sarvam again.

    Args:
        audio_bytes:  Raw audio bytes (ogg/mp3) returned by Sarvam TTS
        filename:     e.g. "name_mismatch_bn.ogg"
        content_type: MIME type. "audio/ogg" for voice notes.

    Returns:
        True if upload succeeded.

    Example:
        audio_bytes = sarvam_tts.generate("আপনার নামে গরমিল আছে")
        success = upload_audio(audio_bytes, "name_mismatch_bn.ogg")
    """
    try:
        key = _audio_key(filename)
        _s3().put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=key,
            Body=audio_bytes,
            ContentType=content_type,
            CacheControl="max-age=86400",   # browser/CDN can cache for 1 day
        )
        logger.info(f"Audio uploaded: s3://{settings.S3_BUCKET_NAME}/{key} ({len(audio_bytes)} bytes)")
        return True

    except Exception as e:
        logger.error(f"upload_audio failed for {filename}: {e}")
        return False


def get_or_generate_audio(
    filename: str,
    text_bn: str,
    tts_func=None
) -> Optional[str]:
    """
    Cache-first audio fetcher.
    Check S3 → if exists return URL → if not, generate via Sarvam → upload → return URL.

    This is the main function the voice pipeline calls.
    It handles the entire cache logic so sarvam_tts.py stays clean.

    Args:
        filename:  Cache key e.g. "name_mismatch_bn.ogg"
        text_bn:   Bengali text to speak if cache miss
        tts_func:  Callable that takes text and returns audio bytes.
                   Pass None to skip generation (just check cache).

    Returns:
        Pre-signed S3 URL, or None if everything fails.

    Example:
        url = get_or_generate_audio(
            filename="name_mismatch_bn.ogg",
            text_bn="আপনার Aadhaar এবং Bank-এ নামের গরমিল আছে।",
            tts_func=sarvam_tts.generate
        )
        # URL returned from cache if exists, generated if not.
    """
    # 1. Check cache first
    if audio_exists(filename):
        logger.debug(f"Cache hit: {filename}")
        return get_audio_url(filename)

    logger.info(f"Cache miss: {filename} — generating via TTS")

    # 2. Generate if tts_func provided
    if tts_func is None:
        logger.warning(f"Cache miss and no tts_func provided for {filename}")
        return None

    if settings.MOCK_MODE:
        return f"https://mock-s3.example.com/{filename}"

    try:
        audio_bytes = tts_func(text_bn)
        if not audio_bytes:
            logger.error(f"TTS returned empty bytes for {filename}")
            return None

        # 3. Upload to cache
        uploaded = upload_audio(audio_bytes, filename)
        if not uploaded:
            return None

        # 4. Return URL
        return get_audio_url(filename)

    except Exception as e:
        logger.error(f"get_or_generate_audio failed for {filename}: {e}")
        return None


# ── Scheme data operations ────────────────────────────────────────────────────

def upload_schemes_json(local_path: str = None, data: dict = None) -> bool:
    """
    Upload schemes.json to S3.
    Called during deployment or when schemes are updated.

    Why keep schemes.json in S3:
      - Lambda can read it at runtime (no need to redeploy Lambda for scheme updates)
      - Acts as backup if local file is corrupted
      - In Phase 2: admin can update schemes without touching code

    Args:
        local_path: Path to local schemes.json file.
        data:       Dict to upload directly (alternative to local_path).

    Example:
        upload_schemes_json(local_path="src/engine/schemes.json")
        # or
        upload_schemes_json(data={"schemes": [...]})
    """
    try:
        if data:
            body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        elif local_path:
            with open(local_path, "rb") as f:
                body = f.read()
        else:
            raise ValueError("Provide either local_path or data")

        _s3().put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=f"{PREFIX_SCHEMES}schemes.json",
            Body=body,
            ContentType="application/json; charset=utf-8",
        )
        logger.info("schemes.json uploaded to S3")
        return True

    except Exception as e:
        logger.error(f"upload_schemes_json failed: {e}")
        return False


# ── Pre-cache script — run this once before the demo ─────────────────────────

# Maps issue code → (Bengali text, filename)
AUDIO_CACHE_MANIFEST = {
    "NAME_MISMATCH":     ("আপনার Aadhaar এবং Bank-এ নামের গরমিল আছে। Bank-এ গিয়ে KYC update করুন।", "name_mismatch_bn.ogg"),
    "DORMANT_ACCOUNT":   ("আপনার bank account dormant হয়ে গেছে। যেকোনো transaction করে account সক্রিয় করুন।", "dormant_account_bn.ogg"),
    "AADHAAR_UNLINKED":  ("আপনার Aadhaar bank account-এর সাথে link নেই। Bank-এ গিয়ে Aadhaar seeding করুন।", "aadhaar_unlinked_bn.ogg"),
    "ADDRESS_MISMATCH":  ("আপনার Ration Card এবং Voter ID-তে ঠিকানা মিলছে না। Panchayat office-এ যান।", "address_mismatch_bn.ogg"),
    "SCORE_GREEN":       ("আপনি প্রস্তুত! আগামীকালই BDO office যেতে পারেন।", "score_green_bn.ogg"),
    "SCORE_RED":         ("এখনই অফিসে যাবেন না। আগে roadmap অনুসরণ করুন।", "score_red_bn.ogg"),
    "WELCOME":           ("স্বাগতম! আমি আপনার Digital Sahayak। আপনি কোন সরকারি scheme-এর জন্য আবেদন করতে চান?", "welcome_bn.ogg"),
}


def precache_all_audio(tts_func) -> dict:
    """
    Pre-generate and upload all static audio responses.
    Run this ONCE before the demo — not on every request.

    How to run:
        python -m scripts.precache_audio

    Args:
        tts_func: Callable(text_bn: str) → bytes

    Returns:
        Dict of results: {"NAME_MISMATCH": True, "DORMANT_ACCOUNT": False, ...}

    Example:
        from src.voice.sarvam_tts import generate_audio
        results = precache_all_audio(generate_audio)
        print(results)
    """
    results = {}
    for code, (text_bn, filename) in AUDIO_CACHE_MANIFEST.items():
        if audio_exists(filename):
            logger.info(f"Already cached: {filename}")
            results[code] = True
            continue

        url = get_or_generate_audio(filename, text_bn, tts_func)
        results[code] = url is not None
        status = "✅" if results[code] else "❌"
        logger.info(f"{status} {code} → {filename}")

    return results