"""
seed/seed_pinecone.py
Embeds ALL scheme data into Pinecone.

Two key changes from original:
  1. _build_scheme_text() — embeds EVERYTHING: eligibility, all docs with notes,
     all Q&A (all languages), benefits, application process, mismatch rules.
  2. _build_metadata() — stores FULL scheme as JSON in 'content' field.
     This is what Nova reads when answering the user.
     Previously Nova got 9 flat fields — now it gets the entire scheme.

Usage:
    python -m src.seed.seed_pinecone --delete-all
    python -m src.seed.seed_pinecone --dry-run
"""

import json
import logging
import argparse
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# import boto3
from pinecone import Pinecone, ServerlessSpec
from src.config.settings import settings
from src.config.aws_clients import get_bedrock_client
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

SCHEMES_JSON_PATH = Path(__file__).resolve().parents[1] / "data" / "schemes.json"

# PINECONE_API_KEY    = os.getenv("PINECONE_API_KEY", "")
# PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "wb-sahayak-schemes")
PINECONE_DIMENSION  = 1024
PINECONE_CLOUD      = "aws"
# PINECONE_REGION     = os.getenv("PINECONE_REGION", "us-east-1")
# BEDROCK_REGION      = os.getenv("BEDROCK_REGION", "us-east-1")
# TITAN_MODEL_ID      = "amazon.titan-embed-text-v2:0"


def _build_scheme_text(scheme: dict) -> str:
    """
    Full text blob for embedding — covers every question type:
    - 'what documents do I need' -> doc labels + notes + where to get
    - 'am I eligible, 30 female SC' -> full eligibility rules
    - 'how much money' -> full benefits breakdown
    - 'where to apply' -> application locations + steps
    - Any Q&A question variant -> all Q&A content all 3 languages
    """
    el   = scheme.get("eligibility", {})
    ben  = scheme.get("benefits", {})
    docs = scheme.get("documents", [])
    qa   = scheme.get("static_qa", [])
    locs = scheme.get("apply_at", [])

    parts = []

    # IDENTITY
    parts.append(f"Scheme: {scheme.get('scheme_name', '')}")
    parts.append(f"Bengali name: {scheme.get('scheme_name_bn', '')}")
    parts.append(f"Hindi name: {scheme.get('scheme_name_hi', '')}")
    parts.append(f"Department: {scheme.get('department', '')}")
    parts.append(f"Category: {scheme.get('tag', '')}")
    parts.append(f"Benefit summary: {scheme.get('benefit_display', '')}")

    # FULL BENEFITS
    parts.append("--- BENEFITS ---")
    parts.append(ben.get("note_en", ""))
    if ben.get("general_monthly"):
        parts.append(f"General category receives Rs {ben['general_monthly']} per month")
    if ben.get("sc_st_monthly"):
        parts.append(f"SC ST category receives Rs {ben['sc_st_monthly']} per month")
    if ben.get("cashless_limit"):
        parts.append(f"Cashless health cover Rs {ben['cashless_limit']} per year per family")
    if ben.get("annual_scholarship"):
        parts.append(f"Annual scholarship Rs {ben['annual_scholarship']}")
    if ben.get("marriage_grant"):
        parts.append(f"One time marriage grant Rs {ben['marriage_grant']}")
    if ben.get("mode"):
        parts.append(f"Payment mode: {ben['mode']}")

    # FULL ELIGIBILITY
    parts.append("--- ELIGIBILITY ---")
    gender = el.get("gender")
    parts.append(f"Gender required: {gender}" if gender else "Open to all genders")
    if el.get("age_min") and el.get("age_max"):
        parts.append(f"Age must be between {el['age_min']} and {el['age_max']} years")
    elif el.get("age_min"):
        parts.append(f"Minimum age {el['age_min']} years")
    parts.append(el.get("note_en", ""))
    parts.append(el.get("caste_note", ""))
    if el.get("not_govt_employee"):
        parts.append("Government employees are NOT eligible")
    if el.get("not_income_tax_payer"):
        parts.append("Income tax payers are NOT eligible")
    if el.get("is_student_required"):
        parts.append("Must be enrolled in school or college")
    if el.get("is_unmarried_required"):
        parts.append("Must be unmarried")
    if el.get("family_card_holder"):
        parts.append("Must have Ration Card or proof of residence")

    # DOCUMENTS — full detail every doc
    parts.append("--- REQUIRED DOCUMENTS ---")
    for doc in docs:
        label    = doc.get("label", "")
        label_bn = doc.get("label_bn", "")
        note_en  = doc.get("note_en", "")
        where_en = doc.get("where_to_get_en", "")
        is_req   = doc.get("required", False)
        status   = "REQUIRED" if is_req else "OPTIONAL"

        line = f"{status}: {label} ({label_bn})"
        if note_en:
            line += f" — {note_en}"
        if where_en:
            line += f" Get from: {where_en}"
        parts.append(line)

    # HOW TO APPLY
    parts.append("--- HOW TO APPLY ---")
    for loc in locs:
        parts.append(f"Step {loc.get('step', '')}: {loc.get('office', '')} ({loc.get('office_bn', '')})")

    # BANK REQUIREMENTS
    bank = scheme.get("bank_conditions", {})
    if bank:
        parts.append("--- BANK ACCOUNT REQUIREMENTS ---")
        if bank.get("aadhaar_linked_required"):
            parts.append("Aadhaar must be linked to bank account")
        if bank.get("dormant_check"):
            months = bank.get("dormant_threshold_months", 6)
            parts.append(f"Bank account must be active and used within last {months} months")

    # ALL Q&A ALL LANGUAGES — makes embedding match any question phrasing
    parts.append("--- QUESTIONS AND ANSWERS ---")
    for entry in qa:
        variants = entry.get("question_variants", [])
        answers  = entry.get("answer", {})
        parts.append(f"Question: {' | '.join(variants[:4])}")
        for lang, ans in answers.items():
            if ans:
                parts.append(f"Answer ({lang}): {ans}")

    # CROSS-SCHEME SUGGESTIONS
    for t in scheme.get("cross_scheme_triggers", []):
        parts.append(t.get("reason_en", ""))

    return "\n".join(filter(None, [p.strip() for p in parts]))


