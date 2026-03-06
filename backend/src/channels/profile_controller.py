"""
src/controllers/profile_controller.py
=======================================
Routes:
  GET  /profile      → get current user's profile
  POST /profile      → save/update profile
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.services.profile_service import ProfileService
from src.middleware.auth_middleware import get_current_user

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileRequest(BaseModel):
    name:                  Optional[str]  = None
    age:                   Optional[int]  = None
    gender:                Optional[str]  = None
    caste:                 Optional[str]  = None    
    district:              Optional[str]  = None
    is_govt_employee:      Optional[bool] = None
    pays_income_tax:       Optional[bool] = None
    has_daughter:          Optional[bool] = None
    has_school_child:      Optional[bool] = None
    is_enrolled_in_school: Optional[bool] = None
    is_unemployed:         Optional[bool] = None
    annual_income_bracket: Optional[str]  = None


@router.get("", summary="Get current user profile")
def get_profile(user: dict = Depends(get_current_user)):
    profile = ProfileService.get_profile(user["sub"])
    if not profile:
        return {"phone": user["sub"], "name": None, "completed": False}
    profile["completed"] = ProfileService._profile_is_complete(profile) if hasattr(ProfileService, '_profile_is_complete') else bool(profile.get("name"))
    return profile


@router.post("", summary="Save or update user profile")
def save_profile(req: ProfileRequest, user: dict = Depends(get_current_user)):
    data = {k: v for k, v in req.model_dump().items() if v is not None}
    result = ProfileService.save_profile(user["sub"], data)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("errors", "Save failed"))
    return result