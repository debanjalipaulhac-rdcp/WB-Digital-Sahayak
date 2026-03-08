# """
# tests/test_e2e.py
# ==================
# End-to-end tests for all controllers:
#   - AuthController    → /auth/*
#   - ProfileController → /profile
#   - SchemesController → /schemes, /recommendations, /eligibility, /script, /applications

# Strategy:
#   - All AWS (DynamoDB, Bedrock) calls are MOCKED — no real cloud calls
#   - FastAPI TestClient runs real HTTP pipeline (middleware, validation, routing)
#   - Each test group is independent — no shared state between tests
#   - Covers: happy path, validation errors, auth failures, edge cases

# Run:
#   pip install pytest pytest-mock httpx
#   pytest tests/test_e2e.py -v
# """

# import json
# import time
# import pytest
# from unittest.mock import MagicMock, patch, ANY
# from fastapi.testclient import TestClient

# # ─────────────────────────────────────────────────────────────
# # APP SETUP — patch AWS before importing app
# # ─────────────────────────────────────────────────────────────

# # Patch boto3 at the root so no real AWS calls ever happen
# import boto3
# boto3.resource = MagicMock()
# boto3.client   = MagicMock()

# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware

# # Build a test app with all routers — mirrors main.py
# app = FastAPI()
# app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# from src.channels.auth_controller    import router as auth_router
# from src.channels.schemes_controller import router as schemes_router
# from src.channels.profile_controller import router as profile_router

# app.include_router(auth_router,    prefix="/api/v1")
# app.include_router(schemes_router, prefix="/api/v1")
# app.include_router(profile_router, prefix="/api/v1")

# client = TestClient(app, raise_server_exceptions=False)


# # ─────────────────────────────────────────────────────────────
# # FIXTURES
# # ─────────────────────────────────────────────────────────────

# VALID_PHONE   = "+919876543210"
# VALID_OTP     = "123456"
# TEST_PHONE    = "+919999999999"

# # Minimal valid profile matching WB scheme eligibility fields
# COMPLETE_PROFILE = {
#     "name":                  "Priya Das",
#     "age":                   30,
#     "gender":                "female",
#     "caste":                 "sc",
#     "district":              "kolkata",
#     "is_govt_employee":      False,
#     "pays_income_tax":       False,
#     "has_daughter":          False,
#     "has_school_child":      False,
#     "is_enrolled_in_school": False,
#     "is_unemployed":         False,
#     "annual_income_bracket": "below_1l",
# }

# # Minimal document checks for Lakshmir Bhandar
# DOCUMENT_CHECKS_PASS = {
#     "aadhaar_name":                   "Priya Das",
#     "bank_name":                      "Priya Das",
#     "voter_name":                     "Priya Das",
#     "ration_name":                    "",
#     "aadhaar_bank_linked":            True,
#     "bank_last_transaction_months_ago": 2,
#     "address_match_ok":               True,
#     "docs_present":                   ["aadhaar", "voter_id", "bank_passbook"],
#     "docs_missing":                   [],
# }

# DOCUMENT_CHECKS_FAIL = {
#     "aadhaar_name":                   "Priya Das",
#     "bank_name":                      "Priyya Daas",   # name mismatch
#     "voter_name":                     "",
#     "ration_name":                    "",
#     "aadhaar_bank_linked":            False,            # not linked
#     "bank_last_transaction_months_ago": 10,             # dormant
#     "address_match_ok":               False,
#     "docs_present":                   ["aadhaar"],
#     "docs_missing":                   ["voter_id", "bank_passbook"],
# }


# def _make_jwt(phone: str = VALID_PHONE) -> str:
#     """Generate a real JWT for test auth headers."""
#     import jwt as pyjwt
#     from datetime import datetime, timezone, timedelta
#     payload = {
#         "sub":  phone,
#         "type": "access",
#         "iat":  datetime.now(timezone.utc),
#         "exp":  datetime.now(timezone.utc) + timedelta(hours=1),
#     }
#     # Use same secret as settings
#     from src.config.settings import settings
#     return pyjwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# def _auth_header(phone: str = VALID_PHONE) -> dict:
#     return {"Authorization": f"Bearer {_make_jwt(phone)}"}


# # ─────────────────────────────────────────────────────────────
# # SAMPLE DATA
# # ─────────────────────────────────────────────────────────────

# LAKSHMIR_BHANDAR = {
#     "scheme_id":      "lakshmir_bhandar",
#     "scheme_name":    "Lakshmir Bhandar",
#     "scheme_name_bn": "লক্ষ্মীর ভাণ্ডার",
#     "tag":            "WOMEN",
#     "benefit_display": "₹1,000–₹1,200/month",
#     "department":     "Women & Child Development Department, WB",
#     "eligibility": {
#         "gender":                      "female",
#         "age_min":                     25,
#         "age_max":                     60,
#         "not_govt_employee":           True,
#         "not_income_tax_payer":        True,
#         "not_enrolled_in_other_cash_scheme": True,
#         "state_resident":              True,
#     },
#     "benefits": {
#         "mode":           "DBT",
#         "general_monthly": 1000,
#         "sc_st_monthly":   1200,
#         "note_en":         "SC/ST women receive ₹1,200/month.",
#         "note_bn":         "SC/ST মহিলারা মাসে ₹১,২০০ পাবেন।",
#     },
#     "documents": [
#         {"doc_id": "aadhaar",     "label": "Aadhaar Card",  "label_bn": "আধার কার্ড",  "required": True,  "score_deduction_if_missing": 20},
#         {"doc_id": "voter_id",    "label": "Voter ID",      "label_bn": "ভোটার কার্ড", "required": True,  "score_deduction_if_missing": 15},
#         {"doc_id": "bank_passbook","label": "Bank Passbook","label_bn": "ব্যাংক পাসবুক","required": True,  "score_deduction_if_missing": 20},
#         {"doc_id": "ration_card", "label": "Ration Card",  "label_bn": "রেশন কার্ড",  "required": False, "score_deduction_if_missing": 5},
#     ],
#     "mismatch_checks": [
#         {
#             "check_id": "name_aadhaar_bank",
#             "field":    "name",
#             "doc_a":    "aadhaar",
#             "doc_b":    "bank_passbook",
#             "severity": "FATAL",
#             "score_deduction": 35,
#             "message_en": "Name on Aadhaar must exactly match Bank Passbook.",
#             "message_bn": "আধার কার্ডের নাম ব্যাংক পাসবুকের সাথে একই হতে হবে।",
#             "script_code": "NAME_MISMATCH",
#         }
#     ],
#     "bank_conditions": {
#         "aadhaar_linked_required":  True,
#         "dormant_check":            True,
#         "dormant_threshold_months": 6,
#         "score_deduction_unlinked": 25,
#         "score_deduction_dormant":  25,
#         "script_code_unlinked":     "AADHAAR_UNLINKED",
#         "script_code_dormant":      "DORMANT_ACCOUNT",
#     },
#     "apply_at": [
#         {"step": 1, "office": "BDO Office"},
#         {"step": 2, "office": "Duare Sarkar Camp"},
#     ],
# }

