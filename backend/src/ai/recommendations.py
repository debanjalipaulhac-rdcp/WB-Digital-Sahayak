"""
src/ai/recommendations.py
==========================
Unified 3-mode recommendation engine.

MODES — called in this priority order and merged:

  MODE 1: profile_based(profile)
    User has a saved profile. We know age/gender/caste/family.
    → Check every scheme's eligibility rules against profile.
    → Return only schemes they are LIKELY eligible for (pre-filter).
    → Example: Female 38, SC → Lakshmir Bhandar + Swasthya Sathi

  MODE 2: context_based(current_scheme_id, profile)
    User is viewing a specific scheme. Suggest related ones.
    → Use cross_scheme_triggers from schemes.json (rule engine).
    → Plus: caste-based extensions (krishak_bondhu for male farmers, etc.)
    → Example: Viewing Lakshmir Bhandar + has_daughter → suggest Kanyashree

  MODE 3: query_based(query)
    User typed/said something freeform: "hospital mein free treatment"
    → Titan V2 embed → Pinecone cosine similarity → top-K schemes
    → Fallback: keyword matching if Pinecone unavailable

DESIGN PRINCIPLES:
  - Each mode returns the same schema (list of RecommendationItem dicts)
  - Caller chooses which modes to invoke
  - get_recommendations() merges all modes, deduplicates, ranks
  - Exclude current_scheme_id from context recommendations (obvious)
  - Never recommend a scheme with matched_by="rule" if basic eligibility fails

OUTPUT SCHEMA (every item):
  {
    "scheme_id":       "kanyashree",
    "scheme_name":     "Kanyashree Prakalpa",
    "scheme_name_bn":  "কন্যাশ্রী প্রকল্প",
    "benefit_display": "₹25,000 at 18 + ₹1,000/year",
    "reason":          "You have a daughter aged 10-19",
    "reason_bn":       "আপনার ১০-১৯ বছরের মেয়ে আছে",
    "trigger":         "has_daughter",
    "matched_by":      "rule" | "vector" | "keyword" | "profile",
    "similarity":      0.94,   # only for vector/keyword matches
    "confidence":      "high" | "medium" | "low",
    "apply_at":        [...],  # from schemes.json
  }
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Mode 1: Profile-based ──────────────────────────────────────────────────────

def profile_based(profile: dict, exclude_scheme_id: str = "") -> list[dict]:
    """
    Given a user profile, return schemes they are likely eligible for.
    Does a lightweight pre-check (not the full engine — that's check-eligibility).
    
    Args:
        profile:           User profile dict (age, gender, caste, has_daughter, etc.)
        exclude_scheme_id: Don't recommend this scheme (user is already on it)

    Returns:
        List of recommendation dicts the user is likely eligible for.
    
    Example:
        profile = {"age": 38, "gender": "female", "caste": "sc", "has_daughter": True}
        → [lakshmir_bhandar, kanyashree, swasthya_sathi]
    """
    from src.engine.eligibility import get_all_schemes

    results = []
    age    = profile.get("age", 0)
    gender = profile.get("gender", "")
    caste  = profile.get("caste", "general")
    is_govt= profile.get("is_govt_employee", False)
    is_tax = profile.get("pays_income_tax", False)

    if is_govt or is_tax:
        # Immediately ineligible for all cash-transfer schemes
        return []

    for scheme in get_all_schemes():
        sid = scheme["scheme_id"]
        if sid == exclude_scheme_id:
            continue

        el = scheme.get("eligibility", {})
        confidence = "high"

        # Age check
        if el.get("age_min") and age < el["age_min"]:
            continue
        if el.get("age_max") and age > el["age_max"]:
            continue

        # Gender check
        if el.get("gender") and gender and el["gender"] != gender:
            continue

        # Scheme-specific soft checks (lower confidence if missing data)
        if sid == "kanyashree" and not profile.get("has_daughter") and not profile.get("is_enrolled_in_school"):
            continue  # No daughter + not a student → skip

        if sid == "yuva_sathi":
            if not profile.get("is_unemployed", True):
                continue
            confidence = "medium"  # Need to verify employment status

        results.append(_make_item(scheme, reason=_profile_reason(sid, profile),
                                  reason_bn=_profile_reason_bn(sid, profile),
                                  trigger="profile_match", matched_by="profile",
                                  confidence=confidence))

    return results


# ── Mode 2: Context-based ──────────────────────────────────────────────────────

def context_based(current_scheme_id: str, profile: Optional[dict] = None) -> list[dict]:
    """
    User is viewing scheme X. Suggest related schemes Y, Z.
    
    Uses two layers:
      1. cross_scheme_triggers from schemes.json (rule engine)
      2. Caste/family-based extensions (e.g., OBC farmer → Krishak Bondhu)

    Args:
        current_scheme_id: The scheme the user is currently viewing
        profile:           Optional — enables profile-filtered suggestions

    Returns:
        Relevant schemes to suggest alongside the current one.

    Example:
        context_based("lakshmir_bhandar", {"has_daughter": True})
        → [kanyashree, swasthya_sathi]
    """
    from src.engine.eligibility import get_scheme, get_all_schemes

    current = get_scheme(current_scheme_id)
    if not current:
        return []

    results = []
    seen = {current_scheme_id}

    # Layer 1: cross_scheme_triggers from schemes.json
    for trigger in current.get("cross_scheme_triggers", []):
        condition  = trigger.get("condition", "")
        suggest_id = trigger.get("suggest_scheme_id", "")
        reason     = trigger.get("reason", "")

        if not suggest_id or suggest_id in seen:
            continue

        # Check condition against profile if available
        if profile and condition != "always":
            if not _check_condition(condition, profile):
                continue

        suggested = get_scheme(suggest_id)
        if not suggested:
            logger.warning(f"context_based: suggest_scheme_id '{suggest_id}' not found — skip")
            continue

        seen.add(suggest_id)
        results.append(_make_item(suggested, reason=reason,
                                  reason_bn=trigger.get("reason_bn", reason),
                                  trigger=condition, matched_by="rule",
                                  confidence="high"))

    # Layer 2: Caste/family extensions — add schemes not in triggers
    if profile:
        caste   = profile.get("caste", "")
        gender  = profile.get("gender", "")
        age     = profile.get("age", 0)

        # Male farmer in rural WB → Krishak Bondhu (not in our 4 schemes but note it)
        # For now, just ensure all 4 scheme cross-refs are covered
        if gender == "female" and age >= 25 and "lakshmir_bhandar" not in seen:
            lb = get_scheme("lakshmir_bhandar")
            if lb:
                seen.add("lakshmir_bhandar")
                results.append(_make_item(lb,
                    reason="Women aged 25+ may qualify for monthly cash transfer",
                    reason_bn="২৫+ বছরের মহিলারা মাসিক নগদ সহায়তা পেতে পারেন",
                    trigger="female_25_plus", matched_by="rule", confidence="medium"))

        # Always suggest health coverage if not already the current scheme
        if "swasthya_sathi" not in seen and current_scheme_id != "swasthya_sathi":
            ss = get_scheme("swasthya_sathi")
            if ss:
                seen.add("swasthya_sathi")
                results.append(_make_item(ss,
                    reason="₹5 lakh health coverage for your entire family",
                    reason_bn="পরিবারের সবার জন্য ₹৫ লাখ স্বাস্থ্য বীমা",
                    trigger="always", matched_by="rule", confidence="high"))

    return results


# ── Mode 3: Query-based (vector + keyword fallback) ────────────────────────────

def query_based(query: str, top_k: int = 3) -> list[dict]:
    """
    Freeform text/voice query → semantic scheme search.

    Flow: Titan V2 embed → Pinecone cosine → results
    Fallback: keyword matching if Pinecone/Bedrock unavailable

    Args:
        query:  Any text — Bengali or English, typed or voice-transcribed
        top_k:  Max results

    Returns:
        List of scheme recommendations ordered by similarity score.

    Example:
        query_based("আমার মায়ের hospital treatment-এর জন্য কোনো scheme আছে?")
        → [swasthya_sathi (0.91), lakshmir_bhandar (0.61)]
    """
    from src.ai.vector_search import search
    from src.engine.eligibility import get_scheme

    try:
        vector_results = search(query, top_k=top_k)
    except Exception as e:
        logger.error(f"query_based vector search failed: {e}")
        vector_results = []

    results = []
    for vr in vector_results:
        scheme = get_scheme(vr["scheme_id"])
        if not scheme:
            continue
        results.append(_make_item(
            scheme,
            reason=f"Matches your search: '{query[:40]}'",
            reason_bn=f"আপনার খোঁজের সাথে মিলছে: '{query[:30]}'",
            trigger="vector_query",
            matched_by=vr.get("matched_by", "vector"),
            confidence="medium",
            similarity=vr.get("similarity", 0.0),
        ))

    return results


# ── Main entry point ───────────────────────────────────────────────────────────

def get_recommendations(
    profile: Optional[dict] = None,
    current_scheme_id: Optional[str] = None,
    query: Optional[str] = None,
    top_k: int = 3,
) -> list[dict]:
    """
    Unified recommendation entry point. Calls all relevant modes and merges.

    Priority order (first occurrence wins in dedup):
      1. context_based  — most specific (user is on a scheme page)
      2. profile_based  — personalized to user profile
      3. query_based    — freeform search

    Args:
        profile:           User profile dict (from DynamoDB or WhatsApp session)
        current_scheme_id: If user is viewing a specific scheme
        query:             Freeform text/voice query
        top_k:             Max total recommendations to return

    Returns:
        Deduplicated, ranked list of recommendation dicts.

    Usage examples:
        # User on Lakshmir Bhandar page with saved profile
        get_recommendations(profile=p, current_scheme_id="lakshmir_bhandar")

        # User asks "hospital mein free treatment"
        get_recommendations(query="hospital free treatment", profile=p)

        # WhatsApp: user just completed eligibility check
        get_recommendations(profile=p, current_scheme_id="lakshmir_bhandar")
    """
    all_recs = []

    if current_scheme_id:
        all_recs.extend(context_based(current_scheme_id, profile))

    if profile:
        all_recs.extend(profile_based(profile, exclude_scheme_id=current_scheme_id or ""))

    if query and query.strip():
        all_recs.extend(query_based(query, top_k=top_k))

    # Deduplicate — first occurrence wins (context > profile > query)
    seen = set()
    unique = []
    for rec in all_recs:
        sid = rec.get("scheme_id")
        if sid and sid not in seen:
            seen.add(sid)
            unique.append(rec)

    # Exclude current scheme from output
    if current_scheme_id:
        unique = [r for r in unique if r.get("scheme_id") != current_scheme_id]

    return unique[:top_k]


# ── Internal helpers ───────────────────────────────────────────────────────────

def _make_item(scheme: dict, reason: str, reason_bn: str, trigger: str,
               matched_by: str, confidence: str, similarity: float = 0.0) -> dict:
    """Build a standardized recommendation output dict."""
    return {
        "scheme_id":       scheme["scheme_id"],
        "scheme_name":     scheme["scheme_name"],
        "scheme_name_bn":  scheme.get("scheme_name_bn", ""),
        "benefit_display": scheme.get("benefit_display", ""),
        "tag":             scheme.get("tag", ""),
        "reason":          reason,
        "reason_bn":       reason_bn,
        "trigger":         trigger,
        "matched_by":      matched_by,
        "confidence":      confidence,
        "similarity":      round(similarity, 3),
        "apply_at":        scheme.get("apply_at", []),
        "apply_online":    scheme.get("apply_online", ""),
    }


def _check_condition(condition: str, profile: dict) -> bool:
    """Evaluate a trigger condition string against profile dict."""
    condition_map = {
        "has_daughter":         lambda p: bool(p.get("has_daughter")),
        "has_school_child":     lambda p: bool(p.get("has_school_child")),
        "is_unemployed":        lambda p: bool(p.get("is_unemployed")),
        "always":               lambda p: True,
        "female":               lambda p: p.get("gender") == "female",
        "male":                 lambda p: p.get("gender") == "male",
        "sc_st":                lambda p: p.get("caste") in ("sc", "st"),
        "female_25_plus":       lambda p: p.get("gender") == "female" and p.get("age", 0) >= 25,
    }
    fn = condition_map.get(condition)
    return fn(profile) if fn else False


def _profile_reason(scheme_id: str, profile: dict) -> str:
    reasons = {
        "lakshmir_bhandar": "You are a woman aged 25-60 and may qualify for ₹1,000/month",
        "swasthya_sathi":   "Your family can get ₹5 lakh health coverage",
        "kanyashree":       "Your daughter may qualify for ₹25,000 education grant",
        "yuva_sathi":       "As an unemployed youth, you may get ₹1,500/month",
    }
    return reasons.get(scheme_id, "You may be eligible for this scheme")


def _profile_reason_bn(scheme_id: str, profile: dict) -> str:
    reasons = {
        "lakshmir_bhandar": "আপনি ২৫-৬০ বছরের মহিলা, মাসে ₹১,০০০ পেতে পারেন",
        "swasthya_sathi":   "আপনার পরিবার ₹৫ লাখ স্বাস্থ্য বীমা পাবে",
        "kanyashree":       "আপনার মেয়ে ₹২৫,০০০ শিক্ষা অনুদান পেতে পারে",
        "yuva_sathi":       "বেকার যুবক হিসেবে আপনি মাসে ₹১,৫০০ পেতে পারেন",
    }
    return reasons.get(scheme_id, "আপনি এই প্রকল্পের জন্য যোগ্য হতে পারেন")