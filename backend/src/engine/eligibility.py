"""
src/engine/eligibility.py
==========================
Deterministic eligibility engine. Zero AI. Pure rules.

THREE modes (called from schemes_controller.py):

  1. check_eligibility(scheme_id, profile, checks)
     → Full check for ONE scheme: profile rules + document checks + mismatch
     → Returns score (0-100), band, issues, roadmap

  2. get_eligible_schemes(profile)
     → Filter ALL schemes by profile rules
     → Used by /recommendations when user has complete profile
     → Returns list of matching scheme_ids

  3. get_script(issue_code, lang, **kwargs)
     → Returns "what to say at office" script for a specific issue

PROFILE FIELDS:
  age, gender, caste, district,
  is_govt_employee, pays_income_tax,
  family_income_annual, has_daughter,
  has_school_child, is_enrolled_in_school,
  is_unemployed

DOCUMENT CHECK FIELDS:
  aadhaar_name, bank_name, voter_name, ration_name
  aadhaar_bank_linked, bank_last_transaction_months_ago
  address_match_ok, docs_present, docs_missing
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────

def _load_schemes() -> list:
    """
    Load schemes from DynamoDB. Falls back to JSON.
    NO module-level cache — keeps function patchable in tests.
    (Per-request cost is negligible for ~10 schemes.)
    """
    # Try DynamoDB first
    try:
        from src.repository.dynamo_repo import SchemeRepository
        schemes = SchemeRepository.get_all()
        if schemes:
            return schemes
    except Exception as e:
        logger.warning(f"DynamoDB unavailable, using JSON: {e}")

    # Fallback: JSON
    try:
        json_path = Path(__file__).resolve().parents[2] / "src" / "data" / "schemes.json"
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f).get("schemes", [])
    except Exception as e:
        logger.error(f"Cannot load schemes: {e}")
        return []


def get_all_schemes() -> list:
    return _load_schemes()


def get_scheme(scheme_id: str) -> Optional[dict]:
    return next((s for s in _load_schemes() if s.get("scheme_id") == scheme_id), None)


# ─────────────────────────────────────────────────────────────
# PROFILE ELIGIBILITY RULES
# ─────────────────────────────────────────────────────────────

def _check_profile_rules(scheme: dict, profile: dict) -> tuple[list, list]:
    """
    Check profile against scheme eligibility rules.
    Returns (passed_rules, failed_rules).
    Each rule is a dict: {rule, passed, fatal, message}
    """
    el       = scheme.get("eligibility", {})
    passed   = []
    failed   = []

    age       = int(profile.get("age", 0))
    gender    = str(profile.get("gender", "")).lower()
    caste     = str(profile.get("caste", "general")).lower()
    is_govt   = bool(profile.get("is_govt_employee", False))
    pays_tax  = bool(profile.get("pays_income_tax", False))
    family_income = int(profile.get("family_income_annual", 0))
    has_daughter  = bool(profile.get("has_daughter", False))
    is_student    = bool(profile.get("is_enrolled_in_school", False))
    is_unemployed = bool(profile.get("is_unemployed", False))

    def pass_rule(rule: str, msg: str):
        passed.append({"rule": rule, "passed": True, "fatal": False, "message": msg})

    def fail_rule(rule: str, msg: str, fatal: bool = True):
        failed.append({"rule": rule, "passed": False, "fatal": fatal, "message": msg})

    # ── Gender ────────────────────────────────────────────────
    req_gender = el.get("gender", "all")
    if req_gender and req_gender not in ("all", "any", ""):
        if gender and gender != req_gender.lower():
            fail_rule("gender", f"Scheme is for {req_gender} only.", fatal=True)
        else:
            pass_rule("gender", f"Gender ({gender}) matches requirement.")
    else:
        pass_rule("gender", "No gender restriction.")

    # ── Age ───────────────────────────────────────────────────
    age_min = el.get("age_min") or 0
    age_max = el.get("age_max") or 999

    if age > 0:
        if age < age_min:
            fail_rule("age_min", f"Minimum age is {age_min}. You are {age}.", fatal=True)
        elif age_max < 999 and age > age_max:
            fail_rule("age_max", f"Maximum age is {age_max}. You are {age}.", fatal=True)
        else:
            pass_rule("age", f"Age {age} is within {age_min}–{age_max} range.")

    # ── Government Employee ───────────────────────────────────
    if el.get("not_govt_employee") and is_govt:
        fail_rule("not_govt_employee", "Government employees are not eligible.", fatal=True)
    elif el.get("not_govt_employee"):
        pass_rule("not_govt_employee", "Not a government employee ✓")

    # ── Income Tax ────────────────────────────────────────────
    if el.get("not_income_tax_payer") and pays_tax:
        fail_rule("not_income_tax", "Income tax payers are not eligible.", fatal=True)
    elif el.get("not_income_tax_payer"):
        pass_rule("not_income_tax", "Not an income tax payer ✓")

    # ── Family Income Cap ─────────────────────────────────────
    income_max = el.get("family_income_max")
    if income_max and family_income > 0:
        if family_income > income_max:
            fail_rule(
                "family_income",
                f"Family income ₹{family_income:,} exceeds limit of ₹{income_max:,}.",
                fatal=True
            )
        else:
            pass_rule("family_income", f"Income ₹{family_income:,} is within ₹{income_max:,} limit.")

    # ── Not enrolled in other cash scheme ─────────────────────
    if el.get("not_enrolled_in_other_cash_scheme"):
        enrolled = bool(profile.get("is_enrolled_in_other_cash_scheme", False))
        if enrolled:
            fail_rule("not_enrolled_other", "Cannot be enrolled in another cash transfer scheme.", fatal=True)
        else:
            pass_rule("not_enrolled_other", "Not enrolled in other cash scheme ✓")

    # ── School enrollment (Kanyashree) ───────────────────────
    if el.get("must_be_enrolled_in_school"):
        if not is_student and not has_daughter:
            fail_rule("school_enrollment", "Must be enrolled in school.", fatal=True)
        else:
            pass_rule("school_enrollment", "School enrollment confirmed ✓")

    # ── Unmarried (Kanyashree K2) ─────────────────────────────
    if el.get("must_be_unmarried"):
        is_unmarried = bool(profile.get("is_unmarried", True))
        if not is_unmarried:
            fail_rule("unmarried", "Must be unmarried to qualify.", fatal=True)
        else:
            pass_rule("unmarried", "Unmarried status confirmed ✓")

    # ── State resident ────────────────────────────────────────
    if el.get("state_resident"):
        pass_rule("state_resident", "West Bengal resident ✓")

    return passed, failed


# ─────────────────────────────────────────────────────────────
# DOCUMENT CHECKS
# ─────────────────────────────────────────────────────────────

def _check_documents(scheme: dict, checks: dict) -> tuple[list, int]:
    """
    Check document availability and name mismatches.
    Returns (issues_list, score_deduction).
    """
    issues    = []
    deduction = 0

    docs_present = set(checks.get("docs_present", []))
    docs_missing = set(checks.get("docs_missing", []))

    aadhaar_name  = str(checks.get("aadhaar_name", "")).strip().lower()
    bank_name     = str(checks.get("bank_name", "")).strip().lower()
    voter_name    = str(checks.get("voter_name", "")).strip().lower()
    ration_name   = str(checks.get("ration_name", "")).strip().lower()
    aadhaar_linked = bool(checks.get("aadhaar_bank_linked", True))
    last_txn_months = int(checks.get("bank_last_transaction_months_ago", 0))
    address_ok    = bool(checks.get("address_match_ok", True))

    # ── Required document check ───────────────────────────────
    for doc in scheme.get("documents", []):
        doc_id   = doc.get("doc_id", "")
        required = doc.get("required", False)
        deduct   = doc.get("score_deduction_if_missing", 0)
        label    = doc.get("label", doc_id)
        label_bn = doc.get("label_bn", label)

        if required and doc_id in docs_missing:
            issues.append({
                "type":     "missing_document",
                "code":     f"MISSING_{doc_id.upper()}",
                "severity": "FATAL",
                "doc_id":   doc_id,
                "label":    label,
                "label_bn": label_bn,
                "message":  f"{label} is required but missing.",
                "message_bn": f"{label_bn} প্রয়োজন কিন্তু নেই।",
                "score_deduction": deduct,
                "script_available": False,
                "where_to_get": doc.get("where_to_get_en", ""),
                "display": {
                    "field_a": doc_id,
                    "label_a": label,
                    "value_a": "Missing",
                    "field_b": "required_status",
                    "label_b": "Required Status",
                    "value_b": "Required",
                    "similarity_score": 0.0,
                }
            })
            deduction += deduct

    # ── Name mismatch checks ──────────────────────────────────
    name_map = {
        "aadhaar":      aadhaar_name,
        "bank_passbook": bank_name,
        "voter_id":     voter_name,
        "ration_card":  ration_name,
    }

    for mismatch in scheme.get("mismatch_checks", []):
        doc_a  = mismatch.get("doc_a", "")
        doc_b  = mismatch.get("doc_b", "")
        field  = mismatch.get("field", "name")
        deduct = mismatch.get("score_deduction", 0)
        severity = mismatch.get("severity", "WARNING")

        name_a = name_map.get(doc_a, "")
        name_b = name_map.get(doc_b, "")

        # Only check if both names were provided
        if name_a and name_b:
            if field == "name" and name_a != name_b:
                # Calculate similarity score using fuzzy matching
                from rapidfuzz import fuzz
                similarity = max(
                    fuzz.ratio(name_a, name_b),
                    fuzz.token_sort_ratio(name_a, name_b)
                )
                
                # Get original (non-lowercased) values from checks
                value_a = str(checks.get(f"{doc_a}_name", name_a)).strip()
                value_b = str(checks.get(f"{doc_b.replace('_passbook', '')}_name", name_b)).strip()
                
                issues.append({
                    "type":      "name_mismatch",
                    "code":      mismatch.get("script_code", "NAME_MISMATCH"),
                    "severity":  severity,
                    "check_id":  mismatch.get("check_id", ""),
                    "doc_a":     doc_a,
                    "doc_b":     doc_b,
                    "message":   mismatch.get("message_en", f"Name mismatch between {doc_a} and {doc_b}"),
                    "message_bn": mismatch.get("message_bn", ""),
                    "script_code": mismatch.get("script_code", ""),
                    "script_available": True,
                    "score_deduction": deduct,
                    "display": {
                        "field_a": f"{doc_a}_name",
                        "label_a": mismatch.get("label_a", doc_a.replace("_", " ").title()),
                        "value_a": value_a,
                        "field_b": f"{doc_b}_name",
                        "label_b": mismatch.get("label_b", doc_b.replace("_", " ").title()),
                        "value_b": value_b,
                        "similarity_score": float(similarity),
                    }
                })
                deduction += deduct

        if field == "address" and not address_ok:
            issues.append({
                "type":     "address_mismatch",
                "code":     mismatch.get("script_code", "ADDRESS_MISMATCH"),
                "severity": severity,
                "check_id": mismatch.get("check_id", ""),
                "message":  mismatch.get("message_en", "Address mismatch between documents"),
                "message_bn": mismatch.get("message_bn", ""),
                "script_code": mismatch.get("script_code", ""),
                "script_available": True,
                "score_deduction": deduct,
                "display": {
                    "field_a": "aadhaar_address",
                    "label_a": "Aadhaar Address",
                    "value_a": str(checks.get("aadhaar_address", "")),
                    "field_b": "bank_address",
                    "label_b": "Bank Address",
                    "value_b": str(checks.get("bank_address", "")),
                    "similarity_score": 0.0,
                }
            })
            deduction += deduct

    # ── Bank conditions ───────────────────────────────────────
    bank = scheme.get("bank_conditions", {})

    if bank.get("aadhaar_linked_required") and not aadhaar_linked:
        deduct = bank.get("score_deduction_unlinked", 25)
        issues.append({
            "type":      "bank_unlinked",
            "code":      bank.get("script_code_unlinked", "AADHAAR_UNLINKED"),
            "severity":  "FATAL",
            "message":   "Aadhaar is not linked to bank account. DBT will fail.",
            "message_bn": "ব্যাংক অ্যাকাউন্টের সাথে আধার লিংক নেই। DBT পাবেন না।",
            "script_code": bank.get("script_code_unlinked", "AADHAAR_UNLINKED"),
            "script_available": True,
            "score_deduction": deduct,
            "display": {
                "field_a": "aadhaar_bank_linked",
                "label_a": "Aadhaar-Bank Link Status",
                "value_a": "Not Linked",
                "field_b": "required_status",
                "label_b": "Required Status",
                "value_b": "Must be Linked",
                "similarity_score": 0.0,
            }
        })
        deduction += deduct

    if bank.get("dormant_check"):
        threshold = bank.get("dormant_threshold_months", 6)
        if last_txn_months > threshold:
            deduct = bank.get("score_deduction_dormant", 25)
            issues.append({
                "type":     "dormant_account",
                "code":     bank.get("script_code_dormant", "DORMANT_ACCOUNT"),
                "severity": "FATAL",
                "message":  f"Bank account dormant for {last_txn_months} months. Must be active.",
                "message_bn": f"ব্যাংক অ্যাকাউন্ট {last_txn_months} মাস ধরে নিষ্ক্রিয়।",
                "script_code": bank.get("script_code_dormant", "DORMANT_ACCOUNT"),
                "script_available": True,
                "score_deduction": deduct,
                "display": {
                    "field_a": "bank_last_transaction_months_ago",
                    "label_a": "Last Transaction",
                    "value_a": f"{last_txn_months} months ago",
                    "field_b": "dormant_threshold",
                    "label_b": "Maximum Allowed",
                    "value_b": f"{threshold} months",
                    "similarity_score": 0.0,
                }
            })
            deduction += deduct

    return issues, deduction


# ─────────────────────────────────────────────────────────────
# SCORING
# ─────────────────────────────────────────────────────────────

def _calculate_score(fatal_rules: list, doc_issues: list, doc_deduction: int, eligible_basic: bool) -> tuple[int, str]:
    """
    Score from 100.
    Fatal profile rule failure → score = 0, band = RED.
    Doc issues deduct from score.
    Band: GREEN ≥80, AMBER 50-79, RED <50
    
    If eligible_basic is True, minimum score is 5 (for ScoreMeter animation).
    If eligible_basic is False, score is always 0.
    """
    # Fatal rule failure → immediately RED with score 0
    fatal_failures = [r for r in fatal_rules if r.get("fatal") and not r.get("passed")]
    if fatal_failures or not eligible_basic:
        return 0, "RED"

    # Eligible users: minimum score is 5 to enable ScoreMeter animation
    score = max(5, 100 - doc_deduction)

    if score >= 80:
        band = "GREEN"
    elif score >= 50:
        band = "AMBER"
    else:
        band = "RED"

    return score, band


def _get_band_labels(band: str) -> tuple[str, str]:
    """Return English and Bengali labels for the band."""
    labels = {
        "GREEN": ("Ready to Apply", "আবেদনের জন্য প্রস্তুত"),
        "AMBER": ("Almost Ready", "প্রায় প্রস্তুত"),
        "RED": ("Not Ready", "প্রস্তুত নয়"),
    }
    return labels.get(band, ("Unknown", "অজানা"))


# ─────────────────────────────────────────────────────────────
# ROADMAP BUILDER
# ─────────────────────────────────────────────────────────────

# Bengali translations for roadmap actions
ROADMAP_BN = {
    "NAME_MISMATCH": "আপনার ব্যাংক শাখায় গিয়ে নাম সংশোধনের আবেদন করুন",
    "DORMANT_ACCOUNT": "ছোট লেনদেনের মাধ্যমে অ্যাকাউন্ট সক্রিয় করুন",
    "AADHAAR_UNLINKED": "ব্যাংক শাখায় আধার সংযোগ করুন",
    "MISSING_VOTER_ID": "নির্বাচন অফিস থেকে ভোটার আইডি সংগ্রহ করুন",
    "MISSING_BANK_PASSBOOK": "ব্যাংক শাখা থেকে পাসবুক নিন",
    "MISSING_AADHAAR": "আধার সেবা কেন্দ্র থেকে আধার কার্ড নিন",
    "MISSING_RATION_CARD": "রেশন অফিস থেকে রেশন কার্ড নিন",
    "MISSING_CASTE_CERTIFICATE": "SDO অফিস থেকে জাতি শংসাপত্র নিন",
    "ADDRESS_MISMATCH": "পঞ্চায়েত অফিসে ঠিকানা সংশোধন করুন",
    "DOB_MISMATCH": "SDO অফিসে জন্ম তারিখ সংশোধন করুন",
    "SUBMIT": "BDO অফিসে সম্পূর্ণ আবেদন জমা দিন",
}

# Location mapping for different issue types
LOCATION_MAP = {
    "NAME_MISMATCH": "Bank Branch",
    "DORMANT_ACCOUNT": "Bank Branch",
    "AADHAAR_UNLINKED": "Bank Branch",
    "ADDRESS_MISMATCH": "Panchayat Office",
    "DOB_MISMATCH": "SDO Office",
}

def _build_roadmap(scheme: dict, doc_issues: list, failed_rules: list) -> list:
    """
    Ordered action list the user must complete to become eligible/ready.
    Returns list with step, action, action_bn, location, done fields.
    """
    steps = []
    step_num = 1

    # Fatal rule failures first
    for rule in failed_rules:
        if rule.get("fatal"):
            steps.append({
                "step": step_num,
                "action": f"Fix eligibility issue: {rule['message']}",
                "action_bn": f"যোগ্যতার সমস্যা সমাধান করুন: {rule['message']}",
                "location": "BDO Office",
                "done": False,
            })
            step_num += 1

    # Document issues
    for issue in doc_issues:
        if issue["type"] == "missing_document":
            doc_id = issue.get("doc_id", "")
            where = issue.get("where_to_get", "")
            action = f"Get {issue['label']}"
            action_bn = ROADMAP_BN.get(f"MISSING_{doc_id.upper()}", f"{issue.get('label_bn', issue['label'])} সংগ্রহ করুন")
            
            # Extract location from where_to_get or use default
            location = where.split(" or ")[0] if where else "BDO Office"
            
            steps.append({
                "step": step_num,
                "action": action,
                "action_bn": action_bn,
                "location": location,
                "done": False,
            })
            step_num += 1

        elif issue["type"] == "name_mismatch":
            script_code = issue.get("script_code", "NAME_MISMATCH")
            steps.append({
                "step": step_num,
                "action": "Visit your bank branch to correct the name on your account",
                "action_bn": ROADMAP_BN.get(script_code, "ব্যাংক শাখায় নাম সংশোধন করুন"),
                "location": LOCATION_MAP.get(script_code, "Bank Branch"),
                "done": False,
            })
            step_num += 1

        elif issue["type"] == "address_mismatch":
            script_code = issue.get("script_code", "ADDRESS_MISMATCH")
            steps.append({
                "step": step_num,
                "action": "Visit Panchayat office to correct address mismatch",
                "action_bn": ROADMAP_BN.get(script_code, "পঞ্চায়েত অফিসে ঠিকানা সংশোধন করুন"),
                "location": LOCATION_MAP.get(script_code, "Panchayat Office"),
                "done": False,
            })
            step_num += 1

        elif issue["type"] == "bank_unlinked":
            steps.append({
                "step": step_num,
                "action": "Link Aadhaar to your bank account at the bank branch",
                "action_bn": ROADMAP_BN.get("AADHAAR_UNLINKED", "ব্যাংক শাখায় আধার লিঙ্ক করুন"),
                "location": "Bank Branch",
                "done": False,
            })
            step_num += 1

        elif issue["type"] == "dormant_account":
            steps.append({
                "step": step_num,
                "action": "Activate your dormant bank account with a small transaction",
                "action_bn": ROADMAP_BN.get("DORMANT_ACCOUNT", "ছোট লেনদেনের মাধ্যমে ঘুমন্ত ব্যাংক অ্যাকাউন্ট সক্রিয় করুন"),
                "location": "Bank Branch",
                "done": False,
            })
            step_num += 1

    # Final step: Submit application (always add if there are any steps)
    if steps:
        apply_office = scheme.get("apply_at", [{}])[0].get("office", "BDO Office")
        steps.append({
            "step": step_num,
            "action": f"Submit completed application at {apply_office}",
            "action_bn": ROADMAP_BN.get("SUBMIT", "BDO অফিসে সম্পূর্ণ আবেদন জমা দিন"),
            "location": apply_office,
            "done": False,
        })

    return steps


# ─────────────────────────────────────────────────────────────
# PUBLIC API — check_eligibility
# ─────────────────────────────────────────────────────────────

def check_eligibility(scheme_id: str, profile: dict, checks: dict = None) -> dict:
    """
    Full eligibility check for ONE scheme.

    Args:
        scheme_id: e.g. "lakshmir_bhandar"
        profile:   dict with age, gender, caste, is_govt_employee, etc.
        checks:    dict with doc names, aadhaar_linked, dormant status, docs_present/missing

    Returns:
        {
          scheme_id, scheme_name, scheme_name_bn, eligible_basic,
          score (0-100), band (RED/AMBER/GREEN), band_label, band_label_bn,
          benefit_amount,
          passed_rules, failed_rules,
          issues (with display objects), roadmap (with action_bn, location, done),
          benefit_info, score_breakdown
        }
    """
    if checks is None:
        checks = {}

    scheme = get_scheme(scheme_id)
    if not scheme:
        return {"error": f"Scheme '{scheme_id}' not found."}

    # Step 1 — Profile rules
    passed_rules, failed_rules = _check_profile_rules(scheme, profile)

    # Basic eligibility: no fatal failures
    eligible_basic = not any(
        r for r in failed_rules if r.get("fatal")
    )

    # Step 2 — Document checks (only meaningful if profile-eligible)
    doc_issues, doc_deduction = _check_documents(scheme, checks)

    # Step 3 — Score + band
    score, band = _calculate_score(failed_rules, doc_issues, doc_deduction, eligible_basic)
    band_label, band_label_bn = _get_band_labels(band)

    # Step 4 — Roadmap
    roadmap = _build_roadmap(scheme, doc_issues, failed_rules)

    # Step 5 — Benefit info (personalised by caste)
    benefit_info = _get_benefit_info(scheme, profile)
    
    # Extract single benefit_amount for frontend
    benefit_amount = (
        benefit_info.get("monthly_amount") or
        benefit_info.get("one_time_grant") or
        benefit_info.get("cashless_limit") or
        None
    )

    # Step 6 — Score breakdown for frontend
    score_breakdown = {}
    for issue in doc_issues:
        issue_code = issue.get("code", issue.get("type", "unknown"))
        score_breakdown[issue_code] = -issue.get("score_deduction", 0)

    return {
        "scheme_id":      scheme_id,
        "scheme_name":    scheme.get("scheme_name", ""),
        "scheme_name_bn": scheme.get("scheme_name_bn", ""),
        "eligible_basic": eligible_basic,
        "score":          score,
        "band":           band,
        "band_label":     band_label,
        "band_label_bn":  band_label_bn,
        "benefit_amount": benefit_amount,
        "passed_rules":   passed_rules,
        "failed_rules":   failed_rules,
        "issues":         doc_issues,  # Renamed from doc_issues for frontend
        "doc_issues":     doc_issues,  # Keep for backward compatibility with tests
        "roadmap":        roadmap,
        "benefit_info":   benefit_info,
        "score_breakdown": score_breakdown,
        "apply_at":       scheme.get("apply_at", []),
        "warnings":       [],  # Empty list for now, can be populated with non-fatal issues
    }


def _get_benefit_info(scheme: dict, profile: dict) -> dict:
    """Return personalised benefit amounts based on caste/profile."""
    b     = scheme.get("benefits", {})
    caste = str(profile.get("caste", "general")).lower()

    info = {
        "mode":    b.get("mode", ""),
        "note_en": b.get("note_en", ""),
        "note_bn": b.get("note_bn", ""),
    }

    # Monthly cash
    if caste in ("sc", "st") and b.get("sc_st_monthly"):
        info["monthly_amount"] = b["sc_st_monthly"]
        info["amount_note"]    = "SC/ST rate"
    elif b.get("general_monthly"):
        info["monthly_amount"] = b["general_monthly"]
        info["amount_note"]    = "General rate"
    elif b.get("monthly_pension"):
        info["monthly_amount"] = b["monthly_pension"]

    # One-time
    if b.get("one_time_grant"):
        info["one_time_grant"] = b["one_time_grant"]

    # Cashless limit
    if b.get("cashless_limit"):
        info["cashless_limit"] = b["cashless_limit"]

    return info


# ─────────────────────────────────────────────────────────────
# PUBLIC API — get_eligible_schemes (for /recommendations)
# ─────────────────────────────────────────────────────────────

def get_eligible_schemes(profile: dict, limit: int = 10) -> list:
    """
    Filter all schemes by profile rules.
    Returns list of {scheme_id, scheme_name, passed_rules, failed_rules}.
    Used by recommendations engine for profile-based suggestions.
    """
    results = []

    for scheme in get_all_schemes():
        _, failed = _check_profile_rules(scheme, profile)
        fatal_failures = [r for r in failed if r.get("fatal")]
        if not fatal_failures:
            results.append({
                "scheme_id":      scheme.get("scheme_id"),
                "scheme_name":    scheme.get("scheme_name"),
                "scheme_name_bn": scheme.get("scheme_name_bn", ""),
                "tag":            scheme.get("tag", ""),
                "benefit_display": scheme.get("benefit_display", ""),
                "department":     scheme.get("department", ""),
            })
        if len(results) >= limit:
            break

    return results


# ─────────────────────────────────────────────────────────────
# PUBLIC API — get_script
# ─────────────────────────────────────────────────────────────

_SCRIPTS = {
    "NAME_MISMATCH": {
        "en": "I want to correct the name spelling on my {doc_a}. "
              "The name on my Aadhaar is '{aadhaar_name}' but on my {doc_b} it shows '{bank_name}'. "
              "Please help me update this.",
        "bn": "আমি আমার {doc_a}-এ নামের বানান ঠিক করতে চাই। "
              "আমার আধার কার্ডে নাম '{aadhaar_name}' কিন্তু {doc_b}-এ '{bank_name}' লেখা আছে। "
              "অনুগ্রহ করে এটি আপডেট করতে সাহায্য করুন।",
    },
    "AADHAAR_UNLINKED": {
        "en": "I want to link my Aadhaar number to my bank account so I can receive government scheme benefits via DBT.",
        "bn": "আমি সরকারি প্রকল্পের টাকা DBT-এর মাধ্যমে পেতে আমার আধার নম্বর ব্যাংক অ্যাকাউন্টের সাথে লিংক করতে চাই।",
    },
    "DORMANT_ACCOUNT": {
        "en": "My bank account has been inactive. I want to reactivate it so I can receive government scheme benefits.",
        "bn": "আমার ব্যাংক অ্যাকাউন্ট নিষ্ক্রিয় হয়ে গেছে। সরকারি সুবিধা পেতে এটি সক্রিয় করতে চাই।",
    },
    "DOB_MISMATCH": {
        "en": "There is a date of birth discrepancy between my documents. "
              "I want to correct this so my application is not rejected.",
        "bn": "আমার কাগজপত্রে জন্ম তারিখে গরমিল আছে। আবেদন বাতিল না হওয়ার জন্য এটি ঠিক করতে চাই।",
    },
    "ADDRESS_MISMATCH": {
        "en": "The address on my Ration Card does not match my Voter ID. "
              "I want to update this to ensure my documents are consistent.",
        "bn": "আমার রেশন কার্ডের ঠিকানা ভোটার কার্ডের সাথে মিলছে না। এটি সঠিক করতে চাই।",
    },
}


def get_script(
    issue_code: str,
    lang: str = "bn",
    aadhaar_name: str = "",
    bank_name: str = "",
    **kwargs,
) -> Optional[dict]:
    """
    Get the exact script to speak at a government office for a given issue.

    Returns:
        {issue_code, script, lang} or None if not found.
    """
    template = _SCRIPTS.get(issue_code.upper())
    if not template:
        return None

    text = template.get(lang) or template.get("en", "")
    text = text.format(
        aadhaar_name=aadhaar_name or "your name",
        bank_name=bank_name or "the bank name",
        doc_a="Aadhaar",
        doc_b="Bank Passbook",
        **{k: v for k, v in kwargs.items() if isinstance(v, str)},
    )

    return {
        "issue_code": issue_code,
        "script":     text,
        "lang":       lang,
    }