# SWASTHYA_SATHI = {
#     "scheme_id":      "swasthya_sathi",
#     "scheme_name":    "Swasthya Sathi",
#     "scheme_name_bn": "স্বাস্থ্য সাথী",
#     "tag":            "HEALTH",
#     "benefit_display": "₹5 lakh health cover/year",
#     "department":     "Health & Family Welfare Department, WB",
#     "eligibility": {
#         "gender":    "all",
#         "age_min":   0,
#         "age_max":   999,
#         "state_resident": True,
#     },
#     "benefits": {
#         "mode":          "Cashless at empanelled hospitals",
#         "cashless_limit": 500000,
#         "note_en":       "Covers entire family.",
#         "note_bn":       "পুরো পরিবার অন্তর্ভুক্ত।",
#     },
#     "documents":       [],
#     "mismatch_checks": [],
#     "bank_conditions": {"aadhaar_linked_required": False, "dormant_check": False},
#     "apply_at": [{"step": 1, "office": "BDO Office"}],
# }

# ALL_SCHEMES = [LAKSHMIR_BHANDAR, SWASTHYA_SATHI]


# # ═════════════════════════════════════════════════════════════
# # 1. AUTH CONTROLLER TESTS
# # ═════════════════════════════════════════════════════════════

# class TestSendOTP:

#     def test_send_otp_valid_phone(self):
#         """Valid +91 phone → OTP sent successfully."""
#         with patch("src.services.auth_service.UserRepository.save_otp", return_value=True), \
#              patch("src.services.auth_service._send_sms",                return_value=True):
#             r = client.post("/auth/send-otp", json={"phone": VALID_PHONE})
#         assert r.status_code == 200
#         body = r.json()
#         assert body["success"] is True
#         assert "expires_in" in body

#     def test_send_otp_invalid_phone_no_country_code(self):
#         """Phone without +91 prefix → 400."""
#         r = client.post("/auth/send-otp", json={"phone": "9876543210"})
#         assert r.status_code == 400

#     def test_send_otp_invalid_phone_wrong_length(self):
#         """Phone too short → 400."""
#         r = client.post("/auth/send-otp", json={"phone": "+9198765"})
#         assert r.status_code == 400

#     def test_send_otp_invalid_phone_empty(self):
#         """Empty phone → 422 Unprocessable."""
#         r = client.post("/auth/send-otp", json={"phone": ""})
#         assert r.status_code in (400, 422)

#     def test_send_otp_missing_phone_field(self):
#         """Missing phone field → 422."""
#         r = client.post("/auth/send-otp", json={})
#         assert r.status_code == 422

#     def test_send_otp_sms_failure(self):
#         """DynamoDB save OK but SMS fails → 400."""
#         with patch("src.services.auth_service.UserRepository.save_otp", return_value=True), \
#              patch("src.services.auth_service._send_sms",                return_value=False):
#             r = client.post("/auth/send-otp", json={"phone": VALID_PHONE})
#         assert r.status_code == 400

#     def test_send_otp_dynamo_failure(self):
#         """DynamoDB save fails → 400."""
#         with patch("src.services.auth_service.UserRepository.save_otp", return_value=False):
#             r = client.post("/auth/send-otp", json={"phone": VALID_PHONE})
#         assert r.status_code == 400


# class TestVerifyOTP:

#     def _mock_otp_record(self, otp: str = VALID_OTP, phone: str = VALID_PHONE) -> dict:
#         """Build a valid OTP record as DynamoDB would return."""
#         import bcrypt
#         from src.config.settings import settings
#         pepper = f"{phone}:{settings.JWT_SECRET_KEY}"
#         salted = f"{otp}:{pepper}"
#         otp_hash = bcrypt.hashpw(salted.encode(), bcrypt.gensalt(10)).decode()
#         return {
#             "phone":      phone,
#             "sk":         "OTP",
#             "otp_hash":   otp_hash,
#             "expires_at": int(time.time()) + 300,
#             "attempts":   0,
#         }

#     def test_verify_otp_correct(self):
#         """Correct OTP → access_token + refresh_token returned."""
#         record = self._mock_otp_record()
#         with patch("src.services.auth_service.UserRepository.get_otp_record",    return_value=record), \
#              patch("src.services.auth_service.UserRepository.delete_otp",         return_value=None), \
#              patch("src.services.auth_service.UserRepository.save_refresh_token", return_value=True), \
#              patch("src.services.auth_service.UserRepository.get_profile",        return_value=None), \
#              patch("src.services.auth_service.UserRepository.save_profile",       return_value=True):
#             r = client.post("/auth/verify-otp", json={"phone": VALID_PHONE, "otp": VALID_OTP})
#         assert r.status_code == 200
#         body = r.json()
#         assert "access_token"  in body
#         assert "refresh_token" in body
#         assert body["token_type"] == "Bearer"
#         assert "is_new_user" in body

#     def test_verify_otp_wrong_otp(self):
#         """Wrong OTP → 401."""
#         record = self._mock_otp_record()
#         with patch("src.services.auth_service.UserRepository.get_otp_record",        return_value=record), \
#              patch("src.services.auth_service.UserRepository.increment_otp_attempts", return_value=1):
#             r = client.post("/auth/verify-otp", json={"phone": VALID_PHONE, "otp": "000000"})
#         assert r.status_code == 401
#         assert "wrong" in r.json()["detail"].lower()

#     def test_verify_otp_expired(self):
#         """Expired OTP record → 401."""
#         expired_record = self._mock_otp_record()
#         expired_record["expires_at"] = int(time.time()) - 10   # already expired
#         with patch("src.services.auth_service.UserRepository.get_otp_record", return_value=expired_record), \
#              patch("src.services.auth_service.UserRepository.delete_otp",      return_value=None):
#             r = client.post("/auth/verify-otp", json={"phone": VALID_PHONE, "otp": VALID_OTP})
#         assert r.status_code == 401
#         assert "expired" in r.json()["detail"].lower()

