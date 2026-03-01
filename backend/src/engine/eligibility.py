"""
src/engine/eligibility.py
==========================
Core deterministic eligibility engine.

This is the most critical file in the entire project.
- NO AI calls
- NO external API calls
- NO randomness
- Pure Python logic that reads schemes.json and returns a result

If this file is wrong, users waste trips.
Every function must be unit tested.

Main function: run_eligibility_check()
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from src.engine.mismatch import check_name_match, check_address_match, check_dob_match
from src.engine.scoring import calculate_score

logger = logging.getLogger(__name__)

# ── Load schemes.json once at module load ─────────────────────────────────────
_SCHEMES_PATH = os.path.join(os.path.dirname(__file__), "schemes.json")
_SCRIPTS_PATH = os.path.join(os.path.dirname(__file__), "scripts.json")

def _load_schemes() -> Dict[str, Any]:
    with open(_SCHEMES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {s["scheme_id"]: s for s in data["schemes"]}

def _load_scripts() -> Dict[str, Any]:
    with open(_SCRIPTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

SCHEMES = _load_schemes()
SCRIPTS = _load_scripts()


# ── Public helpers ────────────────────────────────────────────────────────────

def get_all_schemes() -> List[Dict]:
    """Return list of all schemes (for GET /schemes endpoint)."""
    return list(SCHEMES.values())


def get_scheme(scheme_id: str) -> Optional[Dict]:
    """Return single scheme by ID. Returns None if not found."""
    return SCHEMES.get(scheme_id)


def get_script(issue_code: str, lang: str = "bn",aadhaar_name: str = "", bank_name: str = "") -> Optional[Dict]:
    """
    Return the script for a given issue code, with names interpolated.
    lang: "bn" | "en" | "hi"
    """
    entry = SCRIPTS.get(issue_code)
    if not entry:
        return None

    script_text = entry.get(lang, entry.get("en", ""))
    script_text = script_text.replace("{aadhaar_name}", aadhaar_name)
    script_text = script_text.replace("{bank_name}", bank_name)

    return {
        "issue_code": issue_code,
        "where": entry["where"],
        "form": entry["form"],
        "script": script_text,
        "audio_url": entry.get("audio_url")
    }


# ── Core Engine ───────────────────────────────────────────────────────────────

def run_eligibility_check(
    scheme_id: str,
    profile: Dict[str, Any],
    checks: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Run full eligibility check for a scheme.

    Args:
        scheme_id: e.g. "lakshmir_bhandar"
        profile: {
            name, age, gender, caste, district,
            is_govt_employee, pays_income_tax,
            has_daughter, has_school_child
        }
        checks: {
            aadhaar_name, bank_name, voter_name,
            aadhaar_bank_linked, bank_last_transaction_months_ago,
            address_match_ok, docs_present, docs_missing
        }

    Returns:
        Full result dict with score, issues, roadmap, recommendations.
    """
    scheme = SCHEMES.get(scheme_id)
    if not scheme:
        return {"error": f"Scheme '{scheme_id}' not found.", "score": 0}

    issues: List[Dict] = []
    warnings: List[Dict] = []

    # ── Step 1: Basic eligibility checks ──────────────────────────────────────
    _check_basic_eligibility(scheme, profile, issues)

    # If basic eligibility fails — stop here, score is 0
    if any(i["type"] == "ineligible" for i in issues):
        score_result = calculate_score(issues)
        return _build_response(scheme, profile, issues, warnings, [], score_result)

    # ── Step 2: Document mismatch checks ──────────────────────────────────────
    _check_mismatches(scheme, checks, issues, warnings)

    # ── Step 3: Bank account conditions ───────────────────────────────────────
    _check_bank_conditions(scheme, checks, issues)

    # ── Step 4: Missing required documents ────────────────────────────────────
    _check_missing_docs(scheme, checks, issues)

    # ── Step 5: Calculate score ────────────────────────────────────────────────
    all_issues_for_scoring = issues + warnings
    score_result = calculate_score(all_issues_for_scoring)

    # ── Step 6: Build roadmap ─────────────────────────────────────────────────
    roadmap = _build_roadmap(issues, warnings, score_result["score"])

    # ── Step 7: Cross-scheme recommendations ──────────────────────────────────
    recommendations = _get_recommendations(scheme, profile)

    return _build_response(scheme, profile, issues, warnings, roadmap, score_result, recommendations)


