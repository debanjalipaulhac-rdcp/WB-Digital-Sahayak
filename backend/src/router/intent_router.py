"""
src/router/intent_router.py
Main routing brain. Takes a processed user message and routes it to
the correct handler: GREETING / STATIC / ELIGIBILITY / DYNAMIC.

Called AFTER:
  - guardrails.validate_input (input is already validated)
  - STT (if audio, transcript is already extracted)
  - language detection (language_code is known)

Returns a RouteDecision telling the caller exactly what to do next.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.voice.language_detect import is_greeting, is_out_of_scope

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Scheme name variants for keyword matching
# Covers Bengalish/Hinglish common spellings
# ─────────────────────────────────────────────
SCHEME_NAME_KEYWORDS = {
    "lakshmir_bhandar":  [
        "lakshmir bhandar", "lakshmibhandar", "লক্ষ্মীর ভাণ্ডার",
        "lakshmir", "লক্ষ্মী", "laxmi bhandar"
    ],
    "swasthya_sathi":    [
        "swasthya sathi", "স্বাস্থ্যসাথী", "swasthyasathi",
        "swasthya", "স্বাস্থ্য সাথী", "health scheme"
    ],
    "kanyashree":        [
        "kanyashree", "কন্যাশ্রী", "kanya shree", "kanyasri"
    ],
    "rupashree":         [
        "rupashree", "রূপশ্রী", "rupa shree", "rupasri", "marriage scheme"
    ],
    "yuva_sathi":        [
        "yuva sathi", "যুবসাথী", "yuvasathi", "youth scheme", "unemployment"
    ],
    "samajik_suraksha":  [
        "samajik suraksha", "সামাজিক সুরক্ষা", "pension", "পেনশন",
        "old age", "বৃদ্ধ", "widow", "বিধবা"
    ]
}

# Q&A type keywords
QA_TYPE_KEYWORDS = {
    "documents": [
        "document", "কাগজ", "documents needed", "what do i need",
        "কী কী লাগে", "কী লাগবে", "required papers", "kagoj"
    ],
    "eligibility": [
        "eligible", "যোগ্য", "who can apply", "কারা পাবে",
        "qualification", "criteria", "যোগ্যতা", "ami ki pabo"
    ],
    "benefit": [
        "benefit", "সুবিধা", "how much", "কত টাকা", "money",
        "amount", "পরিমাণ", "koto taka"
    ],
    "apply_where": [
        "where to apply", "কোথায় আবেদন", "how to apply",
        "application", "আবেদন কীভাবে", "apply"
    ]
}

# Eligibility check trigger keywords
ELIGIBILITY_CHECK_KEYWORDS = [
    "am i eligible", "আমি কি যোগ্য", "check eligibility",
    "can i apply", "আমি কি পাব", "my age is", "আমার বয়স",
    "ami eligible", "ami ki pabo", "আমার জন্য কোন প্রকল্প",
    "what scheme for me", "schemes for me", "আমার জন্য"
]


class IntentType(str, Enum):
    GREETING    = "greeting"
    STATIC_QA   = "static_qa"        # Known scheme Q&A → DynamoDB direct
    ELIGIBILITY = "eligibility"      # User wants to check if they qualify
    DYNAMIC     = "dynamic"          # Unknown → vector search + Nova Lite
    OUT_OF_SCOPE = "out_of_scope"    # Shouldn't reach here (filtered by guardrails)


@dataclass
class RouteDecision:
    intent:     IntentType
    scheme_id:  Optional[str]   # Set for STATIC_QA and ELIGIBILITY
    qa_type:    Optional[str]   # Set for STATIC_QA: "documents"|"eligibility"|"benefit"|"apply_where"
    confidence: float           # 0.0–1.0, how confident the routing is
    reason:     str             # Debug string


def _detect_scheme(text: str) -> Optional[str]:
    """Return scheme_id if any scheme name found in text, else None."""
    lower = text.lower()
    for scheme_id, keywords in SCHEME_NAME_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return scheme_id
    return None


def _detect_qa_type(text: str) -> Optional[str]:
    """Return Q&A type if detected in text, else None."""
    lower = text.lower()
    for qa_type, keywords in QA_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return qa_type
    return None


def _is_eligibility_check(text: str) -> bool:
    """Returns True if user is asking to check their own eligibility."""
    lower = text.lower()
    for kw in ELIGIBILITY_CHECK_KEYWORDS:
        if kw in lower:
            return True
    return False


def route(text: str, language_code: str) -> RouteDecision:
    """
    Main routing function. Routes to exactly one intent.

    Priority order (first match wins):
      1. Greeting          → GREETING
      2. Eligibility check → ELIGIBILITY
      3. Scheme + Q&A type → STATIC_QA (DynamoDB direct)
      4. Scheme only       → DYNAMIC (need vector search for context)
      5. Default           → DYNAMIC

    Args:
        text:          User message text (may be any language)
        language_code: Detected language code
    """
    # 1. Greeting
    if is_greeting(text):
        return RouteDecision(
            intent=IntentType.GREETING,
            scheme_id=None, qa_type=None,
            confidence=1.0, reason="is_greeting=True"
        )

    # 2. Eligibility check — user asking about their own profile
    if _is_eligibility_check(text):
        scheme_id = _detect_scheme(text)  # May be None — engine checks all
        return RouteDecision(
            intent=IntentType.ELIGIBILITY,
            scheme_id=scheme_id, qa_type=None,
            confidence=0.9,
            reason=f"eligibility_check keyword matched, scheme={scheme_id}"
        )

    # 3. Scheme + Q&A type → STATIC_QA
    scheme_id = _detect_scheme(text)
    qa_type   = _detect_qa_type(text)

    if scheme_id and qa_type:
        return RouteDecision(
            intent=IntentType.STATIC_QA,
            scheme_id=scheme_id, qa_type=qa_type,
            confidence=0.95,
            reason=f"scheme={scheme_id} qa_type={qa_type} — static lookup"
        )

    # 4. Scheme detected but Q&A type unclear → dynamic can refine
    if scheme_id:
        return RouteDecision(
            intent=IntentType.DYNAMIC,
            scheme_id=scheme_id, qa_type=None,
            confidence=0.7,
            reason=f"scheme={scheme_id} but qa_type unclear — routing to dynamic"
        )

    # 5. Default → dynamic path
    return RouteDecision(
        intent=IntentType.DYNAMIC,
        scheme_id=None, qa_type=None,
        confidence=0.5,
        reason="no scheme or qa_type detected — dynamic path"
    )