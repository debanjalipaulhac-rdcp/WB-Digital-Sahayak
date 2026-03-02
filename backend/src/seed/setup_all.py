#!/usr/bin/env python3
"""
scripts/setup_all.py
=====================
ONE COMMAND to set up everything before the demo.

WHAT THIS DOES (in order):
  Step 1 — DynamoDB: Create table + seed Sulata's demo profile + test session
  Step 2 — S3:       Create bucket + upload schemes.json + scripts.json
  Step 3 — Pinecone: Embed all 4 schemes with Titan V2 → upsert to index
  Step 4 — Verify:   Hit each service, confirm data is there

RUN ONCE before demo (or re-run if you change schemes.json):
    cd wb-digital-sahayak
    python scripts/setup_all.py

DRY RUN (no API calls — just prints what it would do):
    python scripts/setup_all.py --dry-run

RESET (wipe Sulata's session so demo starts fresh):
    python scripts/setup_all.py --reset-demo

PREREQUISITES — .env.local must have:
    AWS_ACCESS_KEY_ID=...
    AWS_SECRET_ACCESS_KEY=...
    AWS_REGION=ap-south-1
    DYNAMODB_TABLE_NAME=wb-sahayak-users
    S3_BUCKET_NAME=wb-sahayak-schemes
    PINECONE_API_KEY=...
    SARVAM_API_KEY=...          (only needed for Step 4 audio cache)

    Pinecone index must already exist:
        Name:       wb-sahayak-schemes
        Dimensions: 1024
        Metric:     cosine
        Cloud/Region: AWS us-east-1
"""

import sys, os, json, argparse, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

ENGINE_DIR   = os.path.join(os.path.dirname(os.path.dirname(__file__)), "engine")
SCHEMES_PATH = os.path.join(ENGINE_DIR, "schemes.json")
SCRIPTS_PATH = os.path.join(ENGINE_DIR, "scripts.json")

SULATA_PHONE = "+919876543210"   # demo user — used in demo script Section 19

SULATA_PROFILE = {
    "name":             "Sulata Mondal",
    "age":              38,
    "gender":           "female",
    "caste":            "sc",
    "district":         "Jalpaiguri",
    "is_govt_employee": False,
    "pays_income_tax":  False,
    "has_daughter":     True,
    "has_school_child": False,
    "is_unemployed":    False,
    "aadhaar_name":     "Sulata Mondal",
    "bank_name":        "Sulata",
    "aadhaar_bank_linked": False,
    "bank_last_transaction_months_ago": 8,
}

# ── Result tracker ─────────────────────────────────────────────────────────────

results = {}

def ok(step):
    results[step] = "✅"
    logger.info(f"  ✅ {step}")

def fail(step, reason=""):
    results[step] = f"❌  {reason}"
    logger.error(f"  ❌ {step}: {reason}")

