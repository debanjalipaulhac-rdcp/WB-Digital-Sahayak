"""
src/services/auth_service.py
=============================
All authentication business logic.

Flow:
  1. send_otp(phone)   → generate OTP → hash it → store → send SMS
  2. verify_otp(phone, otp) → compare hash → issue JWT pair
  3. refresh_token(token) → validate refresh → issue new access token
  4. logout(phone) → delete refresh token from DB

Security:
  - OTP is hashed with bcrypt before storage (never store raw OTP)
  - JWT access token: 7 days (mobile-first, rural users don't log in daily)
  - JWT refresh token: 30 days
  - Max 3 OTP attempts before lockout
  - OTP expires in 5 minutes
"""

import random
import string
import hashlib
import hmac
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import jwt
import bcrypt

from src.config.settings import settings
from src.repository.dynamo_repo import UserRepository

logger = logging.getLogger(__name__)


# ── OTP Utilities ─────────────────────────────────────────────────────────────

def _generate_otp() -> str:
    """Generate cryptographically random 6-digit OTP."""
    if settings.MOCK_MODE or settings.SMS_PROVIDER == "mock":
        return "123456"   # fixed for local dev/demo
    return "".join(random.SystemRandom().choices(string.digits, k=settings.OTP_LENGTH))


def _hash_otp(otp: str, phone: str) -> str:
    """
    Hash OTP using bcrypt.
    Phone is used as pepper (extra secret beyond salt).
    This means stolen DB rows can't be brute-forced without the pepper.
    """
    pepper = f"{phone}:{settings.JWT_SECRET_KEY}"
    salted = f"{otp}:{pepper}"
    return bcrypt.hashpw(salted.encode(), bcrypt.gensalt(rounds=10)).decode()


def _verify_otp_hash(otp: str, phone: str, stored_hash: str) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    try:
        pepper = f"{phone}:{settings.JWT_SECRET_KEY}"
        salted = f"{otp}:{pepper}"
        return bcrypt.checkpw(salted.encode(), stored_hash.encode())
    except Exception:
        return False


def _hash_token(token: str) -> str:
    """SHA-256 hash of refresh token for storage. Fast is fine here."""
    return hashlib.sha256(token.encode()).hexdigest()


# ── SMS Sending ────────────────────────────────────────────────────────────────

def _send_sms(phone: str, otp: str) -> bool:
    """
    Send OTP via configured provider.
    Providers: mock (dev) | twilio | fast2sms
    """
    if settings.SMS_PROVIDER == "mock":
        logger.warning(f"[MOCK SMS] OTP for {phone}: {otp}")
        return True

    if settings.SMS_PROVIDER == "twilio":
        return _send_twilio(phone, otp)

    if settings.SMS_PROVIDER == "fast2sms":
        return _send_fast2sms(phone, otp)

    logger.error(f"Unknown SMS_PROVIDER: {settings.SMS_PROVIDER}")
    return False


def _send_twilio(phone: str, otp: str) -> bool:
    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        msg = f"Your WB Digital Sahayak OTP is {otp}. Valid for 5 minutes. Do not share."
        client.messages.create(body=msg, from_=settings.TWILIO_PHONE_NUMBER, to=phone)
        return True
    except Exception as e:
        logger.error(f"Twilio SMS failed for {phone}: {e}")
        return False


def _send_fast2sms(phone: str, otp: str) -> bool:
    try:
        import requests
        # Strip country code for Fast2SMS (expects 10-digit Indian number)
        number = phone.replace("+91", "").replace(" ", "")
        resp = requests.post(
            "https://www.fast2sms.com/dev/bulkV2",
            headers={"authorization": settings.FAST2SMS_API_KEY},
            json={
                "route": "otp",
                "variables_values": otp,
                "numbers": number,
            },
            timeout=10,
        )
        return resp.json().get("return", False)
    except Exception as e:
        logger.error(f"Fast2SMS failed for {phone}: {e}")
        return False


# ── JWT Utilities ──────────────────────────────────────────────────────────────

