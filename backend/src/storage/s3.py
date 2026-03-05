"""
storage/s3.py
S3 operations for audio chunk storage and retrieval.
All audio files are stored as .opus (Sarvam TTS output format).
"""

import os
import logging
from typing import Optional

from src.config.aws_clients import get_s3_client
from src.config.settings import settings

from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# S3_BUCKET      = os.getenv("S3_BUCKET_NAME", "wb-sahayak-audio")
# AWS_REGION     = os.getenv("AWS_REGION", "ap-south-1")
AUDIO_BASE_URL = os.getenv("S3_AUDIO_BASE_URL", f"https://{settings.S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com")


# def _get_client():
#     return boto3.client("s3", region_name=AWS_REGION)


def upload_audio(audio_bytes: bytes, s3_key: str, content_type: str = "audio/ogg") -> Optional[str]:
    """
    Upload raw audio bytes to S3.
    s3_key: e.g. "chunks/bn/aadhaar_card.opus" or "qa/lakshmir_bhandar/lb_docs_bn.opus"
    Returns full S3 URL on success, None on failure.

    Called by:
    - seed/precache_audio.py  (bulk pre-seeding)
    - cache/background_saver.py  (runtime cache misses — fire & forget)
    """
    try:
        client = get_s3_client()
        client.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=s3_key,
            Body=audio_bytes,
            # ContentType=content_type,
            ContentType='audio/ogg',    
        )
        url = f"{AUDIO_BASE_URL}/{s3_key}"
        logger.info(f"Uploaded audio to S3: {url}")
        return url
    except ClientError as e:
        logger.error(f"upload_audio failed for key '{s3_key}': {e}")
        return None


def get_audio_url(s3_key: str) -> str:
    """
    Build the public URL for a given S3 key.
    Does NOT check if the object exists — use check_audio_exists() for that.
    Fast: pure string construction, no API call.
    """
    return f"{AUDIO_BASE_URL}/{s3_key}"


def check_audio_exists(s3_key: str) -> bool:
    """
    Check if an audio file exists in S3 (head_object call).
    Use sparingly — DynamoDB cache should be checked first.
    This is a fallback for when DynamoDB is out of sync.
    """
    try:
        client =get_s3_client()
        client.head_object(Bucket=settings.S3_BUCKET_NAME, Key=s3_key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        logger.error(f"check_audio_exists failed for '{s3_key}': {e}")
        return False


def download_audio(s3_key: str) -> Optional[bytes]:
    """
    Download audio bytes from S3.
    Used when audio needs to be re-processed or combined.
    Returns bytes or None on failure.
    """
    try:
        client = _get_client()
        resp = client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        return resp["Body"].read()
    except ClientError as e:
        logger.error(f"download_audio failed for '{s3_key}': {e}")
        return None


def delete_audio(s3_key: str) -> bool:
    """
    Delete an audio file from S3.
    Used when regenerating with a better voice or fixing a TTS error.
    """
    try:
        client = _get_client()
        client.delete_object(Bucket=S3_BUCKET, Key=s3_key)
        logger.info(f"Deleted S3 object: {s3_key}")
        return True
    except ClientError as e:
        logger.error(f"delete_audio failed for '{s3_key}': {e}")
        return False


def list_audio_keys(prefix: str) -> list[str]:
    """
    List all S3 keys under a prefix.
    e.g. list_audio_keys("qa/lakshmir_bhandar/") → all Q&A audio for that scheme.
    Used by admin tools and precache_audio.py to check what's already seeded.
    """
    try:
        client = _get_client()
        paginator = client.get_paginator("list_objects_v2")
        keys = []
        for page in paginator.paginate(Bucket=settings.S3_BUCKET_NAME, Prefix=prefix):
            for obj in page.get("Contents", []):
                keys.append(obj["Key"])
        return keys
    except ClientError as e:
        logger.error(f"list_audio_keys failed for prefix '{prefix}': {e}")
        return []


def create_bucket_if_not_exists() -> bool:
    """
    Create the S3 bucket if it doesn't exist.
    Called once from seed/seed_dynamo.py during initial setup.
    Handles ap-south-1 region quirk (requires LocationConstraint).
    """
    try:
        client = get_s3_client()
        if settings.AWS_REGION == "us-east-1":
            client.create_bucket(Bucket=settings.S3_BUCKET_NAME)
        else:
            client.create_bucket(
                Bucket= settings.S3_BUCKET_NAME,
                CreateBucketConfiguration={"LocationConstraint": client.meta.region_name}
            )
        # Set public-read ACL for audio delivery
        client.put_bucket_acl(Bucket=settings.S3_BUCKET_NAME, ACL="public-read")
        logger.info(f"Created S3 bucket: {settings.S3_BUCKET_NAME}")
        return True
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            logger.info(f"S3 bucket already exists: {settings.S3_BUCKET_NAME}")
            return True
        logger.error(f"create_bucket_if_not_exists failed: {e}")
        return False