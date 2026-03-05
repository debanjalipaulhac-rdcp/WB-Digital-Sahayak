"""
src/static/scheme_lookup.py
Direct DynamoDB lookup for known scheme Q&A.
Zero Nova calls. Zero Pinecone calls.
Handles common questions like "what documents for lakshmir bhandar?"

Lookup strategy:
  1. Hash the incoming question (normalized)
  2. Check DynamoDB scheme_qa table
  3. Return answer + audio URL if found
  4. Return None if not found → caller routes to dynamic path
"""

import hashlib
import logging
from dataclasses import dataclass
from typing import Optional

from src.storage.dynamo import get_qa_by_hash

logger = logging.getLogger(__name__)


@dataclass
class StaticAnswer:
    answer_text: str
    audio_url:   str          # Pre-cached S3 URL, empty string if not cached
    scheme_id:   str
    qa_id:       str
    from_cache:  bool = True  # Always True for static lookup


def _hash_question(question: str) -> str:
    """
    Normalize and hash question for DynamoDB key lookup.
    MUST use identical normalization as seed/seed_dynamo.py save path.
    """
    normalized = question.strip().lower()
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def lookup(question: str, language_code: str) -> Optional[StaticAnswer]:
    """
    Look up a question in the static Q&A DynamoDB table.
    Returns StaticAnswer if found, None if not found.

    On None: caller must route to dynamic path (vector search + Nova Lite).

    Args:
        question:      Raw user question text (already in English or translated)
        language_code: "bn-IN" | "hi-IN" | "en-IN" — determines which answer to return
    """
    q_hash = _hash_question(question)

    item = get_qa_by_hash(q_hash, language_code)

    if not item:
        logger.info(f"Static lookup miss: '{question[:50]}' [{language_code}]")
        return None

    logger.info(
        f"Static lookup HIT: qa_id={item.get('qa_id')} "
        f"scheme={item.get('scheme_id')} [{language_code}]"
    )

    return StaticAnswer(
        answer_text=item.get("answer_text", ""),
        audio_url=item.get("audio_url", ""),
        scheme_id=item.get("scheme_id", ""),
        qa_id=item.get("qa_id", ""),
        from_cache=True
    )


def lookup_by_scheme_and_type(
    scheme_id: str,
    qa_type: str,
    language_code: str
) -> Optional[StaticAnswer]:
    """
    Alternative lookup by scheme_id + qa_type for when you know exactly
    what you're looking for (e.g. from eligibility engine output).

    qa_type: "documents" | "eligibility" | "benefit" | "apply_where"
    Maps to qa_id: e.g. "lb_documents", "lb_eligibility"

    Uses scheme_id prefix convention:
      lakshmir_bhandar → lb
      swasthya_sathi   → ss
      kanyashree       → ks
      rupashree        → rp
      yuva_sathi       → ys
      samajik_suraksha → ssy
    """
    prefix_map = {
        "lakshmir_bhandar":  "lb",
        "swasthya_sathi":    "ss",
        "kanyashree":        "ks",
        "rupashree":         "rp",
        "yuva_sathi":        "ys",
        "samajik_suraksha":  "ssy"
    }

    prefix = prefix_map.get(scheme_id)
    if not prefix:
        logger.warning(f"No prefix mapping for scheme_id: {scheme_id}")
        return None

    # Construct canonical question that was seeded
    canonical_questions = {
        "documents":   f"{scheme_id} documents required",
        "eligibility": f"who is eligible for {scheme_id.replace('_', ' ')}",
        "benefit":     f"how much money from {scheme_id.replace('_', ' ')}",
        "apply_where": f"where to apply for {scheme_id.replace('_', ' ')}"
    }

    question = canonical_questions.get(qa_type)
    if not question:
        logger.warning(f"Unknown qa_type: {qa_type}")
        return None

    return lookup(question, language_code)