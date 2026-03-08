"""
src/controllers/schemes_controller.py
=======================================
HTTP layer for all scheme-related routes.

Routes:
  GET  /schemes              → list + search schemes
  GET  /schemes/{scheme_id}  → single scheme detail
  POST /eligibility          → check eligibility (calls engine)
  GET  /recommendations      → personalised scheme suggestions
  GET  /script/{issue_code}  → "what to say at office" scripts
  GET  /applications         → user's past eligibility checks (auth required)
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List

from src.services.scheme_service import SchemeService
from src.services.profile_service import ProfileService
from src.middleware.auth_middleware import get_current_user, get_optional_user
from src.repository.dynamo_repo import UserRepository

logger = logging.getLogger(__name__)
router = APIRouter(tags=["schemes"])


class ProfileInput(BaseModel):
    name:                  Optional[str]  = ""
    age:                   Optional[int]  = 0
    gender:                Optional[str]  = ""
    caste:                 Optional[str]  = ""
    district:              Optional[str]  = ""
    is_govt_employee:      Optional[bool] = False
    pays_income_tax:       Optional[bool] = False
    has_daughter:          Optional[bool] = False
    has_school_child:      Optional[bool] = False
    is_enrolled_in_school: Optional[bool] = False
    is_unemployed:         Optional[bool] = True

class DocumentChecks(BaseModel):
    aadhaar_name:                    str  = ""
    bank_name:                       str  = ""
    voter_name:                      str  = ""
    ration_name:                     str  = ""
    aadhaar_bank_linked:            bool  = True
    bank_last_transaction_months_ago: int = 0
    address_match_ok:               bool  = True
    docs_present:               List[str] = []
    docs_missing:               List[str] = []

class EligibilityRequest(BaseModel):
    scheme_id: str
    profile:   ProfileInput
    checks:    DocumentChecks = DocumentChecks()
    lang:      str = "bn"
    save:      bool = True     # if True + user is logged in, save result to history


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/schemes", summary="List and search schemes")
def list_schemes(
    q:         str = Query("",         description="Search query"),
    category:  str = Query("",         description="Filter: women|student|health|farmers|girl-child"),
    page:      int = Query(1,  ge=1,   description="Page number"),
    page_size: int = Query(8,  ge=1, le=20),
    sort:      str = Query("relevance", description="relevance|name_asc|name_desc"),
):
    """
    Returns paginated scheme list.
    No auth required — works for anonymous users.
    """
    
    return SchemeService.search_schemes(q, category, page, page_size, sort)


@router.get("/schemes/{scheme_id}", summary="Get scheme detail")
def get_scheme(scheme_id: str):
    """
    Full scheme detail including eligibility rules, documents, benefit info.
    Returns 404 if scheme not found.
    """
    scheme = SchemeService.get_scheme(scheme_id)
    if not scheme:
        raise HTTPException(status_code=404, detail=f"Scheme '{scheme_id}' not found.")
    return scheme


@router.get("/recommendations", summary="Get personalised scheme recommendations")
def recommendations(
    scheme_id: Optional[str] = Query(None, description="Current scheme (context-based)"),
    query:     Optional[str] = Query(None, description="Free-text query"),
    limit:     int           = Query(6, ge=1, le=12),
    age:       Optional[int] = Query(None, description="User age for inline profile"),
    gender:    Optional[str] = Query(None, description="User gender: male|female|other"),
    caste:     Optional[str] = Query(None, description="User caste: general|obc|sc|st"),
    has_daughter:    Optional[bool] = Query(None, description="Has daughter"),
    has_school_child: Optional[bool] = Query(None, description="Has school-going child"),
    user: dict = Depends(get_optional_user),  # works for anonymous too
):
    """
    4-mode recommendation engine:
      1. Profile-based if user is logged in and has a complete profile
      2. Profile-based if inline profile params provided (age/gender/caste)
      3. Context-based if viewing a specific scheme (pass scheme_id)
      4. Query-based if free text provided
      5. Featured fallback (curated popular schemes, shuffled)

    No auth required — anonymous users get featured/query results.
    Logged-in users get personalised results based on saved profile.
    Anonymous users can pass age/gender/caste for inline profile-based recommendations.
    """
    phone = user["sub"] if user else None
    
    # Build inline profile if any profile params provided
    inline_profile = None
    if age or gender or caste:
        inline_profile = {
            "age":             age,
            "gender":          gender or "",
            "caste":           caste or "",
            "has_daughter":    has_daughter or False,
            "has_school_child": has_school_child or False,
        }
    
    return SchemeService.get_recommendations(
        phone=phone,
        scheme_id=scheme_id,
        query=query,
        limit=limit,
        inline_profile=inline_profile,
    )


@router.post("/eligibility", summary="Check eligibility for a scheme")
def check_eligibility(
    req: EligibilityRequest,
    user: dict = Depends(get_optional_user),
):
    """
    Deterministic eligibility engine — zero AI, pure rules.
    Returns score (0-100), band (RED/AMBER/GREEN), issues, roadmap.

    If user is logged in and req.save=True, result is saved to their history.
    """
    try:
        from src.engine.eligibility import check_eligibility

        profile_dict = req.profile.model_dump()
        checks_dict  = req.checks.model_dump()

        result = check_eligibility(req.scheme_id, profile_dict, checks_dict)

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        # Save to history if logged in
        if req.save and user:
            try:
                save_data = {
                    "scheme_id":   req.scheme_id,
                    "scheme_name": result.get("scheme_name", ""),
                    "score":       result.get("score", 0),
                    "band":        result.get("band", ""),
                    "eligible":    result.get("eligible_basic", False),
                }
                UserRepository.save_result(user["sub"], save_data)
            except Exception as e:
                logger.warning(f"Failed to save result for {user['sub']}: {e}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"eligibility check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Eligibility check failed: {str(e)}")


@router.get("/script/{issue_code}", summary="Get 'what to say at office' script")
def get_script(
    issue_code:   str,
    lang:         str = Query("bn", description="Language: en|bn|hi"),
    aadhaar_name: str = Query(""),
    bank_name:    str = Query(""),
):
    """
        Returns the exact Bengali/English/Hindi script the citizen should
        speak at the government office to fix a specific issue.
        Key in response is 'script' (NOT 'bn').
    """
    try:
        from src.engine.eligibility import get_script
        script = get_script(issue_code, lang=lang, aadhaar_name=aadhaar_name, bank_name=bank_name)
        if not script:
            raise HTTPException(status_code=404, detail=f"No script for issue: {issue_code}")
        return script
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/applications", summary="Get user's past eligibility checks")
def get_applications(
    limit: int = Query(10, ge=1, le=50),
    user: dict = Depends(get_current_user),   # auth required
):
    """
    Returns the user's history of eligibility checks.
    Sorted newest first. Each item has scheme_id, score, band, checked_at.
    """
    results = SchemeService.get_applications(user["sub"], limit=limit)
    return {"applications": results, "count": len(results)}