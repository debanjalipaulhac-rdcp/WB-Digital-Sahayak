"""
src/ai/language_detector.py
============================
Detect which language the user is writing in.

WHY THIS EXISTS:
  Sulata might type in Bengali: "আমার কত score হলো?"
  A youth from Kolkata might type in English: "what is my readiness score?"
  We respond in the same language they used.

SUPPORTED LANGUAGES (MVP):
  "bn" — Bengali (বাংলা)  ← primary target users
  "en" — English          ← urban/educated users

FUTURE:
  "hi" — Hindi
  "sat" — Santali (tribal dialects, Phase 3)

HOW IT WORKS:
  1. Unicode range check — Bengali script is U+0980–U+09FF
     If >15% of chars are in this range → Bengali
  2. Keyword check — Bengali romanized words ("ami", "amar", "koto", "bhalo")
  3. Default → English (safe fallback)

NO EXTERNAL API — pure Python, zero latency, zero cost.
"""

import re
import logging

logger = logging.getLogger(__name__)

# ── Bengali Unicode range ──────────────────────────────────────────────────────
BENGALI_UNICODE_START = 0x0980
BENGALI_UNICODE_END   = 0x09FF

# Threshold: if this fraction of chars are Bengali Unicode → classify as Bengali
BENGALI_CHAR_THRESHOLD = 0.15

# Romanized Bengali keywords (transliterated Bengali commonly typed on phones)
ROMANIZED_BENGALI_KEYWORDS = {
    "ami", "amar", "apnar", "apni", "aache", "ache", "hobe", "hoye", "nei",
    "ki", "koto", "bhalo", "bhaalo", "jabo", "gele", "asun", "jai", "jan",
    "kori", "kora", "niye", "diye", "pelam", "pabo", "chai", "chahi",
    "bolo", "bolen", "korbo", "korben", "jani", "janina", "thakbo",
    "daktar", "hospital", "sarkari", "sarkar", "scheme", "taka",
    "bondhu", "didi", "boudi", "mashima", "kakima", "baba", "ma",
    "gram", "para", "panchayat", "block", "bdo", "thana",
    # common sentence starters
    "amake", "amader", "apnake", "apnader", "tar", "tader", "ekhane",
    "okhane", "akhn", "ekhon", "age", "pore", "kal", "aaj", "parbo",
}

# English indicator keywords — if these dominate, it's English
ENGLISH_STRONG_KEYWORDS = {
    "the", "is", "are", "was", "were", "have", "has", "been", "will",
    "would", "could", "should", "my", "your", "their", "what", "how",
    "when", "where", "which", "who", "please", "thank", "hello", "hi",
    "okay", "yes", "no", "not", "and", "but", "or", "for", "with",
    "about", "need", "want", "get", "check", "apply", "scheme", "document",
}


def detect_language(text: str) -> str:
    """
    Detect the language of user input text.

    Args:
        text: Any user input — typed or voice-transcribed

    Returns:
        Language code: "bn" (Bengali) or "en" (English)

    Examples:
        detect_language("আমার বয়স ৩৮")            → "bn"
        detect_language("My age is 38")            → "en"
        detect_language("ami 38 bochor")           → "bn"  (romanized)
        detect_language("scheme for my wife")      → "en"
        detect_language("আমার wife এর জন্য scheme") → "bn"  (mixed, Bengali dominant)
        detect_language("")                        → "bn"  (default for WB users)
    """
    if not text or not text.strip():
        # Empty = assume Bengali (our primary user base)
        return "bn"

    text_clean = text.strip()

    # ── Check 1: Bengali Unicode character ratio ───────────────────────────────
    total_alpha = sum(1 for c in text_clean if c.isalpha())
    if total_alpha == 0:
        return "bn"  # only numbers/symbols, default Bengali

    bengali_chars = sum(
        1 for c in text_clean
        if BENGALI_UNICODE_START <= ord(c) <= BENGALI_UNICODE_END
    )
    bengali_ratio = bengali_chars / total_alpha

    if bengali_ratio >= BENGALI_CHAR_THRESHOLD:
        logger.debug(f"detect_language: Bengali script ({bengali_ratio:.0%} Bengali chars)")
        return "bn"

    # ── Check 2: Romanized Bengali keywords ───────────────────────────────────
    words = set(re.findall(r"[a-zA-Z]+", text_clean.lower()))
    romanized_hits = len(words & ROMANIZED_BENGALI_KEYWORDS)
    english_hits   = len(words & ENGLISH_STRONG_KEYWORDS)

    if romanized_hits > 0 and romanized_hits >= english_hits:
        logger.debug(f"detect_language: Romanized Bengali ({romanized_hits} keyword hits)")
        return "bn"

    if english_hits > 0:
        logger.debug(f"detect_language: English ({english_hits} keyword hits)")
        return "en"

    # ── Default: Bengali (WB users are our primary audience) ──────────────────
    logger.debug("detect_language: no signal, defaulting to Bengali")
    return "bn"


def get_response_lang(user_text: str, session: dict) -> str:
    """
    Get the language to respond in, with session memory.

    If user has previously indicated a language preference (stored in session),
    use that. Otherwise detect from current message.

    Args:
        user_text: Current message text
        session:   DynamoDB session dict (may contain "lang" key)

    Returns:
        "bn" or "en"
    """
    # Explicit session preference wins
    if session.get("lang") in ("bn", "en", "hi"):
        return session["lang"]

    # Detect from current message
    detected = detect_language(user_text)

    return detected


def is_bengali(text: str) -> bool:
    """Convenience: True if text is Bengali."""
    return detect_language(text) == "bn"


def is_english(text: str) -> bool:
    """Convenience: True if text is English."""
    return detect_language(text) == "en"