#     def test_verify_otp_no_record(self):
#         """No OTP record in DB → 401."""
#         with patch("src.services.auth_service.UserRepository.get_otp_record", return_value=None):
#             r = client.post("/auth/verify-otp", json={"phone": VALID_PHONE, "otp": VALID_OTP})
#         assert r.status_code == 401

#     def test_verify_otp_max_attempts_exceeded(self):
#         """OTP record has 3+ attempts → 401 lockout."""
#         record = self._mock_otp_record()
#         record["attempts"] = 3
#         with patch("src.services.auth_service.UserRepository.get_otp_record", return_value=record), \
#              patch("src.services.auth_service.UserRepository.delete_otp",      return_value=None):
#             r = client.post("/auth/verify-otp", json={"phone": VALID_PHONE, "otp": VALID_OTP})
#         assert r.status_code == 401
#         assert "attempts" in r.json()["detail"].lower()

#     def test_verify_otp_otp_too_short(self):
#         """OTP length != 6 → 422 validation error."""
#         r = client.post("/auth/verify-otp", json={"phone": VALID_PHONE, "otp": "123"})
#         assert r.status_code == 422

#     def test_verify_otp_is_new_user_true(self):
#         """No existing profile → is_new_user=True."""
#         record = self._mock_otp_record()
#         with patch("src.services.auth_service.UserRepository.get_otp_record",    return_value=record), \
#              patch("src.services.auth_service.UserRepository.delete_otp",         return_value=None), \
#              patch("src.services.auth_service.UserRepository.save_refresh_token", return_value=True), \
#              patch("src.services.auth_service.UserRepository.get_profile",        return_value=None), \
#              patch("src.services.auth_service.UserRepository.save_profile",       return_value=True):
#             r = client.post("/auth/verify-otp", json={"phone": VALID_PHONE, "otp": VALID_OTP})
#         assert r.json()["is_new_user"] is True

#     def test_verify_otp_is_new_user_false(self):
#         """Existing profile → is_new_user=False."""
#         record = self._mock_otp_record()
#         with patch("src.services.auth_service.UserRepository.get_otp_record",    return_value=record), \
#              patch("src.services.auth_service.UserRepository.delete_otp",         return_value=None), \
#              patch("src.services.auth_service.UserRepository.save_refresh_token", return_value=True), \
#              patch("src.services.auth_service.UserRepository.get_profile",        return_value={"name": "Priya"}), \
#              patch("src.services.auth_service.UserRepository.save_profile",       return_value=True):
#             r = client.post("/auth/verify-otp", json={"phone": VALID_PHONE, "otp": VALID_OTP})
#         assert r.json()["is_new_user"] is False


# class TestRefreshToken:

#     def test_refresh_valid_token(self):
#         """Valid refresh token → new access token."""
#         import jwt as pyjwt
#         from datetime import datetime, timezone, timedelta
#         from src.config.settings import settings
#         refresh = pyjwt.encode(
#             {"sub": VALID_PHONE, "type": "refresh",
#              "iat": datetime.now(timezone.utc),
#              "exp": datetime.now(timezone.utc) + timedelta(days=30)},
#             settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
#         )
#         import hashlib
#         token_hash = hashlib.sha256(refresh.encode()).hexdigest()
#         stored = {"token_hash": token_hash, "expires_at": int(time.time()) + 86400}

#         with patch("src.services.auth_service.UserRepository.get_refresh_token", return_value=stored):
#             r = client.post("/auth/refresh", json={"refresh_token": refresh})
#         assert r.status_code == 200
#         assert "access_token" in r.json()

#     def test_refresh_expired_token(self):
#         """Expired refresh token → 401."""
#         import jwt as pyjwt
#         from datetime import datetime, timezone, timedelta
#         from src.config.settings import settings
#         expired = pyjwt.encode(
#             {"sub": VALID_PHONE, "type": "refresh",
#              "iat": datetime.now(timezone.utc) - timedelta(days=60),
#              "exp": datetime.now(timezone.utc) - timedelta(days=1)},
#             settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
#         )
#         r = client.post("/auth/refresh", json={"refresh_token": expired})
#         assert r.status_code == 401
#         assert "expired" in r.json()["detail"].lower()

#     def test_refresh_invalid_token(self):
#         """Garbage token → 401."""
#         r = client.post("/auth/refresh", json={"refresh_token": "not.a.token"})
#         assert r.status_code == 401

#     def test_refresh_missing_field(self):
#         """Missing refresh_token field → 422."""
#         r = client.post("/auth/refresh", json={})
#         assert r.status_code == 422


# class TestGetMe:

#     def test_get_me_authenticated(self):
#         """Valid JWT → returns phone + name."""
#         profile = {**COMPLETE_PROFILE, "phone_number": VALID_PHONE}
#         with patch("src.services.profile_service.UserRepository.get_profile", return_value=profile):
#             r = client.get("/auth/me", headers=_auth_header())
#         assert r.status_code == 200
#         assert r.json()["phone"] == VALID_PHONE

#     def test_get_me_no_token(self):
#         """No auth header → 401 or 403."""
#         r = client.get("/auth/me")
#         assert r.status_code in (401, 403)

#     def test_get_me_invalid_token(self):
#         """Malformed token → 401."""
#         r = client.get("/auth/me", headers={"Authorization": "Bearer garbage"})
#         assert r.status_code in (401, 403)

#     def test_get_me_no_profile(self):
#         """Valid token but no profile → has_profile=False."""
#         with patch("src.services.profile_service.UserRepository.get_profile", return_value=None):
#             r = client.get("/auth/me", headers=_auth_header())
#         assert r.status_code == 200
#         assert r.json()["has_profile"] is False


# class TestLogout:

#     def test_logout_authenticated(self):
#         """Valid token → logs out successfully."""
#         with patch("src.services.auth_service.UserRepository.delete_refresh_token", return_value=None):
#             r = client.post("/auth/logout", headers=_auth_header())
#         assert r.status_code == 200
#         assert r.json()["success"] is True

#     def test_logout_no_token(self):
#         """No auth → 401."""
#         r = client.post("/auth/logout")
#         assert r.status_code in (401, 403)


