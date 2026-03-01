"""
src/engine/mismatch.py
======================
Name and field mismatch detector using rapidfuzz fuzzy matching.

Why rapidfuzz and not exact string match:
  "Sulata Mondal" vs "Sulata"          → exact match fails, fuzzy catches it
  "Souvik Karmakar" vs "Soubhik Karmakar" → single letter typo, fuzzy catches it
  "SULATA MONDAL" vs "Sulata Mondal"   → case difference, normalise first

Threshold: ratio < 90 → flag as MISMATCH
  90–100 = close enough (minor spacing/case differences)
  < 90   = real mismatch, flag it

Usage:
    from src.engine.mismatch import check_name_match, check_address_match
"""

import logging
import re

logger = logging.getLogger(__name__)

# ── Try importing rapidfuzz, fallback to basic if not installed ───────────────
try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    logger.warning("rapidfuzz not installed — using basic string comparison. Run: pip install rapidfuzz")

# ── Threshold ─────────────────────────────────────────────────────────────────
MATCH_THRESHOLD = 90   # score below this = mismatch


# ── Normalisation ─────────────────────────────────────────────────────────────
def _normalise(text: str) -> str:
    """
    Normalise a name/address string for comparison.
    - Lowercase
    - Strip leading/trailing whitespace
    - Collapse multiple spaces
    - Remove common punctuation
    """
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r"[.\-,']", " ", text)   # replace punctuation with space
    text = re.sub(r"\s+", " ", text)        # collapse multiple spaces
    return text


def _similarity_score(a: str, b: str) -> float:
    """
    Returns similarity score 0–100 between two strings.
    Uses rapidfuzz token_sort_ratio (handles word-order differences).
    Falls back to basic containment check if rapidfuzz not available.
    """
    a_norm = _normalise(a)
    b_norm = _normalise(b)

    if not a_norm or not b_norm:
        return 0.0

    if RAPIDFUZZ_AVAILABLE:
        # token_sort_ratio handles "Mondal Sulata" vs "Sulata Mondal"
        score = fuzz.token_sort_ratio(a_norm, b_norm)
        logger.debug(f"rapidfuzz score: '{a_norm}' vs '{b_norm}' = {score}")
        return float(score)
    else:
        # Basic fallback: exact match after normalise
        if a_norm == b_norm:
            return 100.0
        # Partial: check if one is contained in the other
        if a_norm in b_norm or b_norm in a_norm:
            return 75.0
        return 0.0


# ── Public API ─────────────────────────────────────────────────────────────────

def check_name_match(name_a: str, name_b: str,
                     label_a: str = "Doc A", label_b: str = "Doc B") -> dict:
    """
    Check if two names match within acceptable threshold.

    Returns:
        {
          "is_mismatch": bool,
          "score": float,        # 0–100, higher = more similar
          "name_a": str,
          "name_b": str,
          "label_a": str,
          "label_b": str,
          "detail": str          # human-readable explanation
        }

    Example:
        check_name_match("Sulata Mondal", "Sulata", "Aadhaar", "Bank")
        → {"is_mismatch": True, "score": 72.7, ...}
    """
    score = _similarity_score(name_a, name_b)
    is_mismatch = score < MATCH_THRESHOLD

    if is_mismatch:
        detail = (
            f"MISMATCH: '{name_a}' ({label_a}) vs '{name_b}' ({label_b}). "
            f"Similarity: {score:.1f}/100. Fix before applying."
        )
    else:
        detail = (
            f"MATCH: '{name_a}' ({label_a}) matches '{name_b}' ({label_b}). "
            f"Similarity: {score:.1f}/100."
        )

    logger.info(detail)

    return {
        "is_mismatch": is_mismatch,
        "score": round(score, 1),
        "name_a": name_a,
        "name_b": name_b,
        "label_a": label_a,
        "label_b": label_b,
        "detail": detail
    }


def check_address_match(address_a: str, address_b: str,
                        label_a: str = "Doc A", label_b: str = "Doc B") -> dict:
    """
    Check if two addresses match.
    Uses a slightly lower threshold (85) since addresses often have
    minor formatting differences.

    Returns same shape as check_name_match.
    """
    ADDRESS_THRESHOLD = 85
    score = _similarity_score(address_a, address_b)
    is_mismatch = score < ADDRESS_THRESHOLD

    detail = (
        f"{'MISMATCH' if is_mismatch else 'MATCH'}: "
        f"'{address_a}' ({label_a}) vs '{address_b}' ({label_b}). "
        f"Similarity: {score:.1f}/100."
    )

    logger.info(detail)

    return {
        "is_mismatch": is_mismatch,
        "score": round(score, 1),
        "address_a": address_a,
        "address_b": address_b,
        "label_a": label_a,
        "label_b": label_b,
        "detail": detail
    }


def check_dob_match(dob_a: str, dob_b: str,
                    label_a: str = "Doc A", label_b: str = "Doc B") -> dict:
    """
    Check if two date of birth strings match.
    Normalises common date formats before comparing:
      "01/01/1990", "01-01-1990", "1990-01-01" → all treated as same

    Returns same shape as check_name_match.
    """
    def normalise_date(d: str) -> str:
        if not d:
            return ""
        # Remove all separators, just compare the digits
        return re.sub(r"[/\-.\s]", "", d.strip())

    a_norm = normalise_date(dob_a)
    b_norm = normalise_date(dob_b)

    is_mismatch = (a_norm != b_norm) or not a_norm

    detail = (
        f"{'MISMATCH' if is_mismatch else 'MATCH'}: "
        f"'{dob_a}' ({label_a}) vs '{dob_b}' ({label_b})."
    )

    return {
        "is_mismatch": is_mismatch,
        "score": 0.0 if is_mismatch else 100.0,
        "dob_a": dob_a,
        "dob_b": dob_b,
        "label_a": label_a,
        "label_b": label_b,
        "detail": detail
    }