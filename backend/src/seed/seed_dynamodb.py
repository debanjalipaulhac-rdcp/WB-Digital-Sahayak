"""
seed/seed_dynamo.py
Seeds DynamoDB tables from data/schemes.json.
Run this ONCE before the app goes live, and again after any schemes.json update.

Usage:
    python -m src.seed.seed_dynamo                    # Full seed
    python -m src.seed.seed_dynamo --create-tables    # Create tables first then seed
    python -m src.seed.seed_dynamo --schemes-only     # Only seed scheme rules
    python -m src.seed.seed_dynamo --qa-only          # Only seed Q&A entries
    python -m src.seed.seed_dynamo --dry-run          # Print what would happen, no writes
"""

import json
import logging
import argparse
import sys
from pathlib import Path

# Ensure src/ is on path when running as script
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.storage.dynamo import (
    save_qa,
    save_scheme,
    batch_save_audio_chunks,
    create_tables_if_not_exist,
)
from src.storage.s3 import create_bucket_if_not_exists, get_audio_url

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

SCHEMES_JSON_PATH = Path(__file__).resolve().parents[1] / "data" / "schemes.json"

# ─────────────────────────────────────────────
# Counters for summary
# ─────────────────────────────────────────────
stats = {
    "schemes_written": 0,
    "qa_entries_written": 0,
    "audio_chunk_refs_written": 0,
    "errors": 0
}


