"""
src/engine/eligibility.py
Deterministic eligibility check. Pure Python. Zero AI. Zero hallucination.
Scheme IDs MUST match schemes.json exactly.
"""

from dataclasses import dataclass


@dataclass
class EligibilityResult:
    eligible: bool
    scheme_id: str
    scheme_name: str
    passed_rules: list     # ["Age: 38 ✓", "Gender: Female ✓"]
    failed_rules: list     # ["Income: ₹1.8L exceeds ₹1.5L limit ✗"]
    required_documents: list


# ─────────────────────────────────────────────────────────────────────────────
# SCHEME_RULES — MUST STAY IN SYNC WITH schemes.json
# scheme_id keys must exactly match schemes.json "scheme_id" values
# ─────────────────────────────────────────────────────────────────────────────
SCHEME_RULES = {

    "lakshmir_bhandar": {
        "name": "Lakshmir Bhandar",
        "rules": [
            {"field": "gender",                           "operator": "eq",  "value": "female"},
            {"field": "age",                              "operator": "between", "value": [25, 60]},
            {"field": "is_govt_employee",                 "operator": "eq",  "value": False},
            {"field": "is_income_tax_payer",              "operator": "eq",  "value": False},
            {"field": "is_enrolled_in_other_cash_scheme", "operator": "eq",  "value": False},
            {"field": "state",                            "operator": "eq",  "value": "west_bengal"},
        ],
        "documents": ["Aadhaar", "Voter ID", "Bank Passbook", "Ration Card"],
        "benefit": "₹1,000–₹1,200/month DBT"
    },

    "swasthya_sathi": {
        "name": "Swasthya Sathi",
        "rules": [
            {"field": "state", "operator": "eq", "value": "west_bengal"},
        ],
        "documents": ["Aadhaar", "Ration Card"],
        "benefit": "₹5 lakh health cover/year"
    },

    "kanyashree": {
        "name": "Kanyashree Prakalpa",
        "rules": [
            {"field": "gender",    "operator": "eq",      "value": "female"},
            {"field": "age",       "operator": "between", "value": [13, 18]},
            {"field": "is_student","operator": "eq",      "value": True},
            {"field": "is_unmarried", "operator": "eq",   "value": True},
            {"field": "state",     "operator": "eq",      "value": "west_bengal"},
        ],
        "documents": ["Aadhaar", "School Enrollment Certificate", "Birth Certificate", "Bank Passbook"],
        "benefit": "₹1,000/year + ₹25,000 at 18"
    },

    "rupashree": {
        "name": "Rupashree Prakalpa",
        "rules": [
            {"field": "gender", "operator": "eq",      "value": "female"},
            {"field": "age",    "operator": "between", "value": [18, 40]},
            {"field": "income", "operator": "lte",     "value": 150000},
            {"field": "state",  "operator": "eq",      "value": "west_bengal"},
        ],
        "documents": ["Aadhaar", "Age Proof", "Income Certificate", "Bank Passbook"],
        "benefit": "₹25,000 one-time marriage grant"
    },

    # FIX: was "old_age_pension" — MUST be "samajik_suraksha" to match schemes.json
    "samajik_suraksha": {
        "name": "Samajik Suraksha Yojana",
        "rules": [
            {"field": "age",   "operator": "gte", "value": 60},
            {"field": "state", "operator": "eq",  "value": "west_bengal"},
        ],
        "documents": ["Aadhaar", "Age Proof", "Bank Passbook"],
        "benefit": "₹1,000/month pension"
    },

    "yuva_sathi": {
        "name": "Yuva Sathi",
        "rules": [
            {"field": "age",          "operator": "between", "value": [18, 45]},
            {"field": "is_unemployed","operator": "eq",      "value": True},
            {"field": "state",        "operator": "eq",      "value": "west_bengal"},
        ],
        "documents": ["Aadhaar", "Employment Exchange Registration Card", "Educational Certificate", "Bank Passbook"],
        "benefit": "₹1,500–₹2,000/month for max 2 years"
    }
}


def _evaluate_rule(rule: dict, user_profile: dict) -> tuple[bool, str]:
    """
    Evaluates a single rule against user profile.
    Returns (passed: bool, description: str)
    """
    field    = rule["field"]
    operator = rule["operator"]
    expected = rule["value"]
    actual   = user_profile.get(field)

    field_label = field.replace("_", " ").title()

    if actual is None:
        return False, f"{field_label}: Not provided ✗"

    if operator == "eq":
        passed = (actual == expected)
        return (True,  f"{field_label}: {actual} ✓") if passed \
          else (False, f"{field_label}: {actual} (expected {expected}) ✗")

    elif operator == "between":
        low, high = expected
        passed = (low <= actual <= high)
        return (True,  f"{field_label}: {actual} ✓") if passed \
          else (False, f"{field_label}: {actual} (must be {low}–{high}) ✗")

    elif operator == "gte":
        passed = (actual >= expected)
        return (True,  f"{field_label}: {actual} ✓") if passed \
          else (False, f"{field_label}: {actual} (must be ≥ {expected}) ✗")

    elif operator == "lte":
        passed = (actual <= expected)
        return (True,  f"{field_label}: {actual} ✓") if passed \
          else (False, f"{field_label}: {actual} (must be ≤ {expected}) ✗")

    return False, f"{field_label}: Unknown operator '{operator}' ✗"


def check_eligibility(scheme_id: str, user_profile: dict) -> EligibilityResult:
    """
    Deterministic eligibility check.
    user_profile keys:
      age (int), gender (str), caste (str), income (int),
      is_govt_employee (bool), is_income_tax_payer (bool),
      is_enrolled_in_other_cash_scheme (bool), is_student (bool),
      is_unemployed (bool), is_unmarried (bool), state (str)
    """
    if scheme_id not in SCHEME_RULES:
        return EligibilityResult(
            eligible=False,
            scheme_id=scheme_id,
            scheme_name="Unknown Scheme",
            passed_rules=[],
            failed_rules=[f"Scheme '{scheme_id}' not found ✗"],
            required_documents=[]
        )

    scheme       = SCHEME_RULES[scheme_id]
    passed_rules = []
    failed_rules = []

    for rule in scheme["rules"]:
        passed, description = _evaluate_rule(rule, user_profile)
        (passed_rules if passed else failed_rules).append(description)

    return EligibilityResult(
        eligible=len(failed_rules) == 0,
        scheme_id=scheme_id,
        scheme_name=scheme["name"],
        passed_rules=passed_rules,
        failed_rules=failed_rules,
        required_documents=scheme["documents"]
    )


def get_all_eligible_schemes(user_profile: dict) -> list[EligibilityResult]:
    """
    Runs check_eligibility for ALL scheme_ids.
    Returns only those where eligible=True.
    Used for "what schemes can I get?" query type.
    """
    return [
        result for scheme_id in SCHEME_RULES
        if (result := check_eligibility(scheme_id, user_profile)).eligible
    ]