def _build_metadata(scheme: dict) -> dict:
    """
    Flat fields for Pinecone filtering + full 'content' JSON for Nova.
    Nova reads 'content' to answer any user question about this scheme.
    Pinecone limit: 40KB per vector. Full scheme JSON is ~3-5KB.
    """
    el = scheme.get("eligibility", {})

    # Full structured content Nova will read
    content = {
        "scheme_id":   scheme["scheme_id"],
        "scheme_name": scheme["scheme_name"],
        "benefit":     scheme.get("benefit_display", ""),
        "department":  scheme.get("department", ""),

        "eligibility": {
            "gender":            el.get("gender", "any"),
            "age_min":           el.get("age_min"),
            "age_max":           el.get("age_max"),
            "note":              el.get("note_en", ""),
            "caste_note":        el.get("caste_note", ""),
            "not_govt_employee": el.get("not_govt_employee", False),
            "not_income_tax":    el.get("not_income_tax_payer", False),
        },

        "benefits": scheme.get("benefits", {}),

        "documents": [
            {
                "label":        d.get("label", ""),
                "label_bn":     d.get("label_bn", ""),
                "required":     d.get("required", False),
                "note":         d.get("note_en", ""),
                "where_to_get": d.get("where_to_get_en", ""),
                "score_deduction": d.get("score_deduction_if_missing", 0),
            }
            for d in scheme.get("documents", [])
        ],

        "apply_at": [
            {"step": a.get("step"), "office": a.get("office", "")}
            for a in scheme.get("apply_at", [])
        ],

        "bank_conditions": scheme.get("bank_conditions", {}),

        "qa": [
            {
                "qa_id":     q.get("qa_id", ""),
                "questions": q.get("question_variants", []),
                "answer_en": q.get("answer", {}).get("en-IN", ""),
                "answer_bn": q.get("answer", {}).get("bn-IN", ""),
                "answer_hi": q.get("answer", {}).get("hi-IN", ""),
            }
            for q in scheme.get("static_qa", [])
        ],

        "related_schemes": [
            t.get("reason_en", "")
            for t in scheme.get("cross_scheme_triggers", [])
        ]
    }

    return {
        # Flat fields (for metadata filtering if needed later)
        "scheme_id":      scheme["scheme_id"],
        "scheme_name":    scheme["scheme_name"],
        "scheme_name_bn": scheme.get("scheme_name_bn", ""),
        "tag":            scheme.get("tag", ""),
        "benefit":        scheme.get("benefit_display", ""),
        "gender":         el.get("gender", "any") or "any",
        "age_min":        el.get("age_min", 0) or 0,
        "age_max":        el.get("age_max", 999) or 999,
        "state_resident": el.get("state_resident", True),

        # FULL CONTENT — this is what Nova reads to answer user questions
        "content": json.dumps(content, ensure_ascii=False)
    }