# # ═════════════════════════════════════════════════════════════
# # 2. PROFILE CONTROLLER TESTS
# # ═════════════════════════════════════════════════════════════

# class TestGetProfile:

#     def test_get_profile_complete(self):
#         """Logged-in user with full profile → all fields returned + completed=True."""
#         stored = {**COMPLETE_PROFILE, "phone_number": VALID_PHONE}
#         with patch("src.services.profile_service.UserRepository.get_profile", return_value=stored):
#             r = client.get("/profile", headers=_auth_header())
#         assert r.status_code == 200
#         body = r.json()
#         assert body["name"]      == "Priya Das"
#         assert body["age"]       == 30
#         assert body["gender"]    == "female"
#         assert body["caste"]     == "sc"
#         assert body["completed"] is True

#     def test_get_profile_empty(self):
#         """No profile in DB → returns stub with completed=False."""
#         with patch("src.services.profile_service.UserRepository.get_profile", return_value=None):
#             r = client.get("/profile", headers=_auth_header())
#         assert r.status_code == 200
#         body = r.json()
#         assert body["completed"] is False
#         assert body["name"] is None

#     def test_get_profile_unauthenticated(self):
#         """No token → 401."""
#         r = client.get("/profile")
#         assert r.status_code in (401, 403)

#     def test_get_profile_partial(self):
#         """Profile with only name set → completed=False (missing age/gender/caste)."""
#         partial = {"phone_number": VALID_PHONE, "name": "Priya"}
#         with patch("src.services.profile_service.UserRepository.get_profile", return_value=partial):
#             r = client.get("/profile", headers=_auth_header())
#         assert r.status_code == 200
#         assert r.json()["completed"] is False


# class TestSaveProfile:

#     def test_save_profile_full_valid(self):
#         """All valid fields → 200 success."""
#         with patch("src.repository.dynamo_repo.UserRepository.save_profile", return_value=None):
#             r = client.post("/profile", headers=_auth_header(), json=COMPLETE_PROFILE)
#         assert r.status_code == 200
#         assert r.json()["success"] is True

#     def test_save_profile_partial_update(self):
#         """Only name + age → valid partial update (all fields optional)."""
#         with patch("src.repository.dynamo_repo.UserRepository.save_profile", return_value=None):
#             r = client.post("/profile", headers=_auth_header(), json={"name": "Rima", "age": 28})
#         assert r.status_code == 200

#     def test_save_profile_invalid_gender(self):
#         """Gender not in (male/female/other) → 400."""
#         data = {**COMPLETE_PROFILE, "gender": "alien"}
#         with patch("src.repository.dynamo_repo.UserRepository.save_profile", return_value=None):
#             r = client.post("/profile", headers=_auth_header(), json=data)
#         assert r.status_code == 400

#     def test_save_profile_invalid_caste(self):
#         """Caste not in valid set → 400."""
#         data = {**COMPLETE_PROFILE, "caste": "brahmin"}
#         with patch("src.repository.dynamo_repo.UserRepository.save_profile", return_value=None):
#             r = client.post("/profile", headers=_auth_header(), json=data)
#         assert r.status_code == 400

#     def test_save_profile_invalid_age_too_old(self):
#         """Age > 120 → 400."""
#         data = {**COMPLETE_PROFILE, "age": 150}
#         with patch("src.repository.dynamo_repo.UserRepository.save_profile", return_value=None):
#             r = client.post("/profile", headers=_auth_header(), json=data)
#         assert r.status_code == 400

#     def test_save_profile_invalid_age_zero(self):
#         """Age = 0 → 400."""
#         data = {**COMPLETE_PROFILE, "age": 0}
#         with patch("src.repository.dynamo_repo.UserRepository.save_profile", return_value=None):
#             r = client.post("/profile", headers=_auth_header(), json=data)
#         assert r.status_code == 400

#     def test_save_profile_invalid_age_negative(self):
#         """Age < 0 → 400."""
#         data = {**COMPLETE_PROFILE, "age": -5}
#         with patch("src.repository.dynamo_repo.UserRepository.save_profile", return_value=None):
#             r = client.post("/profile", headers=_auth_header(), json=data)
#         assert r.status_code == 400

#     def test_save_profile_all_boolean_fields(self):
#         """All boolean fields accepted correctly."""
#         data = {
#             "is_govt_employee":      True,
#             "pays_income_tax":       True,
#             "has_daughter":          True,
#             "has_school_child":      True,
#             "is_enrolled_in_school": True,
#             "is_unemployed":         True,
#         }
#         with patch("src.repository.dynamo_repo.UserRepository.save_profile", return_value=None):
#             r = client.post("/profile", headers=_auth_header(), json=data)
#         assert r.status_code == 200

#     def test_save_profile_unauthenticated(self):
#         """No token → 401."""
#         r = client.post("/profile", json=COMPLETE_PROFILE)
#         assert r.status_code in (401, 403)

#     def test_save_profile_empty_body(self):
#         """Empty body → 200 (all fields optional, nothing to save is valid)."""
#         with patch("src.repository.dynamo_repo.UserRepository.save_profile", return_value=None):
#             r = client.post("/profile", headers=_auth_header(), json={})
#         assert r.status_code == 200


# # ═════════════════════════════════════════════════════════════
# # 3. SCHEMES CONTROLLER TESTS
# # ═════════════════════════════════════════════════════════════

# class TestListSchemes:

#     def test_list_all_no_filter(self):
#         """No params → returns all schemes paginated."""
#         with patch("src.repository.dynamo_repo.SchemeRepository.get_all", return_value=ALL_SCHEMES):
#             r = client.get("/api/v1/schemes")
#         assert r.status_code == 200
#         body = r.json()
#         assert "schemes" in body
#         assert "total"   in body
#         assert "page"    in body

#     def test_list_filter_by_category_women(self):
#         """category=WOMEN → only WOMEN tagged schemes."""
#         with patch("src.repository.dynamo_repo.SchemeRepository.get_all", return_value=ALL_SCHEMES):
#             r = client.get("/api/v1/schemes?category=WOMEN")
#         assert r.status_code == 200
#         schemes = r.json()["schemes"]
#         assert all(s["tag"] == "WOMEN" for s in schemes)

#     def test_list_filter_by_category_health(self):
#         """category=HEALTH → only HEALTH tagged schemes."""
#         with patch("src.repository.dynamo_repo.SchemeRepository.get_all", return_value=ALL_SCHEMES):
#             r = client.get("/api/v1/schemes?category=HEALTH")
#         assert r.status_code == 200
#         schemes = r.json()["schemes"]
#         assert all(s["tag"] == "HEALTH" for s in schemes)