def _create_access_token(phone: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": phone,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _create_refresh_token(phone: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": phone,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate JWT. Returns payload dict or None.
    Used by auth middleware / Depends(get_current_user).
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "access":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        logger.info("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None


# ── Public Service Methods ────────────────────────────────────────────────────

class AuthService:

    @staticmethod
    def send_otp(phone: str) -> dict:
        """
        Generate OTP, hash it, store in DynamoDB, send SMS.

        Returns:
            {success: bool, message: str, expires_in: int}
        """
        # Validate phone format
        clean = phone.strip().replace(" ", "")
        if not clean.startswith("+91") or len(clean) != 13:
            return {"success": False, "message": "Invalid phone number. Use +91XXXXXXXXXX format."}

        otp = _generate_otp()
        otp_hash = _hash_otp(otp, clean)
        expires_at = int(time.time()) + settings.OTP_EXPIRE_SECONDS

        saved = UserRepository.save_otp(clean, otp_hash, expires_at)
        if not saved:
            return {"success": False, "message": "Failed to generate OTP. Try again."}

        sent = _send_sms(clean, otp)
        if not sent:
            return {"success": False, "message": "Failed to send SMS. Try again."}

        return {
            "success": True,
            "message": f"OTP sent to {clean[-4:].rjust(13, '*')}",
            "expires_in": settings.OTP_EXPIRE_SECONDS,
        }

    @staticmethod
    def verify_otp(phone: str, otp: str) -> dict:
        """
        Verify OTP → return JWT pair + user info.

        Returns:
            {success, access_token, refresh_token, is_new_user, user}
        """
        clean = phone.strip().replace(" ", "")
        record = UserRepository.get_otp_record(clean)

        if not record:
            return {"success": False, "message": "No OTP found. Please request a new one."}

        # Check expiry
        if int(time.time()) > int(record.get("expires_at", 0)):
            UserRepository.delete_otp(clean)
            return {"success": False, "message": "OTP expired. Please request a new one."}

        # Check attempt limit
        attempts = int(record.get("attempts", 0))
        if attempts >= settings.OTP_MAX_ATTEMPTS:
            UserRepository.delete_otp(clean)
            return {"success": False, "message": "Too many wrong attempts. Request a new OTP."}

        # Verify hash
        if not _verify_otp_hash(otp, clean, record["otp_hash"]):
            UserRepository.increment_otp_attempts(clean)
            remaining = settings.OTP_MAX_ATTEMPTS - attempts - 1
            return {"success": False, "message": f"Wrong OTP. {remaining} attempts remaining."}

        # OTP correct — clean up and issue tokens
        UserRepository.delete_otp(clean)

        access_token  = _create_access_token(clean)
        refresh_token = _create_refresh_token(clean)

        # Store hashed refresh token
        rt_expires = int(time.time()) + (settings.JWT_REFRESH_EXPIRE_DAYS * 86400)
        UserRepository.save_refresh_token(clean, _hash_token(refresh_token), rt_expires)

        # Check if new user (no profile yet)
        profile = UserRepository.get_profile(clean)
        is_new_user = profile is None

        if is_new_user:
            # Create minimal profile stub
            UserRepository.save_profile(clean, {"phone": clean, "verified": True})

        return {
            "success": True,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "is_new_user": is_new_user,
            "user": {
                "phone": clean,
                "name": profile.get("name") if profile else None,
                "verified": True,
            },
        }

    @staticmethod
    def refresh_access_token(refresh_token: str) -> dict:
        """Exchange a valid refresh token for a new access token."""
        try:
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except jwt.ExpiredSignatureError:
            return {"success": False, "message": "Refresh token expired. Please login again."}
        except jwt.InvalidTokenError:
            return {"success": False, "message": "Invalid refresh token."}

        if payload.get("type") != "refresh":
            return {"success": False, "message": "Invalid token type."}

        phone = payload["sub"]
        stored = UserRepository.get_refresh_token(phone)

        if not stored:
            return {"success": False, "message": "Session expired. Please login again."}

        # Verify the stored hash matches
        if stored.get("token_hash") != _hash_token(refresh_token):
            return {"success": False, "message": "Token mismatch. Please login again."}

        # Check DB-level expiry
        if int(time.time()) > int(stored.get("expires_at", 0)):
            UserRepository.delete_refresh_token(phone)
            return {"success": False, "message": "Session expired. Please login again."}

        new_access = _create_access_token(phone)
        return {
            "success": True,
            "access_token": new_access,
            "token_type": "Bearer",
        }

    @staticmethod
    def logout(phone: str) -> dict:
        """Invalidate refresh token — next access token use will fail on refresh."""
        UserRepository.delete_refresh_token(phone)
        return {"success": True, "message": "Logged out successfully."}