"""
src/services/scheme_service.py
Business logic for schemes: recommendations, search, eligibility.

Data format matches actual DynamoDB/JSON structure:
  - department  (not dept)
  - no description field → derived from benefits.note_en
  - no icon field        → derived from tag
  - no accent_color      → derived from tag
"""

import logging
import random
from typing import Optional

from src.repository.dynamo_repo import SchemeRepository, UserRepository
from src.config.settings import settings

logger = logging.getLogger(__name__)

# ── Tag → icon mapping (lucide-react icon names) ──────────────────────────────
TAG_ICON_MAP = {
    "WOMEN":      "Heart",
    "HEALTH":     "Activity",
    "GIRL_CHILD": "Star",
    "MARRIAGE":   "Gift",
    "YOUTH":      "Briefcase",
    "PENSION":    "Shield",
    "EDUCATION":  "BookOpen",
    "FARMER":     "Leaf",
    "DEFAULT":    "Award",
}

# ── Tag → accent color ─────────────────────────────────────────────────────────
TAG_COLOR_MAP = {
    "WOMEN":      "#E91E8C",
    "HEALTH":     "#0EA5E9",
    "GIRL_CHILD": "#8B5CF6",
    "MARRIAGE":   "#F59E0B",
    "YOUTH":      "#10B981",
    "PENSION":    "#6366F1",
    "EDUCATION":  "#3B82F6",
    "FARMER":     "#22C55E",
    "DEFAULT":    "#1A56DB",
}

FEATURED_SCHEME_IDS = [
    "lakshmir_bhandar",
    "swasthya_sathi",
    "kanyashree",
    "rupashree",
    "yuva_sathi",
    "samajik_suraksha",
]


def _scheme_card(s: dict) -> dict:
    """
    Normalize a raw scheme dict into a consistent card format.
    Handles missing fields (description, icon, accent_color, dept)
    that don't exist in the actual data.
    """
    tag = s.get("tag", "DEFAULT")

    # description → use benefits.note_en, fallback to benefit_display
    benefits    = s.get("benefits", {})
    description = (
        benefits.get("note_en", "")
        or s.get("benefit_display", "")
    )

    return {
        "scheme_id":      s.get("scheme_id", ""),
        "scheme_name":    s.get("scheme_name", ""),
        "scheme_name_bn": s.get("scheme_name_bn", ""),
        "scheme_name_hi": s.get("scheme_name_hi", ""),
        "tag":            tag,
        "benefit_display": s.get("benefit_display", ""),
        "department":     s.get("department", ""),   # actual field name
        "description":    description,               # derived
        "icon":           TAG_ICON_MAP.get(tag, TAG_ICON_MAP["DEFAULT"]),
        "accent_color":   TAG_COLOR_MAP.get(tag, TAG_COLOR_MAP["DEFAULT"]),
        "eligibility":    s.get("eligibility", {}),
        "documents":      s.get("documents", []),
        "apply_at":       s.get("apply_at", []),
        "benefits":       benefits,
    }


