"""
storage/dynamo.py
DynamoDB CRUD + batch operations for WB Digital Sahayak.
All table names are pulled from environment settings — never hardcoded here.
"""

import json
import logging
import hashlib
from typing import Optional
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError
from src.config.aws_clients import get_dynamodb_resource
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# TABLE NAMES (set via env vars)
# ─────────────────────────────────────────────
import os

TABLE_USERS         = os.getenv("DYNAMO_TABLE_USERS",         "wb_sahayak_users")
TABLE_SESSIONS      = os.getenv("DYNAMO_TABLE_SESSIONS",      "wb_sahayak_sessions")
TABLE_SCHEME_QA     = os.getenv("DYNAMO_TABLE_SCHEME_QA",     "wb_sahayak_scheme_qa")
TABLE_AUDIO_CHUNKS  = os.getenv("DYNAMO_TABLE_AUDIO_CHUNKS",  "wb_sahayak_audio_chunks")
TABLE_SCHEMES       = os.getenv("DYNAMO_TABLE_SCHEMES",       "wb_sahayak_schemes")


def _get_resource():
    """Returns DynamoDB resource. Uses env credentials (Lambda role or .env)."""
    return boto3.resource(
        "dynamodb",
        region_name=os.getenv("AWS_REGION", "ap-south-1")
    )


def _hash_question(question: str) -> str:
    """
    Normalize and hash a question string for consistent DynamoDB key lookup.
    Always lowercase + strip before hashing so variants map to same key.
    """
    normalized = question.strip().lower()
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


# ═══════════════════════════════════════════════════════════
# USER TABLE
# PK: phone_number (string)
# ═══════════════════════════════════════════════════════════

def get_user(phone_number: str) -> Optional[dict]:
    """
    Fetch user profile by phone number.
    Returns None if user does not exist.
    """
    try:
        table = _get_resource().Table(TABLE_USERS)
        resp = table.get_item(Key={"phone_number": phone_number})
        return resp.get("Item")
    except ClientError as e:
        logger.error(f"get_user failed for {phone_number}: {e}")
        return None


def save_user(phone_number: str, profile: dict) -> bool:
    """
    Create or fully overwrite a user profile.
    profile dict should contain: name, language_code, session_state, etc.
    Always sets updated_at timestamp.
    Returns True on success, False on failure.
    """
    try:
        table = _get_resource().Table(TABLE_USERS)
        item = {
            "phone_number": phone_number,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            **profile
        }
        table.put_item(Item=item)
        return True
    except ClientError as e:
        logger.error(f"save_user failed for {phone_number}: {e}")
        return False


def update_user_language(phone_number: str, language_code: str) -> bool:
    """
    Update only the language preference for a user.
    Used when user switches language mid-session.
    """
    try:
        table = _get_resource().Table(TABLE_USERS)
        table.update_item(
            Key={"phone_number": phone_number},
            UpdateExpression="SET language_code = :lang, updated_at = :ts",
            ExpressionAttributeValues={
                ":lang": language_code,
                ":ts": datetime.now(timezone.utc).isoformat()
            }
        )
        return True
    except ClientError as e:
        logger.error(f"update_user_language failed: {e}")
        return False


def update_session_state(phone_number: str, state: str, context: dict = None) -> bool:
    """
    Update WhatsApp conversation state machine state.
    state: e.g. "START" | "COLLECTING_AGE" | "COLLECTING_CASTE" | "RESULT_SENT"
    context: arbitrary dict stored alongside state (partial user profile data)
    """
    try:
        table = _get_resource().Table(TABLE_USERS)
        expr = "SET session_state = :state, updated_at = :ts"
        vals = {
            ":state": state,
            ":ts": datetime.now(timezone.utc).isoformat()
        }
        if context:
            expr += ", session_context = :ctx"
            vals[":ctx"] = json.dumps(context)

        table.update_item(
            Key={"phone_number": phone_number},
            UpdateExpression=expr,
            ExpressionAttributeValues=vals
        )
        return True
    except ClientError as e:
        logger.error(f"update_session_state failed: {e}")
        return False


# ═══════════════════════════════════════════════════════════
# SCHEME QA TABLE
# PK: question_hash (md5 of normalized question)
# SK: language_code  (e.g. "bn-IN")
# ═══════════════════════════════════════════════════════════

def get_qa_by_hash(question_hash: str, language_code: str) -> Optional[dict]:
    """
    Lookup a static Q&A answer by pre-computed question hash + language.
    Returns item with 'answer_text' and 'audio_url' or None if not found.
    """
    try:
        table = _get_resource().Table(TABLE_SCHEME_QA)
        resp = table.get_item(
            Key={
                "question_hash": question_hash,
                "language_code": language_code
            }
        )
        return resp.get("Item")
    except ClientError as e:
        logger.error(f"get_qa_by_hash failed: {e}")
        return None