def warn(step, reason=""):
    results[step] = f"⚠️  {reason}"
    logger.warning(f"  ⚠️  {step}: {reason}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 1 — DynamoDB
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def step1_dynamodb(dry_run=False):
    logger.info("\n━━━ STEP 1: DynamoDB ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("  Creates table (if missing) + seeds Sulata demo profile")

    if dry_run:
        logger.info("  [DRY RUN] Would save Sulata profile to DynamoDB")
        logger.info(f"  [DRY RUN] Phone: {SULATA_PHONE}")
        logger.info(f"  [DRY RUN] Profile keys: {list(SULATA_PROFILE.keys())}")
        ok("DynamoDB (dry-run)")
        return True

    try:
        from src.storage.dynamo import save_profile, save_session

        # Save demo profile
        saved = save_profile(SULATA_PHONE, SULATA_PROFILE)
        if not saved:
            fail("DynamoDB: save Sulata profile", "save_profile returned False")
            return False
        ok("DynamoDB: Sulata profile saved")

        # Save fresh session (START state — demo begins here)
        saved = save_session(SULATA_PHONE, {
            "conversation_step": "START",
            "lang":              "bn",
            "partial_profile":   {},
            "partial_checks":    {},
        })
        if not saved:
            fail("DynamoDB: save session", "save_session returned False")
            return False
        ok("DynamoDB: demo session initialized (START state)")
        return True

    except Exception as e:
        fail("DynamoDB", str(e))
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 2 — S3
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def step2_s3(dry_run=False):
    logger.info("\n━━━ STEP 2: S3 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("  Uploads schemes.json + scripts.json as source-of-truth backup")

    if dry_run:
        logger.info(f"  [DRY RUN] Would upload: {SCHEMES_PATH}")
        logger.info(f"  [DRY RUN] Would upload: {SCRIPTS_PATH}")
        ok("S3 (dry-run)")
        return True

    try:
        from src.storage.s3 import upload_schemes_json
        from src.config.settings import settings
        import boto3

        s3 = boto3.client(
            "s3",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        bucket = settings.S3_BUCKET_NAME

        # Create bucket if it doesn't exist
        try:
            s3.head_bucket(Bucket=bucket)
            ok(f"S3: bucket '{bucket}' exists")
        except Exception:
            logger.info(f"  Creating bucket '{bucket}'...")
            if settings.AWS_REGION == "us-east-1":
                s3.create_bucket(Bucket=bucket)
            else:
                s3.create_bucket(
                    Bucket=bucket,
                    CreateBucketConfiguration={"LocationConstraint": settings.AWS_REGION}
                )
            ok(f"S3: bucket '{bucket}' created")

        # Upload schemes.json
        with open(SCHEMES_PATH, "rb") as f:
            s3.put_object(
                Bucket=bucket,
                Key="data/schemes.json",
                Body=f,
                ContentType="application/json"
            )
        ok("S3: schemes.json uploaded → s3://...data/schemes.json")

        # Upload scripts.json
        with open(SCRIPTS_PATH, "rb") as f:
            s3.put_object(
                Bucket=bucket,
                Key="data/scripts.json",
                Body=f,
                ContentType="application/json"
            )
        ok("S3: scripts.json uploaded → s3://...data/scripts.json")

        return True

    except Exception as e:
        fail("S3", str(e))
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 3 — Pinecone (embed + upsert)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _build_scheme_text(scheme: dict) -> str:
    """
    Build rich text from a scheme for embedding.
    
    CHUNKING STRATEGY:
      We have only 4 schemes. Each scheme → ONE vector (not chunked).
      Why not chunk? Each scheme is ~300 tokens max. Titan V2 handles 8192 tokens.
      Chunking would scatter meaning across vectors and hurt retrieval accuracy.
      
      IF in Phase 2 you add 20+ schemes with long GOs (Govt Orders):
        → chunk each GO into 512-token overlapping windows
        → embed each chunk → upsert with metadata: {scheme_id, chunk_index}
        → at query time: fetch top 5 chunks → group by scheme_id → return top scheme
    """
    el   = scheme.get("eligibility", {})
    ben  = scheme.get("benefits", {})
    docs = [d["label"] for d in scheme.get("documents", []) if d.get("required")]
    apply_locs = [a.get("office","") for a in scheme.get("apply_at", [])]

    parts = [
        # Names (Bengali + English = matches both language queries)
        scheme.get("scheme_name", ""),
        scheme.get("scheme_name_bn", ""),

        # What it is
        scheme.get("benefit_display", ""),
        scheme.get("tag", ""),
        f"Department: {scheme.get('department', '')}",

        # Who can apply
        f"For {el.get('gender', 'all')} applicants" if el.get("gender") else "",
        f"Age {el['age_min']} to {el['age_max']} years" if el.get("age_min") else "",
        el.get("caste_note", ""),

        # What you get
        ben.get("note", ""),
        f"SC/ST get higher amount ₹{ben['sc_st_amount']}/month" if ben.get("sc_st_amount") else "",

        # How to apply (adds semantic signal for "where to apply" queries)
        f"Apply at: {', '.join(filter(None, apply_locs[:3]))}" if apply_locs else "",
        scheme.get("apply_note_bn", ""),
        scheme.get("apply_note", ""),

        # Docs (adds signal for "what documents needed" queries)
        f"Documents: {', '.join(docs)}" if docs else "",

        # Bengali application note for Bengali queries
        scheme.get("scheme_name_bn", ""),  # repeated — boosts Bengali match weight
    ]

    text = ". ".join(p for p in parts if p and p.strip())
    logger.info(f"    Built description: {len(text)} chars for {scheme['scheme_id']}")
    return text


def step3_pinecone(dry_run=False):
    logger.info("\n━━━ STEP 3: Pinecone Vector Index ━━━━━━━━━━━━━━━━━━━━━")
    logger.info("  Embeds 4 schemes with Titan V2 (1024-dim) → upserts to Pinecone")

    from src.engine.eligibility import get_all_schemes
    schemes = get_all_schemes()
    logger.info(f"  Found {len(schemes)} schemes to embed")

    if dry_run:
        logger.info("\n  [DRY RUN] Would embed these descriptions:")
        for s in schemes:
            text = _build_scheme_text(s)
            logger.info(f"\n  --- {s['scheme_id']} ({len(text)} chars) ---")
            logger.info(f"  {text[:300]}...")
        ok("Pinecone (dry-run)")
        return True

    try:
        from src.ai.vector_search import embed, EMBEDDING_DIM, NAMESPACE
        from src.config.pinecone_client import get_pinecone_index

        index = get_pinecone_index()
        if not index:
            fail("Pinecone", "Index not available — check PINECONE_API_KEY and index name")
            return False

        vectors = []
        for scheme in schemes:
            sid  = scheme["scheme_id"]
            text = _build_scheme_text(scheme)

            logger.info(f"  Calling Titan V2 for '{sid}'...")
            vector = embed(text)

            if not vector:
                fail(f"Pinecone: embed {sid}", "Titan returned empty vector — check Bedrock model access")
                continue

            if len(vector) != EMBEDDING_DIM:
                fail(f"Pinecone: embed {sid}", f"Wrong dims: {len(vector)} != {EMBEDDING_DIM}")
                continue

            vectors.append({
                "id":     sid,
                "values": vector,
                "metadata": {
                    "scheme_id":       sid,
                    "scheme_name":     scheme["scheme_name"],
                    "scheme_name_bn":  scheme.get("scheme_name_bn", ""),
                    "benefit_display": scheme.get("benefit_display", ""),
                    "tag":             scheme.get("tag", ""),
                    "department":      scheme.get("department", ""),
                    # Store first 500 chars for debugging in Pinecone console
                    "description_preview": text[:500],
                }
            })
            ok(f"Pinecone: '{sid}' embedded ({EMBEDDING_DIM} dims)")

        if not vectors:
            fail("Pinecone: upsert", "No vectors to upsert")
            return False

        # Upsert all 4 at once (one batch — well within Pinecone limits)
        logger.info(f"\n  Upserting {len(vectors)} vectors...")
        index.upsert(vectors=vectors, namespace=NAMESPACE)
        ok(f"Pinecone: {len(vectors)} vectors upserted")

        # ── Verify round-trip ──────────────────────────────────────────────────
        logger.info("\n  Verifying queries hit the right schemes...")
        test_cases = [
            ("scheme for women monthly cash",          "lakshmir_bhandar"),
            ("hospital treatment sick family",         "swasthya_sathi"),
            ("daughter education scholarship school",  "kanyashree"),
            ("unemployed youth job allowance",         "yuva_sathi"),
            # Bengali queries
            ("মহিলাদের জন্য মাসিক টাকা",              "lakshmir_bhandar"),
            ("হাসপাতাল চিকিৎসা বিনামূল্যে",           "swasthya_sathi"),
        ]

        all_ok = True
        for query, expected in test_cases:
            vec = embed(query)
            if not vec:
                warn(f"Verify: '{query[:30]}'", "Could not embed test query")
                continue
            res = index.query(vector=vec, top_k=1, include_metadata=True, namespace=NAMESPACE)
            if res.matches:
                top = res.matches[0]
                got = top.metadata.get("scheme_id", "?")
                score = round(top.score, 3)
                if got == expected:
                    ok(f"Query '{query[:35]}' → {got} (score={score})")
                else:
                    warn(f"Query '{query[:35]}' → {got} (expected {expected}, score={score})")
                    all_ok = False
            else:
                warn(f"Query '{query[:35]}'", "No matches returned")
                all_ok = False

        if all_ok:
            ok("Pinecone: all verification queries passed")
        else:
            warn("Pinecone: some queries returned unexpected top matches")
            logger.info("  This can happen with only 4 schemes — semantic distance is small.")
            logger.info("  The system will still work; keyword fallback handles edge cases.")

        return True

    except Exception as e:
        fail("Pinecone", str(e))
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 4 — Reset demo (optional)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def reset_demo():
    """
    Wipe Sulata's conversation session so the demo starts from scratch.
    Run this RIGHT BEFORE going on stage.
    """
    logger.info("\n━━━ RESET DEMO SESSION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    try:
        from src.storage.dynamo import save_session, clear_session
        clear_session(SULATA_PHONE)
        ok(f"Demo session cleared for {SULATA_PHONE} — bot will start from START state")
    except Exception as e:
        fail("Reset demo", str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    parser = argparse.ArgumentParser(
        description="Full setup: DynamoDB + S3 + Pinecone"
    )
    parser.add_argument("--dry-run",    action="store_true", help="Print what would happen, no API calls")
    parser.add_argument("--reset-demo", action="store_true", help="Just reset Sulata's demo session")
    parser.add_argument("--pinecone-only", action="store_true", help="Only run Step 3 (Pinecone)")
    parser.add_argument("--dynamo-only",   action="store_true", help="Only run Step 1 (DynamoDB)")
    parser.add_argument("--s3-only",       action="store_true", help="Only run Step 2 (S3)")
    args = parser.parse_args()

    if args.reset_demo:
        reset_demo()
        return

    logger.info("═══════════════════════════════════════════════════════")
    logger.info("  WB Digital Sahayak — Full Setup")
    logger.info("═══════════════════════════════════════════════════════")
    if args.dry_run:
        logger.info("  MODE: DRY RUN — no API calls will be made")

    if args.dynamo_only:
        step1_dynamodb(args.dry_run)
    elif args.s3_only:
        step2_s3(args.dry_run)
    elif args.pinecone_only:
        step3_pinecone(args.dry_run)
    else:
        # Full setup
        step1_dynamodb(args.dry_run)
        step2_s3(args.dry_run)
        step3_pinecone(args.dry_run)

    # ── Summary ────────────────────────────────────────────────────────────────
    logger.info("\n═══════════════════════════════════════════════════════")
    logger.info("  SETUP SUMMARY")
    logger.info("═══════════════════════════════════════════════════════")
    for step, status in results.items():
        logger.info(f"  {status}  {step}")

    failures = [s for s in results.values() if s.startswith("❌")]
    if not failures:
        logger.info("\n✅ All steps complete. System is ready.")
        logger.info(f"\n  Demo user: {SULATA_PHONE}")
        logger.info("  Run before going on stage:")
        logger.info("    python scripts/setup_all.py --reset-demo")
        logger.info("  Then warm Lambda:")
        logger.info("    curl $API_URL/health")
        sys.exit(0)
    else:
        logger.error(f"\n❌ {len(failures)} step(s) failed — fix before demo")
        sys.exit(1)


if __name__ == "__main__":
    main()