def load_schemes_json() -> dict:
    """Load and parse schemes.json. Fail loudly if malformed."""
    with open(SCHEMES_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    logger.info(f"Loaded schemes.json — {len(data['schemes'])} schemes found")
    return data


def seed_schemes(schemes: list[dict], dry_run: bool = False):
    """
    Write each scheme's full rule object to DynamoDB TABLE_SCHEMES.
    We strip static_qa from the scheme before saving (QA goes to its own table).
    """
    logger.info(f"\n── Seeding {len(schemes)} schemes to DynamoDB ──")
    for scheme in schemes:
        scheme_id = scheme["scheme_id"]
        # Strip Q&A — that goes to scheme_qa table separately
        scheme_for_db = {k: v for k, v in scheme.items() if k != "static_qa"}

        if dry_run:
            logger.info(f"  [DRY RUN] Would write scheme: {scheme_id}")
            continue

        ok = save_scheme(scheme_for_db)
        if ok:
            stats["schemes_written"] += 1
            logger.info(f"  ✅ Scheme written: {scheme_id}")
        else:
            stats["errors"] += 1
            logger.error(f"  ❌ Failed to write scheme: {scheme_id}")


def seed_qa(schemes: list[dict], dry_run: bool = False):
    """
    For each scheme's static_qa list, write one DynamoDB entry per
    question variant × language combination.

    Table: wb_sahayak_scheme_qa
    PK: question_hash  SK: language_code
    """
    logger.info(f"\n── Seeding Q&A entries ──")

    languages = ["en-IN", "bn-IN", "hi-IN"]

    for scheme in schemes:
        scheme_id = scheme["scheme_id"]
        qa_list = scheme.get("static_qa", [])

        for qa in qa_list:
            qa_id = qa["qa_id"]
            question_variants = qa["question_variants"]
            answers = qa["answer"]      # dict: {lang: answer_text}
            audio_keys = qa["audio_key"]  # dict: {lang: s3_key}

            for lang in languages:
                answer_text = answers.get(lang)
                audio_s3_key = audio_keys.get(lang)

                if not answer_text:
                    logger.warning(f"  ⚠ No answer for {qa_id} in {lang} — skipping")
                    continue

                # Audio URL = resolved from S3 key
                audio_url = get_audio_url(audio_s3_key) if audio_s3_key else ""

                if dry_run:
                    logger.info(f"  [DRY RUN] Would write {len(question_variants)} variants for {qa_id} [{lang}]")
                    continue

                written = save_qa(
                    question_variants=question_variants,
                    language_code=lang,
                    answer_text=answer_text,
                    audio_url=audio_url,
                    scheme_id=scheme_id,
                    qa_id=qa_id
                )
                stats["qa_entries_written"] += written
                logger.info(f"  ✅ {written} Q&A variants written for {qa_id} [{lang}]")


def seed_common_audio_chunks(data: dict, dry_run: bool = False):
    """
    Write the common_audio_chunks list to DynamoDB audio_chunks table.
    These are pre-seeded S3 keys — actual audio files must be generated
    separately by precache_audio.py.

    This just registers the {chunk_text, language, s3_key} mapping in DynamoDB
    so the cache lookup system knows they exist.
    """
    logger.info(f"\n── Seeding common audio chunk references ──")

    chunks = data.get("common_audio_chunks", [])
    if not chunks:
        logger.warning("No common_audio_chunks found in schemes.json")
        return

    # Group by language for batch write
    by_language: dict[str, list] = {}
    for chunk in chunks:
        lang = chunk["language"]
        if lang not in by_language:
            by_language[lang] = []
        by_language[lang].append({
            "chunk_text": chunk["chunk"],
            "audio_url": get_audio_url(chunk["audio_key"])
        })

    for lang, items in by_language.items():
        if dry_run:
            logger.info(f"  [DRY RUN] Would write {len(items)} chunks for [{lang}]")
            continue
        written = batch_save_audio_chunks(items, lang)
        stats["audio_chunk_refs_written"] += written
        logger.info(f"  ✅ {written} audio chunk refs written [{lang}]")


def seed_script_qa(scripts: dict, dry_run: bool = False):
    """
    Seed the bank scripts (NAME_MISMATCH, DORMANT_ACCOUNT etc.)
    as Q&A entries so they're retrievable by the static lookup path.
    """
    logger.info(f"\n── Seeding script Q&A entries ──")
    languages = ["en-IN", "bn-IN", "hi-IN"]
    script_questions = {
        "NAME_MISMATCH": [
            "name mismatch script",
            "what to say at bank for name mismatch",
            "নাম মিলছে না ব্যাংকে কী বলব",
            "নাম মিসম্যাচ স্ক্রিপ্ট"
        ],
        "DORMANT_ACCOUNT": [
            "dormant account script",
            "how to reactivate dormant account",
            "ডরম্যান্ট অ্যাকাউন্ট ঠিক করার উপায়",
            "নিষ্ক্রিয় অ্যাকাউন্ট সক্রিয় করতে কী বলব"
        ],
        "AADHAAR_UNLINKED": [
            "aadhaar not linked script",
            "how to link aadhaar to bank",
            "আধার লিংক নেই ব্যাংকে কী বলব"
        ]
    }

    lang_script_key = {
        "en-IN": "script_en",
        "bn-IN": "script_bn",
        "hi-IN": "script_hi"
    }
    lang_audio_key = {
        "en-IN": "en-IN",
        "bn-IN": "bn-IN",
        "hi-IN": "hi-IN"
    }

    for code, questions in script_questions.items():
        script_data = scripts.get(code, {})
        if not script_data:
            continue
        for lang in languages:
            script_text = script_data.get(lang_script_key[lang], "")
            audio_s3_key = script_data.get("audio_key", {}).get(lang_audio_key[lang], "")
            audio_url = get_audio_url(audio_s3_key) if audio_s3_key else ""
            if not script_text:
                continue
            if dry_run:
                logger.info(f"  [DRY RUN] Would write script {code} [{lang}]")
                continue
            written = save_qa(
                question_variants=questions,
                language_code=lang,
                answer_text=script_text,
                audio_url=audio_url,
                scheme_id="system",
                qa_id=f"script_{code.lower()}"
            )
            stats["qa_entries_written"] += written
            logger.info(f"  ✅ Script {code} written [{lang}] — {written} variants")


def print_summary():
    logger.info("\n═══════════════════════════════════")
    logger.info("  SEED SUMMARY")
    logger.info("═══════════════════════════════════")
    logger.info(f"  Schemes written:          {stats['schemes_written']}")
    logger.info(f"  Q&A entries written:      {stats['qa_entries_written']}")
    logger.info(f"  Audio chunk refs written: {stats['audio_chunk_refs_written']}")
    logger.info(f"  Errors:                   {stats['errors']}")
    if stats["errors"] == 0:
        logger.info("\n  ✅ Seed complete. DynamoDB is ready.")
    else:
        logger.warning(f"\n  ⚠ Completed with {stats['errors']} errors. Check logs above.")


def main():
    parser = argparse.ArgumentParser(description="Seed DynamoDB from schemes.json")
    parser.add_argument("--create-tables", action="store_true", help="Create DynamoDB tables if they don't exist")
    parser.add_argument("--schemes-only",  action="store_true", help="Only seed scheme rules")
    parser.add_argument("--qa-only",       action="store_true", help="Only seed Q&A entries")
    parser.add_argument("--dry-run",       action="store_true", help="Print actions without writing")
    args = parser.parse_args()

    if args.dry_run:
        logger.info("MODE: DRY RUN — no writes will happen")

    # Step 0: Create tables if requested
    if args.create_tables and not args.dry_run:
        logger.info("\n── Creating DynamoDB tables ──")
        create_tables_if_not_exist()
        print("DB done!")
        create_bucket_if_not_exists()

    # Load data
    data = load_schemes_json()
    schemes = data["schemes"]
    scripts = data.get("scripts", {})

    # Seed based on flags
    if args.schemes_only:
        seed_schemes(schemes, args.dry_run)
    elif args.qa_only:
        seed_qa(schemes, args.dry_run)
        seed_script_qa(scripts, args.dry_run)
    else:
        # Full seed
        seed_schemes(schemes, args.dry_run)
        seed_qa(schemes, args.dry_run)
        seed_script_qa(scripts, args.dry_run)
        seed_common_audio_chunks(data, args.dry_run)

    print_summary()


if __name__ == "__main__":
    main()