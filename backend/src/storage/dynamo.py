"""
src/storage/dynamo.py
======================
All DynamoDB operations for WB Digital Sahayak.

Table Design (single-table pattern):
  Table name: wb-sahayak-users  (from settings.DYNAMODB_TABLE_NAME)

  Every item has:
    PK (partition key) = phone number  e.g. "+919876543210"
    SK (sort key)      = record type   e.g. "PROFILE", "SESSION", "RESULT#<timestamp>"

  This means one table handles everything:
    Phone "+91..."  + "PROFILE"             → user profile
    Phone "+91..."  + "SESSION"             → current WhatsApp conversation state
    Phone "+91..."  + "RESULT#1710000000"   → past eligibility check result

Why single-table:
  - One table to manage, one set of permissions
  - All user data together = cheap reads (no joins)
  - DynamoDB charges per read/write, not per table

Create the table in AWS console:
  Table name:     wb-sahayak-users
  Partition key:  phone (String)
  Sort key:       sk    (String)
  Billing mode:   On-demand (pay per request — cheapest for hackathon)

Usage:
    from src.storage.dynamo import save_profile, get_profile, save_session, get_session
"""

import json
import time
import logging
from typing import Any, Dict, Optional
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

# from src.config.aws_clients import get_dynamodb_table
from ..config.aws_clients import get_dynamodb_table
from src.config.settings import settings

logger = logging.getLogger(__name__)

# ── SK (sort key) constants — never hardcode strings elsewhere ────────────────
SK_PROFILE  = "PROFILE"
SK_SESSION  = "SESSION"
SK_RESULT   = "RESULT"     # prefix — full SK is "RESULT#<unix_timestamp>"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_table():
    """Get DynamoDB table. Raises RuntimeError if unavailable."""
    try:
        return get_dynamodb_table()
    except Exception as e:
        raise RuntimeError(f"DynamoDB unavailable: {e}")


def _now() -> int:
    """Current Unix timestamp as int."""
    return int(time.time())


def _ttl_days(days: int) -> int:
    """Unix timestamp N days from now. Used for automatic item expiry."""
    return _now() + (days * 86400)


# ── Profile operations ────────────────────────────────────────────────────────

def save_profile(phone: str, profile_data: Dict[str, Any]) -> bool:
    """
    Save or update a user profile in DynamoDB.

    Args:
        phone:        User's phone number — the primary key.
                      e.g. "+919876543210"
        profile_data: Dict with name, age, gender, caste, district, etc.

    Returns:
        True if saved, False if error.

    DynamoDB item structure:
        {
          "phone": "+919876543210",   # PK
          "sk":    "PROFILE",         # SK
          "name":  "Sulata Mondal",
          "age":   38,
          "gender": "female",
          "caste":  "sc",
          "district": "Jalpaiguri",
          "is_govt_employee": False,
          "pays_income_tax": False,
          "has_daughter": True,
          "has_school_child": False,
          "created_at": 1710000000,
          "updated_at": 1710000000,
          "ttl": 1741536000           # auto-deleted after 1 year
        }

    Example:
        success = save_profile("+919876543210", {
            "name": "Sulata Mondal",
            "age": 38,
            "gender": "female",
            "caste": "sc",
            "district": "Jalpaiguri",
        })
    """
    try:
        table = _get_table()
        now   = _now()
        print(table)
        item = {
            "phone":      phone,
            "sk":         SK_PROFILE,
            "updated_at": now,
            "ttl":        _ttl_days(365),   # auto-expire after 1 year
            **profile_data,                 # spread all profile fields in
        }

        # Set created_at only if first time (don't overwrite on updates)
        item.setdefault("created_at", now)

        table.put_item(Item=item)
        logger.info(f"Profile saved: {phone}")
        return True

    except ClientError as e:
        logger.error(f"DynamoDB save_profile failed for {phone}: {e}")
        return False

    except Exception as e:
        logger.error(f"Unexpected error in save_profile: {e}")
        return False