class SchemeService:

    # ── Search ────────────────────────────────────────────────────────────────

    @staticmethod
    def search_schemes(
        query: str = "",
        category: str = "",
        page: int = 1,
        page_size: int = 8,
        sort: str = "relevance",
    ) -> dict:
        result = SchemeRepository.search(query, category, page, page_size)

        if not result["schemes"]:
            result = SchemeService._search_from_json(query, category, page, page_size)

        schemes = [_scheme_card(s) for s in result["schemes"]]

        if sort == "name_asc":
            schemes = sorted(schemes, key=lambda s: s.get("scheme_name", ""))
        elif sort == "name_desc":
            schemes = sorted(schemes, key=lambda s: s.get("scheme_name", ""), reverse=True)

        result["schemes"] = schemes
        return result

    @staticmethod
    def _search_from_json(query: str, category: str, page: int, page_size: int) -> dict:
        try:
            import json
            with open(settings.SCHEMES_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            schemes = data.get("schemes", [])

            if query:
                q = query.lower()
                schemes = [
                    s for s in schemes
                    if q in s.get("scheme_name", "").lower()
                    or q in s.get("scheme_name_bn", "").lower()
                    or q in s.get("tag", "").lower()
                    or q in s.get("benefit_display", "").lower()
                    or q in s.get("benefits", {}).get("note_en", "").lower()
                ]

            if category:
                schemes = [s for s in schemes if s.get("tag", "") == category.upper()]

            total = len(schemes)
            start = (page - 1) * page_size
            return {
                "schemes": schemes[start:start + page_size],
                "total": total,
                "page": page,
                "pages": max(1, (total + page_size - 1) // page_size),
                "source": "json_fallback",
            }
        except Exception as e:
            logger.error(f"_search_from_json: {e}")
            return {"schemes": [], "total": 0, "page": 1, "pages": 1}

    # ── Single Scheme ─────────────────────────────────────────────────────────

    @staticmethod
    def get_scheme(scheme_id: str) -> Optional[dict]:
        """Return full scheme with eligibility, documents, benefits — not just card fields."""
        scheme = SchemeRepository.get_by_id(scheme_id)
        if not scheme:
            scheme = SchemeService._get_scheme_from_json(scheme_id)
        if not scheme:
            return None
        # Full detail response — include everything
        card = _scheme_card(scheme)
        card["eligibility"] = scheme.get("eligibility", {})
        card["documents"]   = scheme.get("documents", [])
        card["apply_at"]    = scheme.get("apply_at", [])
        card["benefits"]    = scheme.get("benefits", {})
        card["mismatch_checks"] = scheme.get("mismatch_checks", [])
        card["bank_conditions"] = scheme.get("bank_conditions", {})
        return card

    @staticmethod
    def _get_scheme_from_json(scheme_id: str) -> Optional[dict]:
        try:
            import json
            with open(settings.SCHEMES_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for s in data.get("schemes", []):
                if s.get("scheme_id") == scheme_id:
                    return s
            return None
        except Exception:
            return None

    # ── Recommendations ───────────────────────────────────────────────────────

    @staticmethod
    def get_recommendations(
        phone: Optional[str] = None,
        scheme_id: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 6,
    ) -> dict:
        profile = None
        if phone:
            profile = UserRepository.get_profile(phone)

        if profile and SchemeService._profile_is_complete(profile):
            return {
                "schemes": SchemeService._profile_based(profile, exclude=scheme_id, limit=limit),
                "mode": "profile",
                "personalised": True,
            }

        if scheme_id:
            related = SchemeService._context_based(scheme_id, limit=limit)
            if related:
                return {"schemes": related, "mode": "context", "personalised": False}

        if query:
            found = SchemeService._query_based(query, limit=limit)
            if found:
                return {"schemes": found, "mode": "query", "personalised": False}

        return {
            "schemes": SchemeService._featured(limit=limit),
            "mode": "featured",
            "personalised": False,
        }

    @staticmethod
    def _profile_is_complete(profile: dict) -> bool:
        return all(
            profile.get(f) not in (None, "", "unknown")
            for f in ("age", "gender", "caste")
        )

    @staticmethod
    def _profile_based(profile: dict, exclude: Optional[str], limit: int) -> list:
        try:
            age          = int(profile.get("age", 0))
            gender       = profile.get("gender", "").lower()
            is_govt      = profile.get("is_govt_employee", False)
            has_daughter = profile.get("has_daughter", False)
            is_student   = profile.get("is_enrolled_in_school", False)
            is_unemployed = profile.get("is_unemployed", False)

            all_schemes = SchemeService._load_all_from_dynamo()
            matches = []
            for scheme in all_schemes:
                sid = scheme.get("scheme_id", "")
                if sid == exclude:
                    continue

                el = scheme.get("eligibility", {})

                # Gender filter — "all" means no restriction
                scheme_gender = el.get("gender", "all")
                if scheme_gender and scheme_gender != "all" and gender:
                    if scheme_gender.lower() != gender:
                        continue

                # Age filter
                age_min = el.get("age_min") or 0
                age_max = el.get("age_max") or 999
                if age and age_min and age < age_min:
                    continue
                if age and age_max and age_max < 999 and age > age_max:
                    continue

                # Govt employee exclusion
                if el.get("not_govt_employee") and is_govt:
                    continue

                # Kanyashree: needs daughter or student
                if sid == "kanyashree" and not has_daughter and not is_student:
                    continue

                # Yuva Sathi: must be unemployed
                if sid == "yuva_sathi" and not is_unemployed:
                    continue

                matches.append(_scheme_card(scheme))

                if len(matches) >= limit:
                    break

            return matches if matches else SchemeService._featured(limit=limit)

        except Exception as e:
            logger.error(f"_profile_based: {e}")
            return SchemeService._featured(limit=limit)

    @staticmethod
    def _context_based(current_scheme_id: str, limit: int) -> list:
        try:
            all_schemes = SchemeService._load_all_from_dynamo()
            current = next((s for s in all_schemes if s.get("scheme_id") == current_scheme_id), None)
            if not current:
                return []

            current_tag  = current.get("tag", "").lower()
            current_dept = current.get("department", "").lower()

            related = []
            for s in all_schemes:
                # Strictly exclude the scheme being viewed
                if s.get("scheme_id") == current_scheme_id:
                    continue
                score = 0
                if s.get("tag", "").lower() == current_tag:
                    score += 2
                if s.get("department", "").lower() == current_dept:
                    score += 1
                if score > 0:
                    related.append((score, s))

            related.sort(key=lambda x: x[0], reverse=True)
            # Return cards — guaranteed to NOT include current_scheme_id
            return [_scheme_card(s) for _, s in related[:limit]]

        except Exception as e:
            logger.error(f"_context_based: {e}")
            return []

    @staticmethod
    def _query_based(query: str, limit: int) -> list:
        """Search all schemes in-memory by query text."""
        try:
            all_schemes = SchemeService._load_all_from_dynamo()
            q = query.lower()
            matched = [
                s for s in all_schemes
                if q in s.get("scheme_name", "").lower()
                or q in s.get("scheme_name_bn", "").lower()
                or q in s.get("tag", "").lower()
                or q in s.get("benefit_display", "").lower()
                or q in str(s.get("benefits", {}).get("note_en", "")).lower()
                or q in s.get("department", "").lower()
            ]
            return [_scheme_card(s) for s in matched[:limit]]
        except Exception as e:
            logger.error(f"_query_based: {e}")
            return []

    @staticmethod
    def get_all_schemes() -> list:
        """Public method — returns all schemes as normalized cards."""
        return [_scheme_card(s) for s in SchemeService._load_all_from_dynamo()]

    @staticmethod
    def _load_all_from_dynamo() -> list:
        """
        Fetch all schemes from DynamoDB. Primary data source.
        Falls back to JSON only if DynamoDB returns empty (e.g. first boot).
        """
        try:
            schemes = SchemeRepository.get_all()
            if schemes:
                return schemes
            logger.warning("DynamoDB returned 0 schemes — falling back to JSON")
        except Exception as e:
            logger.error(f"_load_all_from_dynamo DynamoDB failed: {e}")

        # Fallback: JSON (only if DynamoDB empty/down)
        try:
            import json
            from pathlib import Path
            json_path = Path(__file__).resolve().parents[2] / "src" / "data" / "schemes.json"
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f).get("schemes", [])
        except Exception as e:
            logger.error(f"_load_all_from_dynamo JSON fallback failed: {e}")
            return []

    @staticmethod
    def _featured(limit: int = 6) -> list:
        """
        Return random schemes from JSON.
        Called when no profile exists — shows fresh random schemes every time.
        """
        try:
            all_schemes = SchemeService._load_all_from_dynamo()
            if not all_schemes:
                return []

            # Prefer FEATURED_SCHEME_IDS order, shuffle for variety
            # Fall back to any scheme if featured ID not found
            id_map = {s["scheme_id"]: s for s in all_schemes}

            featured = []
            ids = FEATURED_SCHEME_IDS.copy()
            random.shuffle(ids)
            for sid in ids:
                s = id_map.get(sid)
                if s:
                    featured.append(_scheme_card(s))

            # If fewer than limit found in featured list, pad with remaining schemes
            if len(featured) < limit:
                remaining = [s for s in all_schemes if s["scheme_id"] not in FEATURED_SCHEME_IDS]
                random.shuffle(remaining)
                for s in remaining:
                    if len(featured) >= limit:
                        break
                    featured.append(_scheme_card(s))

            return featured[:limit]

        except Exception as e:
            logger.error(f"_featured: {e}")
            return []

    # ── Applications ──────────────────────────────────────────────────────────

    @staticmethod
    def get_applications(phone: str, limit: int = 10) -> list:
        return UserRepository.get_results(phone, limit=limit)