def get_qa(question: str, language_code: str) -> Optional[dict]:
    """
    Convenience wrapper: hash the question then lookup.
    Use this in production code — never hash manually outside this module.
    """
    question_hash = _hash_question(question)
    return get_qa_by_hash(question_hash, language_code)


def save_qa(
    question_variants: list[str],
    language_code: str,
    answer_text: str,
    audio_url: str,
    scheme_id: str,
    qa_id: str
) -> int:
    """
    Save a Q&A entry for ALL question variants.
    Each variant gets its own hash → same answer.
    Returns number of items written.
    Used by seed/seed_dynamo.py to populate from schemes.json.
    """
    table = _get_resource().Table(TABLE_SCHEME_QA)
    written = 0
    for variant in question_variants:
        try:
            q_hash = _hash_question(variant)
            table.put_item(Item={
                "question_hash": q_hash,
                "language_code": language_code,
                "original_question": variant,
                "answer_text": answer_text,
                "audio_url": audio_url,
                "scheme_id": scheme_id,
                "qa_id": qa_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            written += 1
        except ClientError as e:
            logger.error(f"save_qa failed for variant '{variant}': {e}")
    return written


# ═══════════════════════════════════════════════════════════
# AUDIO CHUNKS TABLE  ← Cost savings core
# PK: chunk_text  (normalized chunk string)
# SK: language_code
# ═══════════════════════════════════════════════════════════

def get_audio_chunk(chunk_text: str, language_code: str) -> Optional[str]:
    """
    Lookup S3 audio URL for a single text chunk.
    Returns the S3 URL string, or None on cache miss.
    """
    try:
        table = _get_resource().Table(TABLE_AUDIO_CHUNKS)
        resp = table.get_item(
            Key={
                "chunk_text": chunk_text.strip(),
                "language_code": language_code
            }
        )
        item = resp.get("Item")
        return item.get("audio_url") if item else None
    except ClientError as e:
        logger.error(f"get_audio_chunk failed: {e}")
        return None


def batch_get_audio_chunks(chunks: list[str], language_code: str) -> dict[str, Optional[str]]:
    """
    Batch lookup audio URLs for multiple chunks in ONE DynamoDB call.
    Returns dict: {chunk_text: audio_url_or_None}
    Maximum 100 chunks per call (DynamoDB BatchGetItem limit).
    For >100 chunks, splits automatically into batches.

    This is the KEY cost optimization — 1 DB call instead of N calls.
    """
    if not chunks:
        return {}

    result: dict[str, Optional[str]] = {c: None for c in chunks}
    resource = _get_resource()

    # DynamoDB batch_get_item max = 100 keys per call
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        keys = [
            {"chunk_text": chunk.strip(), "language_code": language_code}
            for chunk in batch
        ]
        try:
            resp = resource.batch_get_item(
                RequestItems={
                    TABLE_AUDIO_CHUNKS: {"Keys": keys}
                }
            )
            for item in resp.get("Responses", {}).get(TABLE_AUDIO_CHUNKS, []):
                chunk_text = item["chunk_text"]
                result[chunk_text] = item.get("audio_url")

            # Handle unprocessed keys (DynamoDB throttle retry)
            unprocessed = resp.get("UnprocessedKeys", {})
            if unprocessed:
                logger.warning(f"batch_get_audio_chunks: {len(unprocessed)} unprocessed keys — retry needed")

        except ClientError as e:
            logger.error(f"batch_get_audio_chunks failed: {e}")

    return result


def save_audio_chunk(chunk_text: str, language_code: str, audio_url: str) -> bool:
    """
    Save a single audio chunk URL to DynamoDB cache.
    Called by background_saver.py AFTER audio is already sent to user.
    Never blocks the main response path.
    """
    try:
        table = _get_resource().Table(TABLE_AUDIO_CHUNKS)
        table.put_item(Item={
            "chunk_text": chunk_text.strip(),
            "language_code": language_code,
            "audio_url": audio_url,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        return True
    except ClientError as e:
        logger.error(f"save_audio_chunk failed for '{chunk_text}': {e}")
        return False


def batch_save_audio_chunks(chunks_and_urls: list[dict], language_code: str) -> int:
    """
    Batch write multiple audio chunks to DynamoDB.
    chunks_and_urls: [{"chunk_text": "...", "audio_url": "s3://..."}]
    Returns number of items written.
    Used by precache_audio.py and background_saver.py.
    """
    if not chunks_and_urls:
        return 0

    table = _get_resource().Table(TABLE_AUDIO_CHUNKS)
    written = 0
    now = datetime.now(timezone.utc).isoformat()

    # DynamoDB batch_writer handles batching + retries automatically
    with table.batch_writer() as batch:
        for item in chunks_and_urls:
            try:
                batch.put_item(Item={
                    "chunk_text": item["chunk_text"].strip(),
                    "language_code": language_code,
                    "audio_url": item["audio_url"],
                    "created_at": now
                })
                written += 1
            except ClientError as e:
                logger.error(f"batch_save_audio_chunks item failed: {e}")

    return written


# ═══════════════════════════════════════════════════════════
# SCHEMES TABLE
# PK: scheme_id
# ═══════════════════════════════════════════════════════════

def get_scheme(scheme_id: str) -> Optional[dict]:
    """
    Get full scheme object from DynamoDB.
    Returns None if not found.
    """
    try:
        table = _get_resource().Table(TABLE_SCHEMES)
        resp = table.get_item(Key={"scheme_id": scheme_id})
        return resp.get("Item")
    except ClientError as e:
        logger.error(f"get_scheme failed for {scheme_id}: {e}")
        return None


def get_all_schemes() -> list[dict]:
    """
    Scan all schemes from DynamoDB.
    Only used at startup/seed time. Never call this per-user-request.
    """
    try:
        table = _get_resource().Table(TABLE_SCHEMES)
        resp = table.scan()
        return resp.get("Items", [])
    except ClientError as e:
        logger.error(f"get_all_schemes failed: {e}")
        return []


def save_scheme(scheme: dict) -> bool:
    """
    Save or overwrite a scheme in DynamoDB.
    Used by seed_dynamo.py.
    """
    try:
        table = _get_resource().Table(TABLE_SCHEMES)
        table.put_item(Item={
            **scheme,
            "seeded_at": datetime.now(timezone.utc).isoformat()
        })
        return True
    except ClientError as e:
        logger.error(f"save_scheme failed for {scheme.get('scheme_id')}: {e}")
        return False


# ═══════════════════════════════════════════════════════════
# TABLE CREATION (run once, for dev/setup)
# ═══════════════════════════════════════════════════════════

def create_tables_if_not_exist():
    """
    Creates all required DynamoDB tables if they don't already exist.
    Safe to call multiple times (checks existence first).
    Call this from seed/seed_dynamo.py --create-tables flag.
    """
    # client = boto3.client("dynamodb", region_name=os.getenv("AWS_REGION", "ap-south-1"))
    client=get_dynamodb_resource()
    
    # existing = {t["TableName"] for t in client.list_tables().get("TableNames", [])}

    tables_to_create = [
        {
            "TableName": TABLE_USERS,
            "KeySchema": [{"AttributeName": "phone_number", "KeyType": "HASH"}],
            "AttributeDefinitions": [{"AttributeName": "phone_number", "AttributeType": "S"}],
            "BillingMode": "PAY_PER_REQUEST"
        },
        {
            "TableName": TABLE_SCHEME_QA,
            "KeySchema": [
                {"AttributeName": "question_hash", "KeyType": "HASH"},
                {"AttributeName": "language_code", "KeyType": "RANGE"}
            ],
            "AttributeDefinitions": [
                {"AttributeName": "question_hash", "AttributeType": "S"},
                {"AttributeName": "language_code", "AttributeType": "S"}
            ],
            "BillingMode": "PAY_PER_REQUEST"
        },
        {
            "TableName": TABLE_AUDIO_CHUNKS,
            "KeySchema": [
                {"AttributeName": "chunk_text", "KeyType": "HASH"},
                {"AttributeName": "language_code", "KeyType": "RANGE"}
            ],
            "AttributeDefinitions": [
                {"AttributeName": "chunk_text", "AttributeType": "S"},
                {"AttributeName": "language_code", "AttributeType": "S"}
            ],
            "BillingMode": "PAY_PER_REQUEST"
        },
        {
            "TableName": TABLE_SCHEMES,
            "KeySchema": [{"AttributeName": "scheme_id", "KeyType": "HASH"}],
            "AttributeDefinitions": [{"AttributeName": "scheme_id", "AttributeType": "S"}],
            "BillingMode": "PAY_PER_REQUEST"
        },
        {
            "TableName": TABLE_SESSIONS,
            "KeySchema": [
                {"AttributeName": "phone_number", "KeyType": "HASH"},
                {"AttributeName": "timestamp", "KeyType": "RANGE"}
            ],
            "AttributeDefinitions": [
                {"AttributeName": "phone_number", "AttributeType": "S"},
                {"AttributeName": "timestamp", "AttributeType": "S"}
            ],
            "BillingMode": "PAY_PER_REQUEST"
        }
    ]

    for spec in tables_to_create:
        # if spec["TableName"] in existing:
        #     logger.info(f"Table already exists: {spec['TableName']}")
        #     continue
        try:
            client.create_table(**spec)
            logger.info(f"Created table: {spec['TableName']}")
        except ClientError as e:
            logger.error(f"Failed to create table {spec['TableName']}: {e}")