# ── Step implementations ──────────────────────────────────────────────────────

def _check_basic_eligibility(scheme: Dict, profile: Dict, issues: List) -> None:
    """Check age, gender, employment status, tax status."""
    el = scheme["eligibility"]

    # Gender check
    if el.get("gender") and profile.get("gender") != el["gender"]:
        issues.append({
            "type": "ineligible",
            "code": "WRONG_GENDER",
            "message": f"This scheme is for {el['gender']} applicants only.",
            "score_deduction": 100
        })

    # Age check
    age = profile.get("age", 0)
    if el.get("age_min") and age < el["age_min"]:
        issues.append({
            "type": "ineligible",
            "code": "AGE_TOO_YOUNG",
            "message": f"Minimum age is {el['age_min']}. Your age: {age}.",
            "score_deduction": 100
        })
    if el.get("age_max") and age > el["age_max"]:
        issues.append({
            "type": "ineligible",
            "code": "AGE_TOO_OLD",
            "message": f"Maximum age is {el['age_max']}. Your age: {age}.",
            "score_deduction": 100
        })

    # Government employee check
    if el.get("not_govt_employee") and profile.get("is_govt_employee"):
        issues.append({
            "type": "ineligible",
            "code": "GOVT_EMPLOYEE",
            "message": "Government employees are not eligible for this scheme.",
            "score_deduction": 100
        })

    # Income tax payer check
    if el.get("not_income_tax_payer") and profile.get("pays_income_tax"):
        issues.append({
            "type": "ineligible",
            "code": "INCOME_TAX_PAYER",
            "message": "Income tax payers are not eligible for this scheme.",
            "score_deduction": 100
        })

    # School enrollment check (Kanyashree)
    if el.get("must_be_enrolled_in_school") and not profile.get("is_enrolled_in_school"):
        issues.append({
            "type": "ineligible",
            "code": "NOT_ENROLLED_IN_SCHOOL",
            "message": "Applicant must be currently enrolled in school.",
            "score_deduction": 100
        })

    # Unemployment check (Yuva Sathi)
    if el.get("must_be_unemployed") and not profile.get("is_unemployed", True):
        issues.append({
            "type": "ineligible",
            "code": "NOT_UNEMPLOYED",
            "message": "This scheme is for unemployed applicants only.",
            "score_deduction": 100
        })


def _check_mismatches(scheme: Dict, checks: Dict, issues: List, warnings: List) -> None:
    """Run all mismatch checks defined in the scheme's mismatch_checks array."""

    aadhaar_name = checks.get("aadhaar_name", "")
    bank_name    = checks.get("bank_name", "")
    voter_name   = checks.get("voter_name", "")

    for mc in scheme.get("mismatch_checks", []):
        field    = mc["field"]
        doc_a    = mc["doc_a"]
        doc_b    = mc["doc_b"]
        severity = mc["severity"]   # "FATAL" or "WARNING"

        # Only run the check if we have both values
        val_a, val_b = _get_field_values(field, doc_a, doc_b, checks)
        if not val_a or not val_b:
            logger.debug(f"Skipping mismatch check {mc['check_id']} — missing input values")
            continue

        if field == "name":
            result = check_name_match(val_a, val_b, mc["label_a"], mc["label_b"])
        elif field == "address":
            result = check_address_match(val_a, val_b, mc["label_a"], mc["label_b"])
        elif field == "date_of_birth":
            result = check_dob_match(val_a, val_b, mc["label_a"], mc["label_b"])
        else:
            continue

        if result["is_mismatch"]:
            issue = {
                "type": "fatal" if severity == "FATAL" else "warning",
                "code": mc["script_code"],
                "check_id": mc["check_id"],
                "message": mc["message"],
                "display": {
                    "field_a": val_a, "label_a": mc["label_a"],
                    "field_b": val_b, "label_b": mc["label_b"],
                    "similarity_score": result["score"]
                },
                "score_deduction": mc["score_deduction"],
                "script_code": mc["script_code"],
                "script_available": True
            }
            if severity == "FATAL":
                issues.append(issue)
            else:
                warnings.append(issue)