#     def test_list_search_by_name(self):
#         """q=lakshmir → matches Lakshmir Bhandar."""
#         with patch("src.repository.dynamo_repo.SchemeRepository.get_all", return_value=ALL_SCHEMES):
#             r = client.get("/api/v1/schemes?q=lakshmir")
#         assert r.status_code == 200
#         schemes = r.json()["schemes"]
#         assert any("lakshmir" in s["scheme_id"] for s in schemes)

#     def test_list_search_no_match(self):
#         """q=xyz → no results."""
#         with patch("src.repository.dynamo_repo.SchemeRepository.get_all", return_value=ALL_SCHEMES):
#             r = client.get("/api/v1/schemes?q=xyznonexistent")
#         assert r.status_code == 200
#         assert r.json()["total"] == 0

#     def test_list_sort_name_asc(self):
#         """sort=name_asc → alphabetical order."""
#         with patch("src.repository.dynamo_repo.SchemeRepository.get_all", return_value=ALL_SCHEMES):
#             r = client.get("/api/v1/schemes?sort=name_asc")
#         assert r.status_code == 200
#         names = [s["scheme_name"] for s in r.json()["schemes"]]
#         assert names == sorted(names)

#     def test_list_sort_name_desc(self):
#         """sort=name_desc → reverse alphabetical."""
#         with patch("src.repository.dynamo_repo.SchemeRepository.get_all", return_value=ALL_SCHEMES):
#             r = client.get("/api/v1/schemes?sort=name_desc")
#         assert r.status_code == 200
#         names = [s["scheme_name"] for s in r.json()["schemes"]]
#         assert names == sorted(names, reverse=True)

#     def test_list_pagination(self):
#         """page=1&page_size=1 → max 1 scheme per page."""
#         with patch("src.repository.dynamo_repo.SchemeRepository.get_all", return_value=ALL_SCHEMES):
#             r = client.get("/api/v1/schemes?page=1&page_size=1")
#         assert r.status_code == 200
#         assert len(r.json()["schemes"]) <= 1

#     def test_list_page_size_too_large(self):
#         """page_size=999 → 422 (max is 20)."""
#         r = client.get("/api/v1/schemes?page_size=999")
#         assert r.status_code == 422

#     def test_list_page_zero(self):
#         """page=0 → 422 (min is 1)."""
#         r = client.get("/api/v1/schemes?page=0")
#         assert r.status_code == 422

#     def test_list_no_auth_required(self):
#         """No auth header → still works (public endpoint)."""
#         with patch("src.repository.dynamo_repo.SchemeRepository.get_all", return_value=ALL_SCHEMES):
#             r = client.get("/api/v1/schemes")
#         assert r.status_code == 200


# class TestGetScheme:

#     def test_get_scheme_exists(self):
#         """Valid scheme_id → full scheme returned with all fields."""
#         with patch("src.repository.dynamo_repo.SchemeRepository.get_by_id", return_value=LAKSHMIR_BHANDAR):
#             r = client.get("/api/v1/schemes/lakshmir_bhandar")
#         assert r.status_code == 200
#         body = r.json()
#         assert body["scheme_id"]      == "lakshmir_bhandar"
#         assert body["scheme_name"]    == "Lakshmir Bhandar"
#         assert "eligibility"          in body
#         assert "documents"            in body
#         assert "benefits"             in body
#         assert "apply_at"             in body
#         assert "icon"                 in body
#         assert "accent_color"         in body

#     def test_get_scheme_not_found(self):
#         """Unknown scheme_id → 404."""
#         with patch("src.repository.dynamo_repo.SchemeRepository.get_by_id", return_value=None):
#             r = client.get("/api/v1/schemes/fake_scheme")
#         assert r.status_code == 404
#         assert "not found" in r.json()["detail"].lower()

#     def test_get_scheme_icon_derived_from_tag(self):
#         """WOMEN tag → icon=Heart."""
#         with patch("src.repository.dynamo_repo.SchemeRepository.get_by_id", return_value=LAKSHMIR_BHANDAR):
#             r = client.get("/api/v1/schemes/lakshmir_bhandar")
#         assert r.json()["icon"] == "Heart"

#     def test_get_scheme_accent_color_derived(self):
#         """WOMEN tag → accent_color=#E91E8C."""
#         with patch("src.repository.dynamo_repo.SchemeRepository.get_by_id", return_value=LAKSHMIR_BHANDAR):
#             r = client.get("/api/v1/schemes/lakshmir_bhandar")
#         assert r.json()["accent_color"] == "#E91E8C"

#     def test_get_scheme_health_icon(self):
#         """HEALTH tag → icon=Activity."""
#         with patch("src.repository.dynamo_repo.SchemeRepository.get_by_id", return_value=SWASTHYA_SATHI):
#             r = client.get("/api/v1/schemes/swasthya_sathi")
#         assert r.json()["icon"] == "Activity"

#     def test_get_scheme_no_auth_required(self):
#         """No auth → public endpoint, works fine."""
#         with patch("src.repository.dynamo_repo.SchemeRepository.get_by_id", return_value=SWASTHYA_SATHI):
#             r = client.get("/api/v1/schemes/swasthya_sathi")
#         assert r.status_code == 200


# class TestRecommendations:

#     def test_recommendations_anonymous_featured(self):
#         """No auth, no params → featured/random schemes."""
#         with patch("src.repository.dynamo_repo.SchemeRepository.get_all", return_value=ALL_SCHEMES):
#             r = client.get("/api/v1/recommendations")
#         assert r.status_code == 200
#         body = r.json()
#         assert body["mode"]         == "featured"
#         assert body["personalised"] is False
#         assert len(body["schemes"]) > 0

#     def test_recommendations_context_based(self):
#         """scheme_id param → context-based (related schemes)."""
#         with patch("src.repository.dynamo_repo.SchemeRepository.get_all", return_value=ALL_SCHEMES):
#             r = client.get("/api/v1/recommendations?scheme_id=lakshmir_bhandar")
#         assert r.status_code == 200
#         body = r.json()
#         # Should not include the current scheme itself
#         assert not any(s["scheme_id"] == "lakshmir_bhandar" for s in body["schemes"])

