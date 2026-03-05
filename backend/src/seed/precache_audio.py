"""
seed/precache_audio.py
Pre-generates audio for ALL static Q&A answers and common chunks.
Saves ,opus files to S3 and registers URLs in DynamoDB.

Run this ONCE after seed_dynamo.py.
Cost impact: pays Sarvam TTS once per entry, then cache serves forever.

Usage:
    python -m src.seed.precache_audio
    python -m src.seed.precache_audio --scheme lakshmir_bhandar   # One scheme only
    python -m src.seed.precache_audio --chunks-only               # Only common chunks
    python -m src.seed.precache_audio --dry-run                   # List what would be generated
    python -m src.seed.precache_audio --skip-existing             # Skip S3 keys that exist
"""

import json
import time
import logging
import argparse
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import requests
from src.storage.s3 import upload_audio, check_audio_exists, get_audio_url
from src.storage.dynamo import save_audio_chunk, save_qa

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

SCHEMES_JSON_PATH = Path(__file__).resolve().parents[1] / "data" / "schemes.json"
# If you see this → update to point to new files
# GREETINGS_PATH = Path(...) / "data" / "greetings.json"
# CHUNKS_PATH    = Path(...) / "data" / "common_chunks.json"
# SARVAM_API_KEY   = os.getenv("SARVAM_API_KEY", "")
# SARVAM_TTS_URL   = "https://api.sarvam.ai/text-to-speech"

# Sarvam voice IDs per language

#   Ritu, Priya, Neha, Pooja, Simran, Kavya, Ishita, Shreya,  Roopa, Amelia, Sophia, Anand, Tanya, Tarun, Sunny, Mani, Gokul, Vijay, Shruti, Suhani, Mohit, Kavitha, Rehan, Soham, Rupali

from src.voice.audio_converter import wav_to_ogg
VOICE_MAP = {
    "bn-IN": "kavitha",   # Bengali female voice
    "hi-IN": "suhani",     # Hindi female voice
    "en-IN": "shruti"       # English Indian accent
}

# Sarvam TTS rate limit: be conservative
RATE_LIMIT_DELAY_SEC = 0.5

stats = {
    "generated": 0,
    "skipped_existing": 0,
    "failed": 0
}

from src.config.sarvam_client import get_sarvam_client
def call_sarvam_tts(text: str, language_code: str) -> bytes | None:
    """
    Call Sarvam TTS API for given text + language.
    Returns raw audio bytes (,opus) or None on failure.
    """
    
    try:
        client = get_sarvam_client()
        voice = VOICE_MAP.get(language_code, "maya")
        print("Voice:", voice)
        res=client.text_to_speech.convert(
            text=text, 
            model="bulbul:v3",
            target_language_code=language_code, 
            speaker=voice, 
            # output_format="opus",
            pace=1.1,
            speech_sample_rate=16000
            )

        import base64
        audio_b64 = res.audios[0]
        wav_bytes= base64.b64decode(audio_b64)
        ogg_bytes = wav_to_ogg(wav_bytes)
        if not ogg_bytes:
            logger.warning("OGG conversion failed — saving raw WAV as fallback")
            return wav_bytes  # fallback

        return ogg_bytes

    except requests.RequestException as e:
        logger.error(f"Sarvam TTS call failed: {e}")
        return None
    except (KeyError, IndexError) as e:
        logger.error(f"Sarvam TTS unexpected response: {e}|message: {e.message}")
        return None


def generate_and_save(text: str, s3_key: str, language_code: str,
                      skip_existing: bool = False, dry_run: bool = False) -> str | None:
    """
    Generate TTS audio for text and save to S3.
    Returns S3 URL on success, None on failure.
    """
    if dry_run:
        logger.info(f"  [DRY RUN] Would generate: [{language_code}] '{text[:60]}' → {s3_key}")
        return get_audio_url(s3_key)

    if skip_existing and check_audio_exists(s3_key):
        logger.info(f"  ⏭ Skipping (exists): {s3_key}")
        stats["skipped_existing"] += 1
        return get_audio_url(s3_key)

    logger.info(f"  🔊 Generating [{language_code}]: '{text[:60]}'")
    audio_bytes = call_sarvam_tts(text, language_code)

    if not audio_bytes:
        stats["failed"] += 1
        return None

    url = upload_audio(audio_bytes, s3_key)
    
    if url:
        stats["generated"] += 1
        logger.info(f"     ✅ Saved to S3: {s3_key}")
    else:
        stats["failed"] += 1

    time.sleep(RATE_LIMIT_DELAY_SEC)
    return url


def precache_greetings(greetings: dict, skip_existing: bool, dry_run: bool):
    """Pre-generate greeting audio for all 3 languages."""
    logger.info("\n── Pre-caching greeting audio ──")
    for lang, greeting_data in greetings.items():
        text = greeting_data["text"]
        s3_key = greeting_data["audio_key"]
        url = generate_and_save(text, s3_key, lang, skip_existing, dry_run)
        if url and not dry_run:
            # Register in DynamoDB audio chunks table for system-wide availability
            save_audio_chunk(f"__greeting__{lang}", lang, url)