def _get_field_values(field: str, doc_a: str, doc_b: str, checks: Dict):
    """Map (field, doc) pairs to the actual values from checks dict."""
    mapping = {
        ("name", "aadhaar"):           checks.get("aadhaar_name", ""),
        ("name", "bank_passbook"):     checks.get("bank_name", ""),
        ("name", "voter_id"):          checks.get("voter_name", ""),
        ("name", "ration_card"):       checks.get("ration_name", ""),
        ("name", "birth_certificate"): checks.get("birth_cert_name", ""),
        ("address", "aadhaar"):        checks.get("aadhaar_address", ""),
        ("address", "voter_id"):       checks.get("voter_address", ""),
        ("address", "ration_card"):    checks.get("ration_address", ""),
        ("date_of_birth", "aadhaar"):          checks.get("aadhaar_dob", ""),
        ("date_of_birth", "birth_certificate"):checks.get("birth_cert_dob", ""),
    }
    return mapping.get((field, doc_a), ""), mapping.get((field, doc_b), "")


def _check_bank_conditions(scheme: Dict, checks: Dict, issues: List) -> None:
    """Check bank account active status and Aadhaar linkage."""
    bc = scheme.get("bank_conditions", {})

    if not bc.get("account_required"):
        return

    # Dormant account check
    if bc.get("dormant_check"):
        months_ago = checks.get("bank_last_transaction_months_ago", 0)
        threshold  = bc.get("dormant_threshold_months", 6)
        if months_ago > threshold:
            issues.append({
                "type": "fatal",
                "code": "DORMANT_ACCOUNT",
                "message": (
                    f"Bank account has been inactive for {months_ago} months. "
                    f"Benefits will bounce. Reactivate before applying."
                ),
                "action": "Visit bank branch and make any transaction to reactivate.",
                "score_deduction": bc["score_deduction_dormant"],
                "script_code": bc["script_code_dormant"],
                "script_available": True
            })

    # Aadhaar-bank linkage check
    if bc.get("aadhaar_linked_required"):
        if not checks.get("aadhaar_bank_linked", True):
            issues.append({
                "type": "fatal",
                "code": "AADHAAR_UNLINKED",
                "message": "Aadhaar is not linked to your bank account. DBT will fail.",
                "action": "Visit bank with Aadhaar card and request Aadhaar seeding.",
                "score_deduction": bc["score_deduction_unlinked"],
                "script_code": bc["script_code_unlinked"],
                "script_available": True
            })


def _check_missing_docs(scheme: Dict, checks: Dict, issues: List) -> None:
    """Check for missing required documents."""
    docs_present = set(checks.get("docs_present", []))

    for doc in scheme.get("documents", []):
        if doc["required"] and doc["doc_id"] not in docs_present:
            issues.append({
                "type": "missing_doc",
                "code": f"MISSING_{doc['doc_id'].upper()}",
                "message": f"Missing required document: {doc['label']}",
                "action": f"Obtain {doc['label']} before applying.",
                "score_deduction": doc["score_deduction_if_missing"],
                "script_code": "MISSING_BANK_ACCOUNT" if doc["doc_id"] == "bank_passbook" else None,
                "script_available": doc["doc_id"] == "bank_passbook"
            })