def get_profile(phone: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a user profile by phone number.

    Args:
        phone: User's phone number e.g. "+919876543210"

    Returns:
        Profile dict if found, None if not found or error.

    Example:
        profile = get_profile("+919876543210")
        if profile:
            print(profile["name"])  # "Sulata Mondal"
        else:
            print("New user — start onboarding flow")
    """
    try:
        table    = _get_table()
        response = table.get_item(Key={"phone": phone, "sk": SK_PROFILE})
        item     = response.get("Item")

        if not item:
            logger.debug(f"No profile found for {phone}")
            return None

        # Remove DynamoDB-internal fields before returning
        item.pop("sk", None)
        item.pop("ttl", None)

        logger.debug(f"Profile fetched: {phone}")
        return item

    except ClientError as e:
        logger.error(f"DynamoDB get_profile failed for {phone}: {e}")
        return None

    except Exception as e:
        logger.error(f"Unexpected error in get_profile: {e}")
        return None


def profile_exists(phone: str) -> bool:
    """
    Quick check — does this user have a profile?
    Cheaper than get_profile (projects only 1 attribute).

    Example:
        if not profile_exists("+919876543210"):
            send_onboarding_message(phone)
    """
    try:
        table    = _get_table()
        response = table.get_item(
            Key={"phone": phone, "sk": SK_PROFILE},
            ProjectionExpression="phone"   # only fetch PK — minimal read cost
        )
        return "Item" in response

    except Exception as e:
        logger.error(f"profile_exists check failed: {e}")
        return False


# ── Session operations (WhatsApp conversation state) ─────────────────────────

def save_session(phone: str, session_data: Dict[str, Any]) -> bool:
    """
    Save WhatsApp conversation state for a user.

    Called after every WhatsApp message exchange to track
    where the user is in the multi-step conversation flow.

    Session states (conversation_step values):
        "START"              → new conversation
        "AWAITING_SCHEME"    → asked which scheme, waiting for reply
        "AWAITING_AGE"       → collecting profile: asked age
        "AWAITING_GENDER"    → collecting profile: asked gender
        "AWAITING_DOCS"      → asking which docs they have
        "AWAITING_NAMES"     → asking for names on each doc
        "RESULT_SHOWN"       → sent the result, waiting for follow-up
        "AWAITING_SCRIPT"    → user asked for office script

    Args:
        phone:        User's phone number
        session_data: Dict with conversation state

    DynamoDB item structure:
        {
          "phone":             "+919876543210",
          "sk":                "SESSION",
          "conversation_step": "AWAITING_DOCS",
          "scheme_id":         "lakshmir_bhandar",
          "partial_profile":   {"name": "Sulata", "age": 38},
          "partial_checks":    {"aadhaar_name": "Sulata Mondal"},
          "last_message":      "আপনার কাছে কোন কোন document আছে?",
          "updated_at":        1710000000,
          "ttl":               1710086400   # expires in 24 hours
        }

    Example:
        save_session("+919876543210", {
            "conversation_step": "AWAITING_DOCS",
            "scheme_id": "lakshmir_bhandar",
            "partial_profile": {"name": "Sulata", "age": 38},
        })
    """
    try:
        table = _get_table()
        item  = {
            "phone":      phone,
            "sk":         SK_SESSION,
            "updated_at": _now(),
            "ttl":        _ttl_days(1),   # sessions expire after 24 hours
            **session_data,
        }
        table.put_item(Item=item)
        logger.debug(f"Session saved: {phone} → step={session_data.get('conversation_step')}")
        return True

    except Exception as e:
        logger.error(f"save_session failed for {phone}: {e}")
        return False


def get_session(phone: str) -> Optional[Dict[str, Any]]:
    """
    Fetch current conversation session for a user.

    Called at the start of every WhatsApp webhook to restore
    conversation context before processing the new message.

    Returns:
        Session dict if active, None if expired or not found.
        None = treat as new conversation, start from "START".

    Example:
        session = get_session("+919876543210")
        step = session.get("conversation_step", "START") if session else "START"
    """
    try:
        table    = _get_table()
        response = table.get_item(Key={"phone": phone, "sk": SK_SESSION})
        item     = response.get("Item")

        if not item:
            return None

        item.pop("sk", None)
        item.pop("ttl", None)
        return item

    except Exception as e:
        logger.error(f"get_session failed for {phone}: {e}")
        return None


def clear_session(phone: str) -> bool:
    """
    Delete a user's session — resets conversation to START.
    Called when: user sends "restart", conversation completes,
    or session gets into an unrecoverable state.

    Example:
        if user_message.lower() in ("restart", "reset", "শুরু করুন"):
            clear_session(phone)
            send_welcome_message(phone)
    """
    try:
        table = _get_table()
        table.delete_item(Key={"phone": phone, "sk": SK_SESSION})
        logger.info(f"Session cleared: {phone}")
        return True
    except Exception as e:
        logger.error(f"clear_session failed for {phone}: {e}")
        return False


# ── Eligibility result operations ─────────────────────────────────────────────

def save_result(phone: str, scheme_id: str, result: Dict[str, Any]) -> str:
    """
    Save an eligibility check result to DynamoDB.
    Each result gets a unique SK: "RESULT#<timestamp>"

    Why save results:
      - User can ask "what was my score?" anytime
      - Track improvement over time (score went from 42 → 95)
      - Analytics: which schemes are most checked, avg scores, etc.

    Args:
        phone:     User's phone number
        scheme_id: e.g. "lakshmir_bhandar"
        result:    Full result dict from run_eligibility_check()

    Returns:
        The SK of the saved result (for reference).

    Example:
        result_sk = save_result("+919876543210", "lakshmir_bhandar", eligibility_result)
        print(result_sk)  # "RESULT#1710000000"
    """
    try:
        table     = _get_table()
        timestamp = _now()
        sk        = f"{SK_RESULT}#{timestamp}"

        item = {
            "phone":     phone,
            "sk":        sk,
            "scheme_id": scheme_id,
            "score":     result.get("score"),
            "band":      result.get("band"),
            "issues":    json.dumps(result.get("issues", [])),       # DynamoDB can't store complex nested lists directly
            "roadmap":   json.dumps(result.get("roadmap", [])),
            "checked_at": timestamp,
            "ttl":       _ttl_days(90),   # keep results for 90 days
        }

        table.put_item(Item=item)
        logger.info(f"Result saved: {phone} | scheme={scheme_id} | score={result.get('score')} | sk={sk}")
        return sk

    except Exception as e:
        logger.error(f"save_result failed for {phone}: {e}")
        return ""


def get_latest_result(phone: str, scheme_id: str = None) -> Optional[Dict[str, Any]]:
    """
    Get the most recent eligibility result for a user.

    Args:
        phone:     User's phone number
        scheme_id: Optional filter by scheme. If None, returns latest overall.

    Returns:
        Result dict with issues and roadmap deserialized, or None.

    Example:
        result = get_latest_result("+919876543210", "lakshmir_bhandar")
        if result:
            print(f"Last score: {result['score']}/100")
    """
    try:
        table = _get_table()

        # Query all RESULT# items for this phone, sorted by SK (which includes timestamp)
        response = table.query(
            KeyConditionExpression=Key("phone").eq(phone) & Key("sk").begins_with(SK_RESULT),
            ScanIndexForward=False,   # newest first
            Limit=10
        )

        items = response.get("Items", [])

        if scheme_id:
            items = [i for i in items if i.get("scheme_id") == scheme_id]

        if not items:
            return None

        item = items[0]   # most recent

        # Deserialize JSON strings back to Python objects
        if isinstance(item.get("issues"), str):
            item["issues"] = json.loads(item["issues"])
        if isinstance(item.get("roadmap"), str):
            item["roadmap"] = json.loads(item["roadmap"])

        item.pop("sk", None)
        item.pop("ttl", None)
        return item

    except Exception as e:
        logger.error(f"get_latest_result failed for {phone}: {e}")
        return None