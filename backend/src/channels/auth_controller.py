"""
src/controllers/auth_controller.py
====================================
HTTP layer for auth routes. No business logic — delegates to AuthService.

Routes:
  POST /auth/send-otp       → request OTP
  POST /auth/verify-otp     → verify OTP, get JWT
  POST /auth/refresh         → exchange refresh token for new access token
  POST /auth/logout          → invalidate session
  POST /auth/update-name     → set name after first login (new user flow)
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from src.services.auth_service import AuthService
from src.services.profile_service import ProfileService
from src.middleware.auth_middleware import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Request Models ────────────────────────────────────────────────────────────

class SendOTPRequest(BaseModel):
    phone: str = Field(..., example="+919876543210", description="E.164 format")


class VerifyOTPRequest(BaseModel):
    phone: str  = Field(..., example="+919876543210")
    otp:   str  = Field(..., min_length=6, max_length=6, example="123456")


class RefreshRequest(BaseModel):
    refresh_token: str


class UpdateNameRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/send-otp", summary="Request OTP for phone number")
def send_otp(req: SendOTPRequest):
    """
    Send a 6-digit OTP to the given phone number.
    Rate limiting: 1 OTP per 60s (enforced in DynamoDB TTL — if OTP record exists, reject).
    In MOCK_MODE: always returns success, OTP is 123456.
    """
    result = AuthService.send_otp(req.phone)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/verify-otp", summary="Verify OTP and get JWT tokens")
def verify_otp(req: VerifyOTPRequest):
    """
    Verify OTP. On success returns:
      - access_token (JWT, 7 days)
      - refresh_token (JWT, 30 days, also stored hashed in DynamoDB)
      - is_new_user (bool — frontend shows name setup screen if true)
    """
    result = AuthService.verify_otp(req.phone, req.otp)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["message"])
    return result


@router.post("/refresh", summary="Get new access token using refresh token")
def refresh_token(req: RefreshRequest):
    """
    Exchange a valid refresh token for a new access token.
    Does NOT issue a new refresh token (sliding sessions not needed here).
    """
    result = AuthService.refresh_access_token(req.refresh_token)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["message"])
    return result


@router.post("/logout", summary="Invalidate session")
def logout(user: dict = Depends(get_current_user)):
    """
    Deletes the stored refresh token. Access token stays valid until expiry
    (short-lived enough for our use case — no token blacklist needed).
    """
    result = AuthService.logout(user["sub"])
    return result


@router.post("/update-name", summary="Set user name after first login")
def update_name(req: UpdateNameRequest, user: dict = Depends(get_current_user)):
    """
    Called after OTP verification when is_new_user=true.
    Lets users set their display name without filling the full profile.
    """
    result = ProfileService.update_name(user["sub"], req.name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.get("/me", summary="Get current user info")
def get_me(user: dict = Depends(get_current_user)):
    """Lightweight endpoint — just validates the token and returns user info."""
    profile = ProfileService.get_profile(user["sub"])
    return {
        "phone": user["sub"],
        "name": profile.get("name") if profile else None,
        "has_profile": profile is not None and bool(profile.get("name")),
    }