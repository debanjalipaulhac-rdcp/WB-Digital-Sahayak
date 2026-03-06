"""
src/channels/api.py — FastAPI REST routes
ROUTES: /health /schemes /scheme/{id} /check-eligibility /profile /script/{code}
        /recommendations (3-mode: profile+context+query) /voice/transcribe /voice/cache-status
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List

from src.engine.eligibility import check_eligibility, get_all_eligible_schemes
from src.engine.scoring     import calculate_score
from src.engine.mismatch    import check_name_mismatch, generate_mismatch_script
from src.static.scheme_lookup import lookup as static_lookup
from src.dynamic.keyword_extractor import extract_keywords
from src.dynamic.vector_search     import search as vector_search
from src.dynamic.nova_responder    import generate_response

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Models ─────────────────────────────────────────────────────────────────────

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
    aadhaar_name: str = ""
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
    profile: ProfileModel
    checks: DocumentChecks = DocumentChecks()
    lang: str = "bn"
    save: bool = True

class TranscribeRequest(BaseModel):
    audio_url: str
    lang: str = "bn"

class EligibilityRequest(BaseModel):
    scheme_id:  str
    profile:    dict
    documents:  Optional[dict] = {}
    aadhaar_name: Optional[str] = ""
    bank_name:    Optional[str] = ""

class QueryRequest(BaseModel):
    query:         str
    language_code: Optional[str] = "en-IN"

class MismatchRequest(BaseModel):
    aadhaar_name: str
    bank_name:    str
    language:     Optional[str] = "en-IN"


# ── Routes ─────────────────────────────────────────────────────────────────────
@router.get("/health")
def health():
    return {"status": "ok", "service": "WB Digital Sahayak"}


@router.get("/schemes")
def list_schemes():
    """List all scheme IDs and names."""
    from src.storage.dynamo import get_all_schemes
    schemes = get_all_schemes()
    return {
        "schemes": [
            {
                "scheme_id":   s.get("scheme_id"),
                "scheme_name": s.get("scheme_name"),
                "tag":         s.get("tag"),
                "benefit":     s.get("benefit_display")
            }
            for s in schemes
        ]
    }


# @router.get("/scheme/{scheme_id}")
# def get_scheme_detail(scheme_id: str):
#     scheme = get_scheme(scheme_id)
#     if not scheme:
#         raise HTTPException(status_code=404, detail=f"Scheme '{scheme_id}' not found")
#     return scheme


@router.post("/check-eligibility")
def check_eligibility_endpoint(req: EligibilityRequest):
    """Full eligibility check with score and mismatch."""
    result = check_eligibility(req.scheme_id, req.profile)

    mismatch_status = "match"
    mismatch_detail = None
    if req.aadhaar_name and req.bank_name:
        mm = check_name_mismatch(req.aadhaar_name, req.bank_name)
        mismatch_status = mm.status
        mismatch_detail = {
            "status": mm.status,
            "score": mm.score,
            "suggestion": mm.suggestion
        }

    score_res = calculate_score(
        {
            "passed_rules": result.passed_rules,
            "failed_rules": result.failed_rules,
            "required_documents": result.required_documents
        },
        req.documents or {},
        mismatch_status=mismatch_status
    )

    return {
        "scheme_id":    result.scheme_id,
        "scheme_name":  result.scheme_name,
        "eligible":     result.eligible,
        "score":        score_res.total,
        "label":        score_res.readiness_label,
        "passed_rules": result.passed_rules,
        "failed_rules": result.failed_rules,
        "missing_docs": score_res.missing_documents,
        "mismatch":     mismatch_detail,
        "breakdown":    score_res.breakdown
    }

@router.post("/all-eligible-schemes")
def all_eligible_schemes(profile: dict):
    """Return all schemes a given profile is eligible for."""
    results = get_all_eligible_schemes(profile)
    return {
        "eligible_schemes": [
            {
                "scheme_id":   r.scheme_id,
                "scheme_name": r.scheme_name,
                "documents":   r.required_documents
            }
            for r in results
        ]
    }

@router.post("/query")
def query_endpoint(req: QueryRequest):
    """
    Dynamic query: keyword extract → vector search → Nova Lite.
    For testing the dynamic path end-to-end.
    """
    # Try static lookup first
    static = static_lookup(req.query, req.language_code)
    if static:
        return {
            "source":   "static",
            "answer":   static.answer_text,
            "audio_url": static.audio_url,
            "scheme_id": static.scheme_id
        }

    # Dynamic path
    keywords      = extract_keywords(req.query)
    search_result = vector_search(keywords)
    response      = generate_response(req.query, search_result)

    return {
        "source":      "dynamic",
        "keywords":    keywords,
        "top_scheme":  search_result.results[0].scheme_id if search_result.results else None,
        "top_score":   search_result.top_score,
        "confident":   search_result.is_confident,
        "answer":      response
    }

@router.post("/check-mismatch")
def check_mismatch_endpoint(req: MismatchRequest):
    """Name mismatch check between Aadhaar and bank name."""
    result = check_name_mismatch(req.aadhaar_name, req.bank_name)
    script = generate_mismatch_script(result, req.language)
    return {
        "status":      result.status,
        "score":       result.score,
        "suggestion":  result.suggestion,
        "bank_script": script
    }



# @router.post("/profile")
# def create_profile(profile: ProfileModel):
#     if not profile.phone:
#         raise HTTPException(status_code=400, detail="phone is required")
#     data = profile.model_dump() if hasattr(profile, "model_dump") else dict(profile.__dict__)
#     data.pop("phone", None)
#     if not save_profile(profile.phone, data):
#         raise HTTPException(status_code=500, detail="Failed to save profile")
#     return {"status": "saved", "phone": profile.phone}


# @router.get("/profile/{phone}")
# def fetch_profile(phone: str):
#     profile = get_profile(phone)
#     if not profile:
#         raise HTTPException(status_code=404, detail=f"No profile for {phone}")
#     return profile


# @router.get("/profile/{phone}/result")
# def fetch_latest_result(phone: str, scheme_id: Optional[str] = Query(default=None)):
#     result = get_latest_result(phone, scheme_id)
#     if not result:
#         raise HTTPException(status_code=404, detail="No results found")
#     return result


# @router.get("/script/{issue_code}")
# def fetch_script(
#     issue_code: str,
#     lang: str = Query(default="bn"),
#     aadhaar_name: str = Query(default=""),
#     bank_name: str = Query(default=""),
# ):
#     """Exact words to say at the office + fix_at location + form needed."""
#     script = get_script(issue_code, lang=lang, aadhaar_name=aadhaar_name, bank_name=bank_name)
#     if not script:
#         raise HTTPException(status_code=404, detail=f"No script for: {issue_code}")
#     return script


# @router.get("/recommendations")
# def get_recommendations_route(
#     query:      Optional[str] = Query(default=None),
#     profile_id: Optional[str] = Query(default=None),
#     scheme_id:  Optional[str] = Query(default=None),
#     top_k:      int           = Query(default=3),
# ):
#     """
#     3-mode recommendation engine:
#       - profile_id → fetch profile → profile_based (which schemes can this user apply for)
#       - scheme_id  → context_based (user viewing X, suggest Y,Z)
#       - query      → query_based (vector search: "hospital free treatment")
#     All modes combine. Deduplicated. First match wins.
#     """
#     from src.ai.recommendations import get_recommendations