#     def test_recommendations_query_based(self):
#         """query=health → query-based."""
#         with patch("src.repository.dynamo_repo.SchemeRepository.get_all", return_value=ALL_SCHEMES):
#             r = client.get("/api/v1/recommendations?query=health")
#         assert r.status_code == 200
#         assert r.json()["mode"] in ("query", "featured")

#     def test_recommendations_profile_based_logged_in(self):
#         """Logged-in user with complete profile → profile mode."""
#         stored = {**COMPLETE_PROFILE, "phone_number": VALID_PHONE}
#         with patch("src.repository.dynamo_repo.UserRepository.get_profile", return_value=stored), \
#              patch("src.repository.dynamo_repo.SchemeRepository.get_all",   return_value=ALL_SCHEMES):
#             r = client.get("/api/v1/recommendations", headers=_auth_header())
#         assert r.status_code == 200
#         body = r.json()
#         assert body["mode"]         == "profile"
#         assert body["personalised"] is True

#     def test_recommendations_limit_respected(self):
#         """limit=1 → at most 1 scheme returned."""
#         with patch("src.repository.dynamo_repo.SchemeRepository.get_all", return_value=ALL_SCHEMES):
#             r = client.get("/api/v1/recommendations?limit=1")
#         assert r.status_code == 200
#         assert len(r.json()["schemes"]) <= 1

#     def test_recommendations_limit_too_high(self):
#         """limit=999 → 422."""
#         r = client.get("/api/v1/recommendations?limit=999")
#         assert r.status_code == 422

#     def test_recommendations_gender_filter(self):
#         """Female profile → male-only schemes excluded."""
#         female_profile = {**COMPLETE_PROFILE, "gender": "male", "phone_number": VALID_PHONE}
#         with patch("src.repository.dynamo_repo.UserRepository.get_profile", return_value=female_profile), \
#              patch("src.repository.dynamo_repo.SchemeRepository.get_all",   return_value=ALL_SCHEMES):
#             r = client.get("/api/v1/recommendations", headers=_auth_header())
#         assert r.status_code == 200
#         # Lakshmir Bhandar is female-only — must not appear for male user
#         scheme_ids = [s["scheme_id"] for s in r.json()["schemes"]]
#         assert "lakshmir_bhandar" not in scheme_ids


# class TestEligibility:

#     def test_eligibility_eligible_pass(self):
#         """Eligible female, age 30, SC caste → GREEN score, eligible_basic=True."""
#         with patch("src.engine.eligibility._load_schemes", return_value=ALL_SCHEMES):
#             r = client.post("/api/v1/eligibility", json={
#                 "scheme_id": "lakshmir_bhandar",
#                 "profile":   COMPLETE_PROFILE,
#                 "checks":    DOCUMENT_CHECKS_PASS,
#             })
#         assert r.status_code == 200
#         body = r.json()
#         assert body["eligible_basic"] is True
#         assert body["band"]  in ("GREEN", "AMBER")
#         assert body["score"] > 0
#         assert "passed_rules" in body
#         assert "failed_rules" in body
#         assert "roadmap"      in body
#         assert "benefit_info" in body

#     def test_eligibility_benefit_sc_amount(self):
#         """SC caste → monthly_amount should be 1200 (SC/ST rate)."""
#         with patch("src.engine.eligibility._load_schemes", return_value=ALL_SCHEMES):
#             r = client.post("/api/v1/eligibility", json={
#                 "scheme_id": "lakshmir_bhandar",
#                 "profile":   {**COMPLETE_PROFILE, "caste": "sc"},
#                 "checks":    DOCUMENT_CHECKS_PASS,
#             })
#         assert r.status_code == 200
#         benefit = r.json()["benefit_info"]
#         assert benefit.get("monthly_amount") == 1200

#     def test_eligibility_benefit_general_amount(self):
#         """General caste → monthly_amount = 1000."""
#         with patch("src.engine.eligibility._load_schemes", return_value=ALL_SCHEMES):
#             r = client.post("/api/v1/eligibility", json={
#                 "scheme_id": "lakshmir_bhandar",
#                 "profile":   {**COMPLETE_PROFILE, "caste": "general"},
#                 "checks":    DOCUMENT_CHECKS_PASS,
#             })
#         assert r.status_code == 200
#         benefit = r.json()["benefit_info"]
#         assert benefit.get("monthly_amount") == 1000

#     def test_eligibility_ineligible_wrong_gender(self):
#         """Male applicant for female-only scheme → eligible_basic=False, band=RED."""
#         with patch("src.engine.eligibility._load_schemes", return_value=ALL_SCHEMES):
#             r = client.post("/api/v1/eligibility", json={
#                 "scheme_id": "lakshmir_bhandar",
#                 "profile":   {**COMPLETE_PROFILE, "gender": "male"},
#                 "checks":    DOCUMENT_CHECKS_PASS,
#             })
#         assert r.status_code == 200
#         body = r.json()
#         assert body["eligible_basic"] is False
#         assert body["band"]  == "RED"
#         assert body["score"] == 0

#     def test_eligibility_ineligible_age_too_young(self):
#         """Age 20 < min 25 → ineligible."""
#         with patch("src.engine.eligibility._load_schemes", return_value=ALL_SCHEMES):
#             r = client.post("/api/v1/eligibility", json={
#                 "scheme_id": "lakshmir_bhandar",
#                 "profile":   {**COMPLETE_PROFILE, "age": 20},
#                 "checks":    DOCUMENT_CHECKS_PASS,
#             })
#         assert r.status_code == 200
#         assert r.json()["eligible_basic"] is False

#     def test_eligibility_ineligible_age_too_old(self):
#         """Age 65 > max 60 → ineligible."""
#         with patch("src.engine.eligibility._load_schemes", return_value=ALL_SCHEMES):
#             r = client.post("/api/v1/eligibility", json={
#                 "scheme_id": "lakshmir_bhandar",
#                 "profile":   {**COMPLETE_PROFILE, "age": 65},
#                 "checks":    DOCUMENT_CHECKS_PASS,
#             })
#         assert r.status_code == 200
#         assert r.json()["eligible_basic"] is False

#     def test_eligibility_ineligible_govt_employee(self):
#         """Govt employee → ineligible for Lakshmir Bhandar."""
#         with patch("src.engine.eligibility._load_schemes", return_value=ALL_SCHEMES):
#             r = client.post("/api/v1/eligibility", json={
#                 "scheme_id": "lakshmir_bhandar",
#                 "profile":   {**COMPLETE_PROFILE, "is_govt_employee": True},
#                 "checks":    DOCUMENT_CHECKS_PASS,
#             })
#         assert r.status_code == 200
#         assert r.json()["eligible_basic"] is False

