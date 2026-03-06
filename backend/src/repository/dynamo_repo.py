"""
src/repository/dynamo_repo.py
================================
DynamoDB repository layer for the REST API.

Tables used:
  wb_sahayak_schemes  — scheme_id (PK) — seeded by seed_pinecone.py
  wb_sahayak_users    — phone_number (PK)

SchemeRepository:
  get_by_id(scheme_id)         → single scheme dict
  get_all()                    → all schemes (Scan — acceptable for ~10 schemes)
  search(query, category, ...) → filtered list

UserRepository:
  get_profile(phone)           → profile dict or None
  save_profile(phone, data)    → None
  get_results(phone, limit)    → list of past results
"""

import logging
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

from src.config.settings import settings

logger = logging.getLogger(__name__)


def _get_table(name: str):
    dynamodb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
    return dynamodb.Table(name)


# ─────────────────────────────────────────────────────────────────────────────
# SCHEME REPOSITORY
# ─────────────────────────────────────────────────────────────────────────────

class SchemeRepository:

    @staticmethod
    def _tbl():
        return _get_table(settings.DYNAMO_TABLE_SCHEMES)

    @staticmethod
    def get_by_id(scheme_id: str) -> Optional[dict]:
        """Fetch single scheme by PK. Table has NO sort key — hash only."""
        try:
            resp = SchemeRepository._tbl().get_item(
                Key={"scheme_id": scheme_id}   # hash key only — no sk
            )
            return resp.get("Item")
        except ClientError as e:
            logger.error(f"SchemeRepository.get_by_id({scheme_id}): {e}")
            return None

    @staticmethod
    def get_all() -> list:
        """
        Scan entire schemes table.
        Safe for WB Sahayak — ~10 schemes, never going to be thousands.
        Returns list of raw DynamoDB items.
        """
        try:
            resp  = SchemeRepository._tbl().scan()
            items = resp.get("Items", [])

            # Handle DynamoDB pagination (unlikely for 10 schemes, but correct)
            while "LastEvaluatedKey" in resp:
                resp  = SchemeRepository._tbl().scan(
                    ExclusiveStartKey=resp["LastEvaluatedKey"]
                )
                items.extend(resp.get("Items", []))

            return items
        except ClientError as e:
            logger.error(f"SchemeRepository.get_all(): {e}")
            return []

    @staticmethod
    def search(
        query: str = "",
        category: str = "",
        page: int = 1,
        page_size: int = 8,
    ) -> dict:
        """
        Filter schemes from DynamoDB.
        Scans all then filters in-memory — correct for small dataset.
        """
        try:
            all_schemes = SchemeRepository.get_all()

            if not all_schemes:
                return {"schemes": [], "total": 0, "page": page, "pages": 1}

            # Filter by category (tag field)
            if category:
                all_schemes = [
                    s for s in all_schemes
                    if s.get("tag", "").upper() == category.upper()
                ]

            # Filter by query — search name, name_bn, tag, benefit
            if query:
                q = query.lower()
                all_schemes = [
                    s for s in all_schemes
                    if q in s.get("scheme_name", "").lower()
                    or q in s.get("scheme_name_bn", "").lower()
                    or q in s.get("tag", "").lower()
                    or q in s.get("benefit", "").lower()
                    or q in str(s.get("benefits", {}).get("note_en", "")).lower()
                ]

            total = len(all_schemes)
            start = (page - 1) * page_size
            page_items = all_schemes[start:start + page_size]

            return {
                "schemes": page_items,
                "total": total,
                "page": page,
                "pages": max(1, (total + page_size - 1) // page_size),
                "source": "dynamodb",
            }

        except Exception as e:
            logger.error(f"SchemeRepository.search(): {e}")
            return {"schemes": [], "total": 0, "page": page, "pages": 1}


# ─────────────────────────────────────────────────────────────────────────────
# USER REPOSITORY
# ─────────────────────────────────────────────────────────────────────────────

class UserRepository:

    @staticmethod
    def _tbl():
        return _get_table(settings.DYNAMO_TABLE_USERS)

    @staticmethod
    def get_profile(phone: str) -> Optional[dict]:
        """
        Fetch user record by phone. Returns profile fields or None.
        Profile fields stored flat in the user record:
          name, age, gender, caste, district,
          is_govt_employee, pays_income_tax, has_daughter,
          has_school_child, is_enrolled_in_school,
          is_unemployed, annual_income_bracket
        """
        try:
            resp = UserRepository._tbl().get_item(
                Key={"phone_number": phone}
            )
            item = resp.get("Item")
            if not item:
                return None

            # Extract only profile fields (not session/TTS fields)
            profile_fields = [
                "phone_number", "name", "age", "gender", "caste", "district",
                "is_govt_employee", "pays_income_tax", "has_daughter",
                "has_school_child", "is_enrolled_in_school",
                "is_unemployed", "annual_income_bracket",
            ]
            return {k: item[k] for k in profile_fields if k in item}

        except ClientError as e:
            logger.error(f"UserRepository.get_profile({phone}): {e}")
            return None

    @staticmethod
    def save_profile(phone: str, data: dict) -> None:
        """
        Merge profile fields into user record.
        Creates record if not exists (upsert via UpdateItem).
        """
        if not data:
            return

        try:
            # Build UpdateExpression dynamically from provided fields
            expr_parts  = []
            attr_names  = {}
            attr_values = {}

            for i, (key, value) in enumerate(data.items()):
                placeholder_name  = f"#f{i}"
                placeholder_value = f":v{i}"
                expr_parts.append(f"{placeholder_name} = {placeholder_value}")
                attr_names[placeholder_name]  = key
                attr_values[placeholder_value] = value

            if not expr_parts:
                return

            UserRepository._tbl().update_item(
                Key={"phone_number": phone},
                UpdateExpression="SET " + ", ".join(expr_parts),
                ExpressionAttributeNames=attr_names,
                ExpressionAttributeValues=attr_values,
            )

        except ClientError as e:
            logger.error(f"UserRepository.save_profile({phone}): {e}")

    @staticmethod
    def get_results(phone: str, limit: int = 10) -> list:
        """
        Fetch past eligibility check results for a user.
        Stored as JSON string in 'results' field of user record.
        """
        try:
            import json
            resp = UserRepository._tbl().get_item(
                Key={"phone_number": phone}
            )
            item = resp.get("Item")
            if not item:
                return []

            raw = item.get("results", "[]")
            results = json.loads(raw) if isinstance(raw, str) else raw
            return results[-limit:] if len(results) > limit else results

        except Exception as e:
            logger.error(f"UserRepository.get_results({phone}): {e}")
            return []