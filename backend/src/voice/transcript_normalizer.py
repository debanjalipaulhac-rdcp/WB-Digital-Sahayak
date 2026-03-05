"""
src/voice/transcript_normalizer.py
===================================
Post-STT transcript normalizer.
Problem: Sarvam STT with mode="translate" translates scheme NAMES into English meaning.
  "স্বাস্থ্যসাথী" → "health companion"   (wrong — should stay "swasthya sathi")
  "যুবসাথী"       → "young companion"    (wrong — should stay "yuva sathi")
  "লক্ষ্মীর ভাণ্ডার" → "lakshmi treasury" (wrong — should stay "lakshmir bhandar")

Fix: fuzzy match translated English terms → canonical scheme name.
Uses rapidfuzz token_set_ratio for partial phrase matching.
Threshold tuned per scheme to avoid false positives.

Called ONCE right after STT, before intent routing.
Zero API calls. Pure Python.
"""

import re
import logging
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# SCHEME ALIAS MAP
# Key   = canonical scheme name (what the router understands)
# Value = list of (alias_phrase, min_score) tuples
#
# HOW TO READ THE SCORE:
#   fuzz.token_set_ratio("health companion", "health companion") = 100
#   fuzz.token_set_ratio("helth companon",   "health companion") = 88   ← typo
#   fuzz.token_set_ratio("young friend",     "health companion") = 30   ← wrong
#
# Set threshold HIGH (85+) for short common words to avoid false positives.
# Set threshold LOWER (75+) for long unique phrases that can't be confused.
# ─────────────────────────────────────────────────────────────

SCHEME_ALIASES: list[dict] = [
    {
        "canonical": "swasthya sathi",
        "aliases": [
            ("health companion",     85),
            ("health friend",        85),
            ("health partner",       82),
            ("health साथी",          80),
            ("swasthya sathi",       90),
            ("swasthyasathi",        88),
            ("swastha sathi",        85),
            ("swasthya sati",        85),
            ("swasthya saathi",      85),
            ("sastha sathi",         83),   # common mispronunciation
            ("shastra sathi",         60),   # common mispronunciation
            ("sasthya sathi",        83),
            ("health scheme",        75),
            ("health insurance",     72),
            ("hospital scheme",      72),
        ]
    },
    {
        "canonical": "lakshmir bhandar",
        "aliases": [
            ("lakshmi treasury",     80),
            ("laxmi treasury",       80),
            ("lakshmi bhandar",      90),
            ("lakshmibhandar",       88),
            ("laxmi bhandar",        88),
            ("lakshmir bhandar",     95),
            ("lakshmi store",        78),
            ("lakshmi warehouse",    75),
            ("lakshmi granary",      75),
            ("লক্ষ্মীর ভাণ্ডার",       95),
            ("women scheme",         65),   # low threshold, common term
            ("monthly cash",         65),
        ]
    },
    {
        "canonical": "kanyashree",
        "aliases": [
            ("girl fortune",         78),
            ("daughter fortune",     78),
            ("kanyashree",           95),
            ("kanya shree",          90),
            ("kanyasri",             88),
            ("kannyashree",          85),
            ("girl scheme",          70),
            ("daughter scheme",      70),
            ("scholarship girl",     70),
        ]
    },
    {
        "canonical": "yuva sathi",
        "aliases": [
            ("young companion",      85),
            ("youth companion",      85),
            ("young friend",         82),
            ("youth friend",         82),
            ("young partner",        80),
            ("youth partner",        80),
            ("yuva sathi",           95),
            ("yubasathi",            88),   # common bengali pronunciation
            ("jubasathi",            88),
            ("juba sathi",           85),
            ("jugo sathi",           75),
            ("yuba sathi",           85),
            ("yuva sati",            85),
            ("youth scheme",         72),
            ("unemployment scheme",  70),
            ("young stipend",        72),
        ]
    },
    {
        "canonical": "rupashree",
        "aliases": [
            ("beautiful fortune",    75),
            ("beauty fortune",       75),
            ("marriage grant",       72),
            ("wedding grant",        72),
            ("rupashree",            95),
            ("rupa shree",           90),
            ("rupasri",              88),
            ("ruposhri",             85),
        ]
    },
    {
        "canonical": "samajik suraksha",
        "aliases": [
            ("social security",      82),
            ("social protection",    80),
            ("social safety",        78),
            ("pension scheme",       72),
            ("old age pension",      72),
            ("samajik suraksha",     95),
            ("samajik surakhsha",    88),
            ("widow pension",        70),
        ]
    },
]


def _find_best_scheme_match(phrase: str) -> tuple[str | None, int]:
    """
    Compare phrase against all aliases using token_set_ratio.
    Returns (canonical_name, score) of best match above threshold.
    Returns (None, 0) if no match found.

    token_set_ratio is used because:
    - It ignores word order: "companion health" matches "health companion"
    - It handles extra words: "my health companion card" still matches
    - It handles partial matches better than simple ratio
    """
    best_canonical = None
    best_score     = 0

    for scheme in SCHEME_ALIASES:
        for alias, threshold in scheme["aliases"]:
            score = fuzz.token_set_ratio(phrase.lower(), alias.lower())
            if score >= threshold and score > best_score:
                best_score     = score
                best_canonical = scheme["canonical"]

    return best_canonical, best_score


def normalize_transcript(transcript: str) -> str:
    """
    Main entry point. Run this on every STT transcript before routing.

    Strategy:
      1. Split transcript into overlapping windows of 1–4 words
      2. For each window, check if it fuzzy-matches a scheme alias
      3. If match found above threshold → replace window with canonical name
      4. Return cleaned transcript

    Example:
      Input:  "I want to know about health companion scheme"
      Output: "I want to know about swasthya sathi scheme"

      Input:  "young companion ke liye apply karna hai"
      Output: "yuva sathi ke liye apply karna hai"
    """
    if not transcript or not transcript.strip():
        return transcript

    words        = transcript.split()
    replacements = []   # list of (start_idx, end_idx, canonical_name, score)

    # Slide windows of size 1 to 4 over the word list
    for window_size in [4, 3, 2, 1]:
        for start in range(len(words) - window_size + 1):
            phrase = " ".join(words[start:start + window_size])
            canonical, score = _find_best_scheme_match(phrase)

            if canonical:
                # Check this window doesn't overlap with already-found replacement
                overlap = any(
                    not (start >= r[1] or start + window_size <= r[0])
                    for r in replacements
                )
                if not overlap:
                    replacements.append((start, start + window_size, canonical, score))
                    logger.info(
                        f"[normalizer] '{phrase}' → '{canonical}' (score={score})"
                    )

    if not replacements:
        return transcript

    # Apply replacements — build new word list
    # Sort by start position to apply in order
    replacements.sort(key=lambda r: r[0])

    new_words  = []
    covered_up = 0

    for start, end, canonical, score in replacements:
        # Add words before this replacement
        new_words.extend(words[covered_up:start])
        # Add canonical scheme name
        new_words.extend(canonical.split())
        covered_up = end

    # Add remaining words after last replacement
    new_words.extend(words[covered_up:])

    normalized = " ".join(new_words)

    if normalized != transcript:
        logger.info(f"[normalizer] '{transcript[:80]}' → '{normalized[:80]}'")

    return normalized