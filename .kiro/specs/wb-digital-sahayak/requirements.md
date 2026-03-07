# Requirements: Eligibility API Response Enhancement

## Overview
Enhance the eligibility API response structure to provide all necessary fields for three frontend UI components: Score Display, Issues List, and Roadmap. The API must return comprehensive data including Bengali translations, user values for display, and actionable roadmap steps.

## User Stories

### 1. Score Display Component
**As a** frontend developer  
**I want** the eligibility API to return complete score information  
**So that** I can display the user's eligibility score with proper band labels in both English and Bengali

**Acceptance Criteria:**
- 1.1 Response includes `score` (integer 0-100)
- 1.2 Response includes `band` ("RED" | "AMBER" | "GREEN")
- 1.3 Response includes `band_label` (English label e.g., "Not Ready")
- 1.4 Response includes `band_label_bn` (Bengali label e.g., "প্রস্তুত নয়")
- 1.5 Response includes `score_breakdown` (flat dict showing per-issue deductions)
- 1.6 Response includes `benefit_amount` (integer or null)
- 1.7 Eligible users with document issues receive minimum score of 5 (for ScoreMeter animation)
- 1.8 Ineligible users (failed hard eligibility rules) receive score of 0

### 2. Issues List Component
**As a** frontend developer  
**I want** detailed issue information with actual user values  
**So that** I can display specific problems and their severity to users

**Acceptance Criteria:**
- 2.1 Response includes `issues` array (alias for `doc_issues` for backward compatibility)
- 2.2 Each issue includes `type` ("fatal" | "warning" | "ineligible")
- 2.3 Each issue includes `code` (string identifier e.g., "NAME_MISMATCH")
- 2.4 Each issue includes `message` (English description)
- 2.5 Each issue includes `score_deduction` (integer penalty)
- 2.6 Each issue includes `script_code` (string or null)
- 2.7 Each issue includes `script_available` (boolean)
- 2.8 Each issue includes `display` object with:
  - `field_a` (string field name)
  - `label_a` (string field label)
  - `value_a` (string - actual user value, not just label)
  - `field_b` (string field name)
  - `label_b` (string field label)
  - `value_b` (string - actual user value, not just label)
  - `similarity_score` (float - fuzzy matching score)
- 2.9 Issues with `script_available=True` must include non-null `script_code`

### 3. Roadmap Component
**As a** frontend developer  
**I want** actionable roadmap steps with Bengali translations  
**So that** I can guide users through the process of resolving their eligibility issues

**Acceptance Criteria:**
- 3.1 Response includes `roadmap` array generated from issues list
- 3.2 Each roadmap step includes `step` (1-based integer index)
- 3.3 Each roadmap step includes `action` (English instruction)
- 3.4 Each roadmap step includes `action_bn` (Bengali instruction)
- 3.5 Each roadmap step includes `location` (e.g., "Bank Branch", "BDO Office", "Post Office")
- 3.6 Each roadmap step includes `done` (boolean, false for incomplete steps)
- 3.7 Roadmap follows proper mapping:
  - NAME_MISMATCH → Bank Branch visit for name correction
  - DORMANT_ACCOUNT → Bank Branch visit to activate account
  - AADHAAR_UNLINKED → Bank Branch visit to link Aadhaar
  - MISSING_DOCS → Collect from appropriate office (from schemes.json)
  - Final step → Submit at BDO Office
- 3.8 All Bengali translations are accurate and complete

### 4. General API Requirements
**As a** backend developer  
**I want** to maintain backward compatibility and code quality  
**So that** existing tests continue to pass and the codebase remains maintainable

**Acceptance Criteria:**
- 4.1 Response includes `warnings` field (empty array if no warnings)
- 4.2 Response includes `scheme_name` (string)
- 4.3 Response includes `scheme_name_bn` (string)
- 4.4 Response includes `eligible_basic` (boolean)
- 4.5 All 20 existing eligibility tests continue to pass
- 4.6 Backward compatibility maintained (keep `doc_issues` alongside `issues`)
- 4.7 Only serialization layer modified (eligibility.py), no changes to engine files (scoring.py, mismatch.py)
- 4.8 Sulata test case validates all required fields

## Technical Constraints

1. **No Engine Modifications**: Do not modify `scoring.py` or `mismatch.py` - only patch the serialization layer in `eligibility.py`
2. **Backward Compatibility**: Maintain existing field names and structure where possible
3. **Test Coverage**: All existing tests must pass after changes
4. **Bengali Support**: All user-facing text must have Bengali translations
5. **Data Integrity**: Actual user values must be preserved and returned in display objects

## Test Cases

### Sulata Test Case (Primary Validation)
**Input:**
- scheme_id: "lakshmir_bhandar"
- profile: Sulata Mondal, 38, female, SC, Jalpaiguri
- checks: Name mismatch (Aadhaar: "Sulata Mondal", Bank: "Sulata"), Aadhaar unlinked, missing docs

**Expected Output:**
- score < 50
- band == "RED"
- issues array contains NAME_MISMATCH with:
  - display.value_a == "Sulata Mondal"
  - display.value_b == "Sulata"
  - display.similarity_score (float)
- roadmap array has >= 2 steps
- every roadmap step has action_bn (non-empty Bengali string)
- last roadmap step location == "BDO Office"

## Dependencies

- `backend/src/engine/eligibility.py` - Main implementation file
- `backend/src/engine/scoring.py` - Score calculation (read-only)
- `backend/src/engine/mismatch.py` - Name matching (read-only)
- `backend/src/data/schemes.json` - Scheme metadata
- `backend/src/tests/test_e2e.py` - Test suite
- `backend/test_sulata_case.py` - Validation test

## Success Metrics

1. All 20 eligibility tests passing
2. Sulata test case validates all required fields
3. Frontend components can render without missing data errors
4. Bengali translations display correctly in UI
5. Score calculation follows new rules (min 5 for eligible, 0 for ineligible)
