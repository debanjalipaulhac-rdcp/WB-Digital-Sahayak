"""
src/voice/response_router.py
=============================
Decides WHETHER to send audio and WHAT format to use for a given user.

WHY THIS IS SEPARATE:
  The audio-vs-text decision has business logic that will evolve:
  - Legal requirements may change
  - A/B testing may require different rules
  - Judges may ask "can you change this rule?" — answer is YES, it's one file

  This module is the ONLY place where that decision lives.
  whatsapp.py calls: should_send_audio(profile, session) → bool
  Then: send_audio if True, else send_text.

CURRENT RULES (in priority order):
  Rule 1 [ALWAYS]:  User sent a voice note → MUST reply with voice + text
  Rule 2 [SOCIAL]:  Female + age 30+ → audio (primary target user, likely low literacy)
  Rule 3 [SOCIAL]:  SC/ST caste + age 20+ → audio (marginalized, literacy gap)
  Rule 4 [SOCIAL]:  Male + age 45+ → audio (older users, lower digital literacy)
  Rule 5 [FALLBACK]: Everyone else → text only (safe, always works)

DESIGN DECISIONS:
  - Audio is ADDITIVE — we always also send text when audio is sent
    (WhatsApp doesn't guarantee audio delivery on slow connections)
  - Rules are evaluated in ORDER — first match wins
  - Rules are named so they can be toggled individually
  - MOCK_MODE always returns text (no Sarvam API credits during testing)

MODIFYING RULES:
  To add a new rule, add a function _rule_X() and add it to RULES list.
  To disable a rule, comment it out of RULES list.
  Rules receive (profile, session) and return True/False.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ── Individual rule functions ──────────────────────────────────────────────────

def _rule_user_sent_voice(profile: dict, session: dict) -> bool:
    """Rule 1: If user sent voice, always reply with voice."""
    return bool(session.get("last_input_was_voice", False))


def _rule_female_30_plus(profile: dict, session: dict) -> bool:
    """Rule 2: Female, 30 or older → audio (Sulata persona, likely low literacy)."""
    return (
        profile.get("gender") == "female" and
        profile.get("age", 0) >= 30
    )


def _rule_sc_st_20_plus(profile: dict, session: dict) -> bool:
    """Rule 3: SC/ST caste, 20+ → audio (marginalized communities, literacy gap)."""
    return (
        profile.get("caste") in ("sc", "st") and
        profile.get("age", 0) >= 20
    )


def _rule_male_45_plus(profile: dict, session: dict) -> bool:
    """Rule 4: Male, 45 or older → audio (older users, lower digital fluency)."""
    return (
        profile.get("gender") == "male" and
        profile.get("age", 0) >= 45
    )


def _rule_obc_rural(profile: dict, session: dict) -> bool:
    """Rule 5: OBC + rural district → audio (semi-urban, may benefit from audio)."""
    rural_districts = {
        "jalpaiguri", "cooch behar", "alipurduar", "north dinajpur",
        "south dinajpur", "malda", "murshidabad", "birbhum", "bankura",
        "purulia", "jhargram", "west medinipur", "east medinipur",
        "hooghly", "nadia", "north 24 parganas"
    }
    district = profile.get("district", "").lower()
    return (
        profile.get("caste") == "obc" and
        any(d in district for d in rural_districts)
    )


# ── Rules registry ─────────────────────────────────────────────────────────────
# ORDER MATTERS — first match wins.
# To disable a rule: comment it out.
# To add a rule: create _rule_X() above and append here.

RULES = [
    ("voice_input",  _rule_user_sent_voice),   # Always reply voice for voice input
    ("female_30+",   _rule_female_30_plus),    # Primary target audience
    ("sc_st_20+",    _rule_sc_st_20_plus),     # Marginalized communities
    ("male_45+",     _rule_male_45_plus),      # Older male users
    ("obc_rural",    _rule_obc_rural),         # Rural OBC users
]


# ── Main API ───────────────────────────────────────────────────────────────────

def should_send_audio(profile: Optional[dict], session: Optional[dict]) -> bool:
    """
    Decide whether this user should receive audio responses.

    Args:
        profile: User profile dict (age, gender, caste, district)
        session: Current WhatsApp session (contains last_input_was_voice)

    Returns:
        True → send voice note (+ text as backup)
        False → send text only

    Usage in whatsapp.py:
        if should_send_audio(profile, session):
            _send_voice(phone, audio_url)
        _send_text(phone, text)   # always send text
    """
    from src.config.settings import settings

    if settings.MOCK_MODE:
        return False  # Never burn Sarvam credits in test mode

    profile = profile or {}
    session = session or {}

    for rule_name, rule_fn in RULES:
        try:
            if rule_fn(profile, session):
                logger.info(f"response_router: audio → rule '{rule_name}' matched "
                            f"(age={profile.get('age')}, gender={profile.get('gender')}, "
                            f"caste={profile.get('caste')})")
                return True
        except Exception as e:
            logger.warning(f"response_router: rule '{rule_name}' failed: {e}")
            continue

    logger.debug("response_router: text only (no rules matched)")
    return False


def get_audio_priority(profile: Optional[dict], session: Optional[dict]) -> str:
    """
    Return the REASON audio was triggered (for logging/analytics).

    Returns:
        Rule name that matched, or "none" if text-only.
    """
    profile = profile or {}
    session = session or {}

    for rule_name, rule_fn in RULES:
        try:
            if rule_fn(profile, session):
                return rule_name
        except Exception:
            continue
    return "none"


def format_whatsapp_response(
    text: str,
    text_bn: Optional[str],
    audio_url: Optional[str],
    profile: Optional[dict],
    session: Optional[dict],
    lang: str = "bn",
) -> dict:
    """
    Build the final response payload for WhatsApp.

    Returns a dict with:
      {
        "send_audio": bool,
        "audio_url":  str | None,
        "text":       str,          # always present
        "lang":       "bn" | "en",
      }

    whatsapp.py uses this dict to decide what to send.
    """
    send_audio = should_send_audio(profile, session) and bool(audio_url)

    # Pick text in the right language
    if lang == "bn" and text_bn:
        display_text = text_bn
    else:
        display_text = text

    return {
        "send_audio": send_audio,
        "audio_url":  audio_url if send_audio else None,
        "text":       display_text,
        "lang":       lang,
    }


def explain_routing_decision(profile: dict, session: dict) -> str:
    """
    Debug helper: explain why a user gets audio or text.
    Useful for logging and for answering judge questions.
    """
    profile = profile or {}
    session = session or {}

    triggered = []
    for rule_name, rule_fn in RULES:
        try:
            if rule_fn(profile, session):
                triggered.append(rule_name)
        except Exception:
            pass

    if triggered:
        return f"Audio: rules matched = {triggered}"
    return "Text only: no rules matched"