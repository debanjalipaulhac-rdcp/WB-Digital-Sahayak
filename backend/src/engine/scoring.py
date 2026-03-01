"""
src/engine/scoring.py
======================
Readiness Score calculator (0–100).

Takes a list of issue objects from eligibility.py and returns
a final weighted score with band classification.

Score bands:
    80–100  GREEN  "Go to office tomorrow"
    50–79   AMBER  "Fix issues first, then go"
    0–49    RED    "Do NOT go yet — you will be rejected"

This file does ONE thing: calculate scores.
It does not run eligibility checks. It does not know about schemes.
Feed it issues, get back a score.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


# ── Score Deduction Map ────────────────────────────────────────────────────────
# Centralised weights. Changing a weight here changes it everywhere.
# These must match the values in schemes.json — schemes.json is the source of truth
# for per-scheme weights; this map handles engine-level overrides.

SCORE_BANDS = {
    "GREEN": {"min": 80, "max": 100, "label": "Go to office tomorrow", "label_bn": "আগামীকাল অফিসে যান"},
    "AMBER": {"min": 50, "max": 79,  "label": "Fix issues first, then go", "label_bn": "আগে সমস্যা ঠিক করুন, তারপর যান"},
    "RED":   {"min": 0,  "max": 49,  "label": "Do NOT go yet — follow the roadmap first", "label_bn": "এখনই যাবেন না — আগে roadmap অনুসরণ করুন"},
}

ISSUE_TYPES = {
    "INELIGIBLE": "ineligible",    # fails basic eligibility — game over
    "FATAL":      "fatal",         # critical issue — will be rejected
    "WARNING":    "warning",       # non-blocking but risks delay
    "MISSING_DOC": "missing_doc",  # required document not present
}


# ── Band classifier ───────────────────────────────────────────────────────────
def get_band(score: int) -> str:
    if score >= 80:
        return "GREEN"
    elif score >= 50:
        return "AMBER"
    return "RED"


def get_band_detail(band: str) -> dict:
    return SCORE_BANDS.get(band, SCORE_BANDS["RED"])


# ── Main scoring function ──────────────────────────────────────────────────────
def calculate_score(issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate readiness score from a list of issues.

    Args:
        issues: list of issue dicts, each with at least:
            {
              "type": "fatal" | "warning" | "missing_doc" | "ineligible",
              "code": str,
              "score_deduction": int,
              ...
            }

    Returns:
        {
          "score": int,          # 0–100
          "band": str,           # GREEN | AMBER | RED
          "band_label": str,     # human-readable verdict
          "band_label_bn": str,  # Bengali verdict
          "total_deduction": int,
          "breakdown": list      # which issues caused which deductions
        }

    Example:
        issues = [
            {"type": "fatal", "code": "NAME_MISMATCH", "score_deduction": 35},
            {"type": "fatal", "code": "DORMANT_ACCOUNT", "score_deduction": 25},
        ]
        → score = 40, band = RED
    """
    base_score = 100
    total_deduction = 0
    breakdown = []

    # If ANY ineligible issue exists — score is 0, game over
    ineligible_issues = [i for i in issues if i.get("type") == ISSUE_TYPES["INELIGIBLE"]]
    if ineligible_issues:
        for issue in ineligible_issues:
            breakdown.append({
                "code": issue.get("code"),
                "type": "ineligible",
                "deduction": 100,
                "reason": issue.get("message", "Basic eligibility failed")
            })
        logger.info(f"Score: 0 (INELIGIBLE) — {[i['code'] for i in ineligible_issues]}")
        band = "RED"
        return {
            "score": 0,
            "band": band,
            "band_label": get_band_detail(band)["label"],
            "band_label_bn": get_band_detail(band)["label_bn"],
            "total_deduction": 100,
            "breakdown": breakdown
        }

    # Accumulate deductions from all other issue types
    for issue in issues:
        issue_type = issue.get("type", "")
        deduction = issue.get("score_deduction", 0)

        if issue_type == ISSUE_TYPES["INELIGIBLE"]:
            continue   # handled above

        if deduction > 0:
            total_deduction += deduction
            breakdown.append({
                "code": issue.get("code"),
                "type": issue_type,
                "deduction": deduction,
                "reason": issue.get("message", "")
            })

    final_score = max(0, base_score - total_deduction)
    band = get_band(final_score)

    logger.info(
        f"Score: {final_score}/100 ({band}) | "
        f"Deductions: {total_deduction} | "
        f"Issues: {[i.get('code') for i in issues]}"
    )

    return {
        "score": final_score,
        "band": band,
        "band_label": get_band_detail(band)["label"],
        "band_label_bn": get_band_detail(band)["label_bn"],
        "total_deduction": total_deduction,
        "breakdown": breakdown
    }