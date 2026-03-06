"""
src/services/profile_service.py
================================
Business logic for user profile CRUD.
Used by profile_controller.py.
"""

import logging
from typing import Optional

from src.repository.dynamo_repo import UserRepository

logger = logging.getLogger(__name__)

REQUIRED_PROFILE_FIELDS = ("age", "gender", "caste")


class ProfileService:

    @staticmethod
    def get_profile(phone: str) -> Optional[dict]:
        return UserRepository.get_profile(phone)

    @staticmethod
    def save_profile(phone: str, data: dict) -> dict:
        """
        Validate and save profile fields.
        Returns {"success": True} or {"success": False, "errors": [...]}
        """
        errors = []

        if "age" in data:
            age = data["age"]
            if not isinstance(age, int) or not (5 < age < 120):
                errors.append("Age must be between 5 and 120")

        if "gender" in data:
            if data["gender"].lower() not in ("male", "female", "other"):
                errors.append("Gender must be male, female, or other")
            else:
                data["gender"] = data["gender"].lower()

        if "caste" in data:
            valid_castes = ("general", "sc", "st", "obc")
            if data["caste"].lower() not in valid_castes:
                errors.append(f"Caste must be one of: {', '.join(valid_castes)}")
            else:
                data["caste"] = data["caste"].lower()

        if errors:
            return {"success": False, "errors": errors}

        UserRepository.save_profile(phone, data)
        return {"success": True, "updated_fields": list(data.keys())}

    @staticmethod
    def _profile_is_complete(profile: dict) -> bool:
        return all(
            profile.get(f) not in (None, "", "unknown")
            for f in REQUIRED_PROFILE_FIELDS
        )