#     def test_eligibility_ineligible_income_tax_payer(self):
#         """Income tax payer → ineligible."""
#         with patch("src.engine.eligibility._load_schemes", return_value=ALL_SCHEMES):
#             r = client.post("/api/v1/eligibility", json={
#                 "scheme_id": "lakshmir_bhandar",
#                 "profile":   {**COMPLETE_PROFILE, "pays_income_tax": True},
#                 "checks":    DOCUMENT_CHECKS_PASS,
#             })
#         assert r.status_code == 200
#         assert r.json()["eligible_basic"] is False

#     def test_eligibility_doc_issues_score_deduction(self):
#         """Name mismatch + bank unlinked + dormant → AMBER/RED with deductions."""
#         with patch("src.engine.eligibility._load_schemes", return_value=ALL_SCHEMES):
#             r = client.post("/api/v1/eligibility", json={
#                 "scheme_id": "lakshmir_bhandar",
#                 "profile":   COMPLETE_PROFILE,
#                 "checks":    DOCUMENT_CHECKS_FAIL,
#             })
#         assert r.status_code == 200
#         body = r.json()
#         # Profile OK but docs bad → eligible_basic could be True but score low
#         assert body["score"] < 100
#         assert len(body["doc_issues"]) > 0

#     def test_eligibility_name_mismatch_in_issues(self):
#         """Aadhaar name != bank name → name_mismatch in doc_issues."""
#         with patch("src.engine.eligibility._load_schemes", return_value=ALL_SCHEMES):
#             r = client.post("/api/v1/eligibility", json={
#                 "scheme_id": "lakshmir_bhandar",
#                 "profile":   COMPLETE_PROFILE,
#                 "checks":    DOCUMENT_CHECKS_FAIL,
#             })
#         issue_types = [i["type"] for i in r.json()["doc_issues"]]
#         assert "name_mismatch" in issue_types

#     def test_eligibility_bank_unlinked_in_issues(self):
#         """aadhaar_bank_linked=False → bank_unlinked in doc_issues."""
#         with patch("src.engine.eligibility._load_schemes", return_value=ALL_SCHEMES):
#             r = client.post("/api/v1/eligibility", json={
#                 "scheme_id": "lakshmir_bhandar",
#                 "profile":   COMPLETE_PROFILE,
#                 "checks":    {**DOCUMENT_CHECKS_FAIL, "aadhaar_bank_linked": False},
#             })
#         issue_types = [i["type"] for i in r.json()["doc_issues"]]
#         assert "bank_unlinked" in issue_types

#     def test_eligibility_dormant_account_in_issues(self):
#         """Last transaction 10 months ago → dormant_account in issues."""
#         with patch("src.engine.eligibility._load_schemes", return_value=ALL_SCHEMES):
#             r = client.post("/api/v1/eligibility", json={
#                 "scheme_id": "lakshmir_bhandar",
#                 "profile":   COMPLETE_PROFILE,
#                 "checks":    {**DOCUMENT_CHECKS_PASS, "bank_last_transaction_months_ago": 10},
#             })
#         issue_types = [i["type"] for i in r.json()["doc_issues"]]
#         assert "dormant_account" in issue_types

#     def test_eligibility_missing_required_doc(self):
#         """voter_id in docs_missing → missing_document issue."""
#         with patch("src.engine.eligibility._load_schemes", return_value=ALL_SCHEMES):
#             r = client.post("/api/v1/eligibility", json={
#                 "scheme_id": "lakshmir_bhandar",
#                 "profile":   COMPLETE_PROFILE,
#                 "checks":    {**DOCUMENT_CHECKS_PASS,
#                               "docs_present": ["aadhaar"],
#                               "docs_missing": ["voter_id", "bank_passbook"]},
#             })
#         issue_types = [i["type"] for i in r.json()["doc_issues"]]
#         assert "missing_document" in issue_types

#     def test_eligibility_roadmap_populated(self):
#         """Issues present → roadmap has ordered steps."""
#         with patch("src.engine.eligibility._load_schemes", return_value=ALL_SCHEMES):
#             r = client.post("/api/v1/eligibility", json={
#                 "scheme_id": "lakshmir_bhandar",
#                 "profile":   COMPLETE_PROFILE,
#                 "checks":    DOCUMENT_CHECKS_FAIL,
#             })
#         roadmap = r.json()["roadmap"]
#         assert len(roadmap) > 0
#         assert "step" in roadmap[0]
#         assert "action" in roadmap[0]
#         assert "action_bn" in roadmap[0]
#         assert "location" in roadmap[0]
#         assert "done" in roadmap[0]

#     def test_eligibility_scheme_not_found(self):
#         """Unknown scheme_id → 404."""
#         with patch("src.engine.eligibility._load_schemes", return_value=ALL_SCHEMES):
#             r = client.post("/api/v1/eligibility", json={
#                 "scheme_id": "fake_scheme_xyz",
#                 "profile":   COMPLETE_PROFILE,
#                 "checks":    DOCUMENT_CHECKS_PASS,
#             })
#         assert r.status_code == 404

#     def test_eligibility_missing_scheme_id(self):
#         """Missing scheme_id → 422."""
#         r = client.post("/api/v1/eligibility", json={
#             "profile": COMPLETE_PROFILE,
#             "checks":  DOCUMENT_CHECKS_PASS,
#         })
#         assert r.status_code == 422

#     def test_eligibility_no_checks_defaults(self):
#         """No checks provided → uses defaults (no doc issues)."""
#         with patch("src.engine.eligibility._load_schemes", return_value=ALL_SCHEMES):
#             r = client.post("/api/v1/eligibility", json={
#                 "scheme_id": "lakshmir_bhandar",
#                 "profile":   COMPLETE_PROFILE,
#             })
#         assert r.status_code == 200

#     def test_eligibility_health_scheme_any_gender(self):
#         """Swasthya Sathi has gender=all → both male/female eligible."""
#         for gender in ("male", "female"):
#             with patch("src.engine.eligibility._load_schemes", return_value=ALL_SCHEMES):
#                 r = client.post("/api/v1/eligibility", json={
#                     "scheme_id": "swasthya_sathi",
#                     "profile":   {**COMPLETE_PROFILE, "gender": gender},
#                     "checks":    DOCUMENT_CHECKS_PASS,
#                 })
#             assert r.status_code == 200
#             assert r.json()["eligible_basic"] is True, f"Failed for gender={gender}"