def _embed_text(bedrock_client, text: str) -> list[float]:
    body = json.dumps({
        "inputText": text,
        "dimensions": PINECONE_DIMENSION,
        "normalize": True
    })
    response = bedrock_client.invoke_model(
        modelId=settings.TITAN_EMBED_MODEL_ID,
        body=body
    )
    return json.loads(response["body"].read())["embedding"]


def get_or_create_index(pc: Pinecone):
    existing = [idx.name for idx in pc.list_indexes()]
    if settings.PINECONE_INDEX_NAME not in existing:
        logger.info(f"Creating index: {settings.PINECONE_INDEX_NAME}")
        pc.create_index(
            name=settings.PINECONE_INDEX_NAME,
            dimension=settings.PINECONE_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud=settings.PINECONE_CLOUD, region=settings.PINECONE_REGION)
        )
    else:
        logger.info(f"Index exists: {settings.PINECONE_INDEX_NAME}")
    return pc.Index(settings.PINECONE_INDEX_NAME)


def seed_vectors(dry_run: bool = False, delete_all: bool = False):
    with open(SCHEMES_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    schemes = data["schemes"]
    logger.info(f"Loaded {len(schemes)} schemes")

    if dry_run:
        for scheme in schemes:
            text     = _build_scheme_text(scheme)
            metadata = _build_metadata(scheme)
            logger.info(f"\n{'='*60}")
            logger.info(f"Scheme:       {scheme['scheme_id']}")
            logger.info(f"Embed words:  ~{len(text.split())}")
            logger.info(f"Content size: {len(metadata['content'])} chars")
            logger.info(f"Q&A entries:  {len(scheme.get('static_qa', []))}")
            logger.info(f"Documents:    {len(scheme.get('documents', []))}")
            logger.info(f"\nText preview:\n{text[:800]}\n")
        return

    # bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
    bedrock = get_bedrock_client()
    pc      = Pinecone(api_key=settings.PINECONE_API_KEY)
    index   = get_or_create_index(pc)

    if delete_all:
        logger.warning("Deleting all vectors...")
        index.delete(delete_all=True)
        logger.info("Cleared.")

    vectors = []
    for scheme in schemes:
        sid  = scheme["scheme_id"]
        text = _build_scheme_text(scheme)
        logger.info(f"Embedding: {sid} (~{len(text.split())} words)")
        try:
            emb  = _embed_text(bedrock, text)
            meta = _build_metadata(scheme)
            vectors.append({"id": sid, "values": emb, "metadata": meta})
            logger.info(f"  OK: {sid} | content={len(meta['content'])}B")
        except Exception as e:
            logger.error(f"  FAILED {sid}: {e}")

    if vectors:
        index.upsert(vectors=vectors)
        logger.info(f"\nUpserted {len(vectors)} vectors to '{settings.PINECONE_INDEX_NAME}'")
    else:
        logger.error("Nothing upserted")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",    action="store_true")
    parser.add_argument("--delete-all", action="store_true")
    args = parser.parse_args()
    if not settings.PINECONE_API_KEY and not args.dry_run:
        logger.error("PINECONE_API_KEY not set")
        sys.exit(1)
    seed_vectors(dry_run=args.dry_run, delete_all=args.delete_all)


if __name__ == "__main__":
    main()