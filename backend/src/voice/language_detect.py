"""
src/voice/language_detect.py
Detects language from raw text input (not audio).
Used ONLY when user sends TEXT — Sarvam STT handles audio detection.
Pure Python. Zero external calls.
"""


def detect_language(text: str) -> str:
    r"""
    Detects language from raw text.
    Returns: "bn-IN" | "hi-IN" | "en-IN"

    Method: count characters in Unicode script ranges.
      Bengali:    U+0980–U+09FF
      Devanagari: U+0900–U+097F
      Latin:      U+0041–U+005A (A-Z uppercase)
                  U+0061–U+007A (a-z lowercase)  ← TWO ranges, not one
                  (single range 0041-007A includes garbage chars like [, \, ^)

    Language = whichever script has the most characters.
    Ties → default "en-IN"
    """

    bengali_count    = 0
    devanagari_count = 0
    latin_count      = 0

    for char in text:
        cp = ord(char)
        if 0x0980 <= cp <= 0x09FF:
            bengali_count += 1
        elif 0x0900 <= cp <= 0x097F:
            devanagari_count += 1
        elif (0x0041 <= cp <= 0x005A) or (0x0061 <= cp <= 0x007A):
            # FIX: two separate ranges — uppercase A-Z and lowercase a-z
            # Previous single range 0x0041-0x007A incorrectly included
            # chars like [, \, ], ^, _, ` between the two letter blocks
            latin_count += 1

    max_count = max(bengali_count, devanagari_count, latin_count)

    if max_count == 0:
        return "en-IN"   # empty or numeric-only → default English

    if bengali_count == max_count:
        return "bn-IN"
    elif devanagari_count == max_count:
        return "hi-IN"
    else:
        return "en-IN"


# Scheme keywords for is_greeting / is_out_of_scope
# Defined once, used by both functions — no duplication
_SCHEME_KEYWORDS = [
    "scheme", "যোজনা", "প্রকল্প", "eligible", "যোগ্য",
    "document", "কাগজ", "benefit", "সুবিধা",
    "lakshmir", "লক্ষ্মীর", "লক্ষ্মীর ভাণ্ডার",
    "swasthya", "স্বাস্থ্য",
    "kanyashree", "কন্যাশ্রী",
    "rupashree", "রূপশ্রী",
    "yuva", "যুবসাথী",
    "samajik", "সামাজিক",
    "apply", "আবেদন",
    "aadhaar", "আধার",
    "ration", "রেশন",
    "pension", "পেনশন",
    "bank", "ব্যাংক",
    "prakalpa", "প্রকল্প"
]

# FIX: deduplicated — removed duplicate "হ্যালো" and "নমস্কার" entries
_GREETING_LIST = {
    "hi", "hello", "hey",
    "হ্যালো", "হেলো", "হাই",
    "নমস্কার", "namaskar",
    "namaste", "নমস্তে"
}


def is_greeting(text: str) -> bool:
    """
    Returns True if the message is a greeting with no scheme content.
    Two conditions trigger True:
      1. Normalized text is in greeting list, OR
      2. Text is short (< 15 chars) AND contains no scheme keywords
    """
    normalized = text.strip().lower()

    if normalized in _GREETING_LIST:
        return True

    if len(normalized) < 15:
        for keyword in _SCHEME_KEYWORDS:
            if keyword in normalized:
                return False
        return True

    return False


def is_out_of_scope(text: str) -> bool:
    """
    Returns True if text contains NONE of the scheme keywords.
    Used by guardrails to short-circuit before any API calls.
    Example: "what's the weather" → True (out of scope)
    Example: "লক্ষ্মীর ভাণ্ডার eligible?" → False (in scope)
    """
    normalized = text.strip().lower()
    for keyword in _SCHEME_KEYWORDS:
        if keyword in normalized:
            return False
    return True