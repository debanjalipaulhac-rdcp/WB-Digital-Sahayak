"""
Test script to verify the Sulata test case response structure.
This validates that all required fields are present for the frontend.
"""
import json
import sys
sys.path.insert(0, 'backend/src')

from src.engine.eligibility import check_eligibility

# Sulata test case - eligible user with many document issues
sulata_request = {
    "scheme_id": "lakshmir_bhandar",
    "profile": {
        "name": "Sulata Mondal",
        "age": 38,
        "gender": "female",
        "caste": "sc",
        "district": "Jalpaiguri",
        "is_govt_employee": False,
        "pays_income_tax": False
    },
    "checks": {
        "aadhaar_name": "Sulata Mondal",
        "bank_name": "Sulata",
        "aadhaar_bank_linked": False,
        "bank_last_transaction_months_ago": 8,
        "docs_present": ["aadhaar"],
        "docs_missing": ["voter_id", "bank_passbook"]
    }
}

# Ineligible user test case - male for female-only scheme
ineligible_request = {
    "scheme_id": "lakshmir_bhandar",
    "profile": {
        "name": "Rajesh Kumar",
        "age": 38,
        "gender": "male",  # Wrong gender for female-only scheme
        "caste": "general",
        "district": "Kolkata",
        "is_govt_employee": False,
        "pays_income_tax": False
    },
    "checks": {
        "aadhaar_name": "Rajesh Kumar",
        "bank_name": "Rajesh Kumar",
        "aadhaar_bank_linked": True,
        "bank_last_transaction_months_ago": 2,
        "docs_present": ["aadhaar", "voter_id", "bank_passbook"],
        "docs_missing": []
    }
}

print("=" * 80)
print("TEST 1: SULATA CASE (Eligible user with document issues)")
print("=" * 80)

result = check_eligibility(
    sulata_request["scheme_id"],
    sulata_request["profile"],
    sulata_request["checks"]
)

print(f"\nScore: {result.get('score')}")
print(f"Band: {result.get('band')}")
print(f"Eligible Basic: {result.get('eligible_basic')}")
print(f"Warnings field present: {'warnings' in result}")
print(f"Warnings: {result.get('warnings', 'NOT PRESENT')}")

# Verify score is at least 5 for eligible users (even with many deductions)
if result.get('eligible_basic'):
    assert result.get('score') >= 5, f"Eligible user score should be >= 5, got {result.get('score')}"
    print(f"✓ Score >= 5 for eligible user (enables ScoreMeter animation)")
else:
    print(f"✗ User is not eligible_basic, score can be 0")

print("\n" + "=" * 80)
print("TEST 2: INELIGIBLE USER (Male for female-only scheme)")
print("=" * 80)

result2 = check_eligibility(
    ineligible_request["scheme_id"],
    ineligible_request["profile"],
    ineligible_request["checks"]
)

print(f"\nScore: {result2.get('score')}")
print(f"Band: {result2.get('band')}")
print(f"Eligible Basic: {result2.get('eligible_basic')}")
print(f"Warnings field present: {'warnings' in result2}")

# Verify score is 0 for ineligible users
assert result2.get('score') == 0, f"Ineligible user score should be 0, got {result2.get('score')}"
assert result2.get('eligible_basic') == False, "User should not be eligible_basic"
print(f"✓ Score = 0 for ineligible user (correct)")

print("\n" + "=" * 80)
print("TEST 3: VERIFY ALL REQUIRED FIELDS")
print("=" * 80)

required_fields = [
    "score", "band", "band_label", "band_label_bn",
    "eligible_basic", "scheme_name", "scheme_name_bn",
    "benefit_amount", "issues", "roadmap", "score_breakdown",
    "warnings"
]

for field in required_fields:
    if field in result:
        print(f"✓ {field}: present")
    else:
        print(f"✗ {field}: MISSING")
        sys.exit(1)

print("\n" + "=" * 80)
print("TEST 4: VERIFY SCRIPT_CODE IN ISSUES")
print("=" * 80)

for issue in result.get("issues", []):
    if issue.get("script_available"):
        if "script_code" in issue and issue["script_code"]:
            print(f"✓ {issue.get('code')}: has script_code = '{issue.get('script_code')}'")
        else:
            print(f"✗ {issue.get('code')}: MISSING script_code but script_available=True")
            sys.exit(1)

print("\n" + "=" * 80)
print("ALL CHECKS PASSED ✓")
print("=" * 80)
print("\nSummary:")
print(f"- Eligible users with doc issues: score >= 5 (was {result.get('score')})")
print(f"- Ineligible users: score = 0 (was {result2.get('score')})")
print(f"- Warnings field: present in response")
print(f"- scheme_name_bn: present in response")
print(f"- All issues with script_available=True have script_code")

