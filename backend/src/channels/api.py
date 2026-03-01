"""
REST API Route Handlers
========================
All HTTP routes for the WB Digital Sahayak API.

Routes:
    POST /api/v1/check-eligibility   ← Core: run eligibility check + score
    GET  /api/v1/schemes             ← List all schemes
    GET  /api/v1/scheme/{scheme_id}  ← Single scheme detail
    POST /api/v1/profile             ← Save user profile
    GET  /api/v1/profile/{phone}     ← Fetch user profile
    GET  /api/v1/script/{code}       ← Script Generator
    GET  /api/v1/recommendations     ← Vector + rule-based suggestions

Status: STUBS — implement as engine modules are built (Level 1 → 2)
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from src.engine.eligibility import (
    run_eligibility_check,
    get_all_schemes,
    get_scheme,
    get_script,
)
from src.storage.dynamo import (
    save_profile, get_profile, profile_exists,
    save_result, get_latest_result,
)
from src.config.bedrock_client import generate_explanation


router = APIRouter()

# ── Pydantic Models ───────────────────────────────────────────────────────────

class ProfileModel(BaseModel):
    name: str
    age: int
    gender: str
    caste: str
    district: str
    is_govt_employee: bool = False
    pays_income_tax: bool = False
    has_daughter: bool = False
    has_school_child: bool = False
    is_enrolled_in_school: bool = False
    is_unemployed: bool = True
    phone: Optional[str] = None

class DocumentChecks(BaseModel):
    aadhaar_name: str
    bank_name: str = ""
    voter_name: str = ""
    ration_name: str = ""
    birth_cert_name: str = ""
    aadhaar_dob: str = ""
    birth_cert_dob: str = ""
    aadhaar_address: str = ""
    voter_address: str = ""
    ration_address: str = ""
    aadhaar_bank_linked: bool = True
    bank_last_transaction_months_ago: int = 0
    address_match_ok: bool = True
    docs_present: List[str] = []
    docs_missing: List[str] = []

class EligibilityRequest(BaseModel):
    scheme_id: str
    profile: Optional[ProfileModel]
    checks: Optional[DocumentChecks]
    lang: str = "bn"         
    save: bool = True       
# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/schemes")
def list_schemes():
    """List all available welfare schemes."""
    schemes = get_all_schemes()
    return {
        "count": len(schemes),
        "schemes": [
            {
                "scheme_id":       s["scheme_id"],
                "scheme_name":     s["scheme_name"],
                "scheme_name_bn":  s["scheme_name_bn"],
                "benefit_display": s["benefit_display"],
                "tag":             s["tag"],
            }
            for s in schemes
        ]
    }

@router.get("/scheme/{scheme_id}")
def get_scheme_detail(scheme_id: str):
    """Get full details for a single scheme."""
    scheme = get_scheme(scheme_id)
    if not scheme:
        raise HTTPException(status_code=404, detail=f"Scheme '{scheme_id}' not found")
    return scheme

@router.post("/check-eligibility")
def check_eligibility(req: EligibilityRequest):
    """
    Core endpoint. Run eligibility check + score + mismatch detection.
    Optionally saves result to DynamoDB and generates AI explanation.

    Integration test (Level 1.3 checkpoint):
        POST body with Sulata's data →
        Expected: score < 50, band=RED,
                  issues contain NAME_MISMATCH + DORMANT_ACCOUNT
    """
    profile_dict = req.profile.model_dump()
    checks_dict=None
    if req.checks:
        checks_dict  = req.checks.model_dump()

    # Run the deterministic engine
    result = run_eligibility_check(req.scheme_id, profile_dict, checks_dict)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    # Generate AI explanation (non-blocking — falls back to template if Bedrock fails)
    result["ai_explanation"] = generate_explanation(
        score        = result["score"],
        band         = result["band"],
        issues       = result.get("issues", []),
        scheme_name  = result.get("scheme_name", req.scheme_id),
        profile_name = req.profile.name.split()[0],   # first name only
        lang         = req.lang,
    )

    # Save result to DynamoDB if phone provided and save=True
    if req.save and req.profile.phone:
        save_result(req.profile.phone, req.scheme_id, result)

    return result

@router.post("/profile")
def create_profile(profile: ProfileModel):
    """Save or update a user profile."""
    if not profile.phone:
        raise HTTPException(status_code=400, detail="phone is required to save a profile")

    data = profile.model_dump()
    data.pop("phone")   # phone is the PK, not stored in the item body

    success = save_profile(profile.phone, data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save profile")

    return {"status": "saved", "phone": profile.phone}



@router.get("/profile/{phone}")
def fetch_profile(phone: str):
    """Fetch a user profile by phone number."""
    profile = get_profile(phone)
    if not profile:
        raise HTTPException(status_code=404, detail=f"No profile found for {phone}")
    return profile


@router.get("/profile/{phone}/result")
def fetch_latest_result(phone: str, scheme_id: Optional[str] = Query(default=None)):
    """Fetch the most recent eligibility result for a user."""
    result = get_latest_result(phone, scheme_id)
    if not result:
        raise HTTPException(status_code=404, detail="No results found")
    return result


@router.get("/script/{issue_code}")
def fetch_script(
    issue_code: str,
    lang: str = Query(default="bn"),
    aadhaar_name: str = Query(default=""),
    bank_name: str = Query(default=""),
):
    """
    Get the exact words to say at the office for a given issue.
    Example: GET /api/v1/script/NAME_MISMATCH?lang=bn&aadhaar_name=Sulata+Mondal&bank_name=Sulata
    """
    script = get_script(issue_code, lang=lang, aadhaar_name=aadhaar_name, bank_name=bank_name)
    if not script:
        raise HTTPException(status_code=404, detail=f"No script for issue code: {issue_code}")
    return script


@router.get("/recommendations")
def get_recommendations(
    query: Optional[str] = Query(default=None),
    profile_id: Optional[str] = Query(default=None),
):
    """
    Rule + vector-based scheme recommendations.
    Vector search (Pinecone) — implemented in Level 2.
    """
    if query:
        try:
            from src.config.pinecone_client import search_schemes
            results = search_schemes(query)
            return {"source": "vector", "results": results}
        except Exception as e:
            logger.warning(f"Vector search failed: {e} — returning empty")

    return {"source": "none", "results": [], "note": "Vector search available at Level 2"}