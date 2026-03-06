"""
src/middleware/auth_middleware.py
==================================
FastAPI dependency injection for JWT authentication.

Usage in routes:
    from src.middleware.auth_middleware import get_current_user, get_optional_user

    # Protected route — 401 if no valid token
    @router.get("/profile")
    def get_profile(user: dict = Depends(get_current_user)):
        return {"phone": user["sub"]}

    # Optional auth — works with or without token
    @router.get("/recommendations")
    def recommendations(user: dict = Depends(get_optional_user)):
        phone = user["sub"] if user else None
        ...
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.services.auth_service import decode_access_token

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Strict auth dependency. Raises 401 if token is missing or invalid.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload   # {"sub": phone, "exp": ..., "iat": ...}


def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict | None:
    """
    Optional auth dependency. Returns None if no token (doesn't raise).
    Used for routes that work for both anonymous and logged-in users.
    """
    if not credentials:
        return None
    return decode_access_token(credentials.credentials)