#     profile = None
#     if profile_id:
#         try:
#             profile = get_profile(profile_id)
#         except Exception as e:
#             logger.warning(f"get_profile({profile_id}) failed: {e}")

#     try:
#         results = get_recommendations(
#             profile=profile, current_scheme_id=scheme_id,
#             query=query, top_k=top_k,
#         )
#         return {
#             "count": len(results), "results": results,
#             "modes_used": {
#                 "profile_based": profile is not None,
#                 "context_based": scheme_id is not None,
#                 "query_based":   query is not None,
#             }
#         }
#     except Exception as e:
#         logger.error(f"recommendations failed: {e}")
#         return {"count": 0, "results": [], "error": str(e)}


# @router.post("/voice/transcribe")
# def transcribe_audio(req: TranscribeRequest):
#     """Transcribe audio URL → text via Sarvam AI STT. For testing voice pipeline."""
#     try:
#         from src.voice.sarvam_stt import transcribe_from_url
#         result = transcribe_from_url(req.audio_url)
#         if not result.get("success"):
#             raise HTTPException(status_code=422, detail=result.get("error","Transcription failed"))
#         return {"transcript": result.get("transcript",""), "language": result.get("language", req.lang),
#                 "confidence": result.get("confidence",0.0), "duration_s": result.get("duration_s")}
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"STT error: {e}")


# @router.get("/voice/cache-status")
# def voice_cache_status():
    """Check S3 audio cache. Use before demo to verify cache is warm."""
    try:
        from src.storage.s3 import AUDIO_CACHE_MANIFEST
        return {"total_files": len(AUDIO_CACHE_MANIFEST),
                "files": [{"key": k, "text_preview": v.get("text","")[:60]} for k,v in AUDIO_CACHE_MANIFEST.items()]}
    except Exception as e:
        return {"error": str(e), "total_files": 0}
    