#     def test_eligibility_save_result_when_logged_in(self):
#         """save=True + authenticated → saves result to DB."""
#         with patch("src.engine.eligibility._load_schemes",         return_value=ALL_SCHEMES), \
#              patch("src.repository.dynamo_repo.UserRepository.save_result", return_value=None) as mock_save:
#             r = client.post("/api/v1/eligibility",
#                 headers=_auth_header(),
#                 json={
#                     "scheme_id": "lakshmir_bhandar",
#                     "profile":   COMPLETE_PROFILE,
#                     "checks":    DOCUMENT_CHECKS_PASS,
#                     "save":      True,
#                 })
#         assert r.status_code == 200
#         mock_save.assert_called_once()

#     def test_eligibility_no_save_when_anonymous(self):
#         """save=True but not authenticated → result NOT saved."""
#         with patch("src.engine.eligibility._load_schemes",         return_value=ALL_SCHEMES), \
#              patch("src.repository.dynamo_repo.UserRepository.save_result", return_value=None) as mock_save:
#             r = client.post("/api/v1/eligibility", json={
#                 "scheme_id": "lakshmir_bhandar",
#                 "profile":   COMPLETE_PROFILE,
#                 "checks":    DOCUMENT_CHECKS_PASS,
#                 "save":      True,
#             })
#         assert r.status_code == 200
#         mock_save.assert_not_called()


# class TestGetScript:

#     def test_script_name_mismatch_bn(self):
#         """NAME_MISMATCH + lang=bn → Bengali script returned."""
#         r = client.get("/api/v1/script/NAME_MISMATCH?lang=bn&aadhaar_name=Priya+Das&bank_name=Priyya+Daas")
#         assert r.status_code == 200
#         body = r.json()
#         assert body["issue_code"] == "NAME_MISMATCH"
#         assert body["lang"]       == "bn"
#         assert len(body["script"]) > 10

#     def test_script_name_mismatch_en(self):
#         """NAME_MISMATCH + lang=en → English script."""
#         r = client.get("/api/v1/script/NAME_MISMATCH?lang=en&aadhaar_name=Priya&bank_name=Priyya")
#         assert r.status_code == 200
#         assert r.json()["lang"] == "en"

#     def test_script_aadhaar_unlinked(self):
#         """AADHAAR_UNLINKED → script for linking Aadhaar."""
#         r = client.get("/api/v1/script/AADHAAR_UNLINKED?lang=bn")
#         assert r.status_code == 200
#         assert r.json()["issue_code"] == "AADHAAR_UNLINKED"

#     def test_script_dormant_account(self):
#         """DORMANT_ACCOUNT → script for reactivating account."""
#         r = client.get("/api/v1/script/DORMANT_ACCOUNT?lang=en")
#         assert r.status_code == 200
#         assert "dormant" in r.json()["script"].lower() or "inactive" in r.json()["script"].lower()

#     def test_script_dob_mismatch(self):
#         """DOB_MISMATCH → script for date of birth correction."""
#         r = client.get("/api/v1/script/DOB_MISMATCH?lang=bn")
#         assert r.status_code == 200

#     def test_script_address_mismatch(self):
#         """ADDRESS_MISMATCH → script for address correction."""
#         r = client.get("/api/v1/script/ADDRESS_MISMATCH?lang=en")
#         assert r.status_code == 200

#     def test_script_unknown_issue_code(self):
#         """Unknown issue code → 404."""
#         r = client.get("/api/v1/script/FAKE_ISSUE?lang=en")
#         assert r.status_code == 404

#     def test_script_case_insensitive(self):
#         """Lowercase issue code → same result as uppercase."""
#         r_upper = client.get("/api/v1/script/NAME_MISMATCH?lang=en")
#         r_lower = client.get("/api/v1/script/name_mismatch?lang=en")
#         assert r_upper.status_code == r_lower.status_code == 200
#         assert r_upper.json()["script"] == r_lower.json()["script"]

#     def test_script_no_auth_required(self):
#         """Scripts are public — no auth needed."""
#         r = client.get("/api/v1/script/AADHAAR_UNLINKED")
#         assert r.status_code == 200


# class TestApplications:

#     def test_applications_authenticated(self):
#         """Logged-in user → returns their past results."""
#         stored_results = [
#             {"scheme_id": "lakshmir_bhandar", "score": 85, "band": "GREEN",
#              "eligible": True, "checked_at": int(time.time()) - 3600},
#             {"scheme_id": "swasthya_sathi",   "score": 95, "band": "GREEN",
#              "eligible": True, "checked_at": int(time.time()) - 7200},
#         ]
#         with patch("src.repository.dynamo_repo.UserRepository.get_results", return_value=stored_results):
#             r = client.get("/api/v1/applications", headers=_auth_header())
#         assert r.status_code == 200
#         body = r.json()
#         assert body["count"] == 2
#         assert len(body["applications"]) == 2

#     def test_applications_empty_history(self):
#         """No past checks → empty list."""
#         with patch("src.repository.dynamo_repo.UserRepository.get_results", return_value=[]):
#             r = client.get("/api/v1/applications", headers=_auth_header())
#         assert r.status_code == 200
#         assert r.json()["count"] == 0

#     def test_applications_unauthenticated(self):
#         """No auth → 401 (auth required for applications)."""
#         r = client.get("/api/v1/applications")
#         assert r.status_code in (401, 403)

#     def test_applications_limit_param(self):
#         """limit=1 → returns max 1 result."""
#         many = [{"scheme_id": f"scheme_{i}", "score": 80, "band": "GREEN",
#                  "eligible": True, "checked_at": int(time.time())} for i in range(5)]
#         with patch("src.repository.dynamo_repo.UserRepository.get_results", return_value=many[:1]):
#             r = client.get("/api/v1/applications?limit=1", headers=_auth_header())
#         assert r.status_code == 200
#         assert len(r.json()["applications"]) <= 1

#     def test_applications_limit_too_high(self):
#         """limit=999 → 422 (max 50)."""
#         r = client.get("/api/v1/applications?limit=999", headers=_auth_header())
#         assert r.status_code == 422

#     def test_applications_limit_zero(self):
#         """limit=0 → 422 (min 1)."""
#         r = client.get("/api/v1/applications?limit=0", headers=_auth_header())
#         assert r.status_code == 422