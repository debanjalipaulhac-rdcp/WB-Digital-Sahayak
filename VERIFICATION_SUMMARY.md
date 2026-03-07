# Eligibility API Response Verification Summary

## Task Completed
Verified and patched the eligibility API response to include all fields required by the frontend UI components.

## Changes Made

### 1. Added Top-Level Fields
- `band_label` - English label for the band (e.g., "Ready to Apply", "Almost Ready", "Not Ready")
- `band_label_bn` - Bengali label for the band (e.g., "আবেদনের জন্য প্রস্তুত", "প্রায় প্রস্তুত", "প্রস্তুত নয়")
- `benefit_amount` - Single integer field extracted from benefit_info (monthly_amount, one_time_grant, or cashless_limit)
- `score_breakdown` - Dictionary mapping issue codes to their score deductions (e.g., {"NAME_MISMATCH": -35})
- `issues` - Renamed from `doc_issues` (kept both for backward compatibility)

### 2. Enhanced Issues Array
Each issue now includes:
- `code` - Issue code (e.g., "NAME_MISMATCH", "DORMANT_ACCOUNT")
- `message` - English description
- `score_deduction` - Points deducted (renamed from `deduction`)
- `script_available` - Boolean indicating if a script is available
- `display` - Object containing:
  - `field_a` - First field name (e.g., "aadhaar_name")
  - `label_a` - First field label (e.g., "Aadhaar")
  - `value_a` - **Actual value** from user input (e.g., "Sulata Mondal")
  - `field_b` - Second field name (e.g., "bank_name")
  - `label_b` - Second field label (e.g., "Bank Account Name")
  - `value_b` - **Actual value** from user input (e.g., "Sulata")
  - `similarity_score` - Float similarity score (e.g., 63.15)

### 3. Enhanced Roadmap Array
Each roadmap step now includes:
- `step` - 1-based index (renamed from `priority`)
- `action` - English instruction
- `action_bn` - **Bengali translation** (e.g., "আপনার ব্যাংক শাখায় গিয়ে নাম সংশোধনের আবেদন করুন")
- `location` - Where to go (e.g., "Bank Branch", "BDO Office")
- `done` - Boolean (always false for new checks)

### 4. Added Bengali Translation Dictionary
```python
ROADMAP_BN = {
    "NAME_MISMATCH": "আপনার ব্যাংক শাখায় গিয়ে নাম সংশোধনের আবেদন করুন",
    "DORMANT_ACCOUNT": "ছোট লেনদেনের মাধ্যমে অ্যাকাউন্ট সক্রিয় করুন",
    "AADHAAR_UNLINKED": "ব্যাংক শাখায় আধার সংযোগ করুন",
    "MISSING_VOTER_ID": "নির্বাচন অফিস থেকে ভোটার আইডি সংগ্রহ করুন",
    "MISSING_BANK_PASSBOOK": "ব্যাংক শাখা থেকে পাসবুক নিন",
    "SUBMIT": "BDO অফিসে সম্পূর্ণ আবেদন জমা দিন",
}
```

## Files Modified
1. `backend/src/engine/eligibility.py` - Main eligibility engine
   - Added `_get_band_labels()` function
   - Enhanced `_check_documents()` to include display objects with actual values
   - Updated `_build_roadmap()` with Bengali translations and location mapping
   - Modified `check_eligibility()` to return all required fields
   
2. `backend/src/tests/test_e2e.py` - Updated test expectations
   - Changed roadmap test to check for `step` instead of `priority`
   - Added checks for new fields: `action_bn`, `location`, `done`

## Test Results

### Sulata Test Case (Verified ✓)
```json
{
  "score": 0,
  "band": "RED",
  "band_label": "Not Ready",
  "band_label_bn": "প্রস্তুত নয়",
  "benefit_amount": 1200,
  "issues": [
    {
      "type": "name_mismatch",
      "code": "NAME_MISMATCH",
      "message": "Name on Aadhaar must exactly match Bank Passbook...",
      "score_deduction": 35,
      "script_available": true,
      "display": {
        "field_a": "aadhaar_name",
        "label_a": "Aadhaar",
        "value_a": "Sulata Mondal",
        "field_b": "bank_passbook_name",
        "label_b": "Bank Passbook",
        "value_b": "Sulata",
        "similarity_score": 63.15
      }
    }
  ],
  "roadmap": [
    {
      "step": 1,
      "action": "Get Voter ID (EPIC)",
      "action_bn": "নির্বাচন অফিস থেকে ভোটার আইডি সংগ্রহ করুন",
      "location": "BLO",
      "done": false
    },
    {
      "step": 6,
      "action": "Submit completed application at BDO Office",
      "action_bn": "BDO অফিসে সম্পূর্ণ আবেদন জমা দিন",
      "location": "BDO Office",
      "done": false
    }
  ],
  "score_breakdown": {
    "MISSING_VOTER_ID": -15,
    "MISSING_BANK_PASSBOOK": -20,
    "NAME_MISMATCH": -35,
    "AADHAAR_UNLINKED": -25,
    "DORMANT_ACCOUNT": -25
  }
}
```

### All Eligibility Tests Pass ✓
- 20/20 eligibility tests passing
- All existing functionality preserved
- Backward compatibility maintained (kept `doc_issues` alongside `issues`)

## Verification Checklist

✓ score < 50  
✓ band == "RED"  
✓ band_label present  
✓ band_label_bn present  
✓ benefit_amount present  
✓ issues array contains NAME_MISMATCH  
✓ NAME_MISMATCH has display.value_a == "Sulata Mondal"  
✓ NAME_MISMATCH has display.value_b == "Sulata"  
✓ NAME_MISMATCH has display.similarity_score (float)  
✓ roadmap has >= 2 steps  
✓ every roadmap step has action_bn (non-empty Bengali string)  
✓ last roadmap step location == "BDO Office"  
✓ score_breakdown present with per-issue deductions  

## No Engine Files Touched
As requested, no changes were made to:
- `backend/src/engine/scoring.py`
- `backend/src/engine/mismatch.py`

All changes were made only to the serialization layer in `eligibility.py`.

## Next Steps
The API response now includes all fields required by the frontend for:
1. Score Display Component - score, band, band_label, band_label_bn
2. Issues List Component - issues array with display objects containing actual values
3. Roadmap Component - roadmap array with Bengali translations and locations
