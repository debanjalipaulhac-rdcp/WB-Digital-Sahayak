# \src\router\guardrails.py

import re
from dataclasses import dataclass
from typing import Optional

from src.voice.language_detect import is_out_of_scope


@dataclass
class GuardrailResult:
    valid: bool
    reason: str            # "ok" | "empty" | "too_long" | "out_of_scope" | "abuse"
    response: Optional[str]   # Pre-built rejection message if not valid


def validate_input(text: str) -> GuardrailResult:
    """
    First filter every message hits. Rejects bad input BEFORE any API calls.
    Checks in order:
        1. Empty input → reject
        2. Length > 500 chars → reject
        3. Contains URLs/phone numbers → reject (abuse vector)
        4. is_out_of_scope() → reject with static message
    If valid → returns {valid: True, reason: "ok", response: None}
    """
    # 1. Empty input
    if not text or not text.strip():
        return GuardrailResult(
            valid=False,
            reason="empty",
            response="Please enter a question."
        )

    # 2. Length > 500 chars
    if len(text) > 500:
        return GuardrailResult(
            valid=False,
            reason="too_long",
            response="Please ask a shorter question."
        )

    # 3. Contains URLs or phone numbers
    url_pattern = re.compile(
        r'(https?://|www\.)\S+',
        re.IGNORECASE
    )
    phone_pattern = re.compile(
        r'\b(\+?\d[\d\s\-]{8,}\d)\b'
    )

    if url_pattern.search(text) or phone_pattern.search(text):
        return GuardrailResult(
            valid=False,
            reason="abuse",
            response="Your message contains content that cannot be processed. Please ask a question about WB government schemes."
        )

    # 4. Out of scope
    if is_out_of_scope(text):
        return GuardrailResult(
            valid=False,
            reason="out_of_scope",
            response="I only help with West Bengal government schemes. Please ask about schemes like Lakshmir Bhandar, Swasthya Sathi, Kanyashree, etc."
        )

    return GuardrailResult(
        valid=True,
        reason="ok",
        response=None
    )