def precache_qa(schemes: list[dict], target_scheme: str | None,
                skip_existing: bool, dry_run: bool):
    """Pre-generate audio for all static Q&A answers."""
    logger.info("\n── Pre-caching Q&A audio ──")
    languages = ["en-IN", "bn-IN", "hi-IN"]

    for scheme in schemes:
        scheme_id = scheme["scheme_id"]
        if target_scheme and scheme_id != target_scheme:
            continue

        qa_list = scheme.get("static_qa", [])
        logger.info(f"\n  Scheme: {scheme_id} ({len(qa_list)} Q&A entries)")

        for qa in qa_list:
            qa_id = qa["qa_id"]
            answers = qa["answer"]
            audio_keys = qa["audio_key"]

            for lang in languages:
                answer_text = answers.get(lang)
                s3_key = audio_keys.get(lang)

                if not answer_text or not s3_key:
                    continue

                url = generate_and_save(answer_text, s3_key, lang, skip_existing, dry_run)

                # Update DynamoDB Q&A table with the generated audio URL
                if url and not dry_run:
                    save_qa(
                        question_variants=qa["question_variants"],
                        language_code=lang,
                        answer_text=answer_text,
                        audio_url=url,
                        scheme_id=scheme_id,
                        qa_id=qa_id
                    )


def precache_scripts(scripts: dict, skip_existing: bool, dry_run: bool):
    """Pre-generate audio for bank/office scripts."""
    logger.info("\n── Pre-caching script audio ──")
    lang_key_map = {
        "en-IN": "script_en",
        "bn-IN": "script_bn",
        "hi-IN": "script_hi"
    }
    count=0
    for code, script_data in scripts.items():
        logger.info(f"\n  Script: {code}")
        audio_keys = script_data.get("audio_key", {})

        for lang, script_key in lang_key_map.items():
            text = script_data.get(script_key, "")
            s3_key = audio_keys.get(lang, "")

            if not text or not s3_key:
                continue

            url = generate_and_save(text, s3_key, lang, skip_existing, dry_run)
            if url and not dry_run:
                save_audio_chunk(f"__script__{code}__{lang}", lang, url)
            count+=1
    logger.info(f"Pre-cached {count} scripts")


def precache_common_chunks(chunks: list[dict], skip_existing: bool, dry_run: bool):
    """Pre-generate audio for common reusable word/phrase chunks."""
    logger.info("\n── Pre-caching common audio chunks ──")

    for chunk in chunks:
        text = chunk["chunk"]
        lang = chunk["language"]
        s3_key = chunk["audio_key"]

        url = generate_and_save(text, s3_key, lang, skip_existing, dry_run)
        if url and not dry_run:
            save_audio_chunk(text, lang, url)


def print_summary():
    logger.info("\n═══════════════════════════════════")
    logger.info("  PRECACHE SUMMARY")
    logger.info("═══════════════════════════════════")
    logger.info(f"  Generated:         {stats['generated']}")
    logger.info(f"  Skipped (exists):  {stats['skipped_existing']}")
    logger.info(f"  Failed:            {stats['failed']}")

    if stats["failed"] == 0:
        logger.info("\n  ✅ All audio pre-cached successfully.")
    else:
        logger.warning(f"\n  ⚠ {stats['failed']} failures — re-run with --skip-existing to retry only failures")


def main():
    parser = argparse.ArgumentParser(description="Pre-generate TTS audio to S3")
    parser.add_argument("--scheme",         type=str,  default=None,  help="Only precache a specific scheme_id")
    parser.add_argument("--chunks-only",    action="store_true",       help="Only precache common chunks")
    parser.add_argument("--skip-existing",  action="store_true",       help="Skip files already in S3")
    parser.add_argument("--dry-run",        action="store_true",       help="List actions, no API calls")
    args = parser.parse_args()

    # if not SARVAM_API_KEY and not args.dry_run:
    #     logger.error("SARVAM_API_KEY not set. Cannot generate audio.")
    #     sys.exit(1)

    with open(SCHEMES_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    schemes  = data["schemes"]
    scripts  = data.get("scripts", {})
    greetings = data.get("greetings", {})
    chunks   = data.get("common_audio_chunks", [])

    if args.chunks_only:
        precache_common_chunks(chunks, args.skip_existing, args.dry_run)
    else:
        precache_greetings(greetings, args.skip_existing, args.dry_run)
        precache_qa(schemes, args.scheme, args.skip_existing, args.dry_run)
        precache_scripts(scripts, args.skip_existing, args.dry_run)
        precache_common_chunks(chunks, args.skip_existing, args.dry_run)

    print_summary()


if __name__ == "__main__":
    main()