def _build_roadmap(issues: List, warnings: List, score: int) -> List[Dict]:
    """Build ordered action steps from issues."""
    roadmap = []
    step = 1
    seen_scripts = set()

    all_issues = issues + warnings
    fatal_codes = {i["code"] for i in all_issues if i.get("type") == "fatal"}

    if "NAME_MISMATCH" in fatal_codes:
        roadmap.append({
            "step": step, "urgent": True,
            "where": "Bank Branch or Post Office / Aadhaar Centre",
            "what": "Fix name mismatch between your documents",
            "what_bn": "আপনার নথিতে নামের গরমিল ঠিক করুন"
        })
        step += 1

    if "DORMANT_ACCOUNT" in fatal_codes:
        roadmap.append({
            "step": step, "urgent": True,
            "where": "Your Bank Branch",
            "what": "Reactivate dormant bank account (make any transaction)",
            "what_bn": "Dormant bank account reactivate করুন"
        })
        step += 1

    if "AADHAAR_UNLINKED" in fatal_codes:
        roadmap.append({
            "step": step, "urgent": True,
            "where": "Bank Branch (bring Aadhaar card)",
            "what": "Link Aadhaar to bank account (Aadhaar seeding)",
            "what_bn": "Bank account-এ Aadhaar link করুন"
        })
        step += 1

    missing_doc_issues = [i for i in all_issues if i.get("type") == "missing_doc"]
    if missing_doc_issues:
        missing_labels = [i["message"].replace("Missing required document: ", "") for i in missing_doc_issues]
        roadmap.append({
            "step": step, "urgent": True,
            "where": "Gram Panchayat / Bank / District Office",
            "what": f"Collect missing documents: {', '.join(missing_labels)}",
            "what_bn": "প্রয়োজনীয় নথি সংগ্রহ করুন"
        })
        step += 1

    if "ADDRESS_MISMATCH" in {i["code"] for i in warnings}:
        roadmap.append({
            "step": step, "urgent": False,
            "where": "Gram Panchayat / Ward Office",
            "what": "Fix address mismatch across documents",
            "what_bn": "নথিতে ঠিকানার গরমিল ঠিক করুন"
        })
        step += 1

    # Final step — only show if score is high enough
    if score >= 50 or not roadmap:
        roadmap.append({
            "step": step, "urgent": False,
            "where": "BDO Office / Duare Sarkar Camp",
            "what": "Submit application" if score >= 80 else "Submit application (after fixing above issues)",
            "what_bn": "আবেদন জমা দিন"
        })

    return roadmap


def _get_recommendations(scheme: Dict, profile: Dict) -> List[Dict]:
    """Apply cross-scheme trigger rules."""
    recommendations = []

    for trigger in scheme.get("cross_scheme_triggers", []):
        condition = trigger["condition"]
        matched = False

        if condition == "always":
            matched = True
        elif condition == "has_daughter":
            matched = profile.get("has_daughter", False)
        elif condition == "has_school_child":
            matched = profile.get("has_school_child", False)

        if matched:
            rec_scheme = SCHEMES.get(trigger["suggest_scheme_id"])
            if rec_scheme:
                recommendations.append({
                    "scheme_id": trigger["suggest_scheme_id"],
                    "scheme_name": rec_scheme["scheme_name"],
                    "scheme_name_bn": rec_scheme["scheme_name_bn"],
                    "benefit_display": rec_scheme["benefit_display"],
                    "reason": trigger["reason"],
                    "matched_by": "rule"
                })

    return recommendations


def _build_response(
    scheme: Dict,
    profile: Dict,
    issues: List,
    warnings: List,
    roadmap: List,
    score_result: Dict,
    recommendations: List = None
) -> Dict:
    """Assemble the final response dict."""
    is_ineligible = any(i["type"] == "ineligible" for i in issues)
    fatal_issues  = [i for i in issues if i["type"] == "fatal"]

    # Determine benefit amount based on caste
    benefit_amount = None
    benefits = scheme.get("benefits", {})
    if "general_monthly" in benefits:
        caste = profile.get("caste", "general").lower()
        if caste in ("sc", "st") and not any(
            i["code"] == f"MISSING_CASTE_CERTIFICATE" for i in issues
        ):
            benefit_amount = benefits.get("sc_st_monthly", benefits["general_monthly"])
        else:
            benefit_amount = benefits["general_monthly"]

    return {
        "scheme_id": scheme["scheme_id"],
        "scheme_name": scheme["scheme_name"],
        "scheme_name_bn": scheme["scheme_name_bn"],
        "score": score_result["score"],
        "band": score_result["band"],
        "band_label": score_result["band_label"],
        "band_label_bn": score_result["band_label_bn"],
        "eligible_basic": not is_ineligible,
        "benefit_amount": benefit_amount,
        "issues": issues,
        "warnings": warnings,
        "roadmap": roadmap,
        "recommendations": recommendations or [],
        "score_breakdown": score_result["breakdown"],
        "ai_explanation": ""   # filled by bedrock.py at API layer
    }