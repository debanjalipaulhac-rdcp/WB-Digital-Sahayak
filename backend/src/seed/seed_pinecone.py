"""
seed/seed_pinecone.py
Generates embeddings for each scheme and upserts to Pinecone.
One vector per scheme — schemes are short enough to fit in one embedding.
Uses Amazon Titan Text Embeddings V2 via Bedrock.

Usage:
    python -m src.seed.seed_pinecone
    python -m src.seed.seed_pinecone --dry-run
    python -m src.seed.seed_pinecone --delete-all   # Wipe index and re-seed
"""

import json
import logging
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pinecone import Pinecone, ServerlessSpec
from src.config.settings import settings
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

SCHEMES_JSON_PATH = Path(__file__).resolve().parents[1] / "data" / "schemes.json"

# PINECONE_API_KEY    = os.getenv("PINECONE_API_KEY", "")
# PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "wb-sahayak-schemes")
# PINECONE_CLOUD      = "aws"
# PINECONE_REGION     = os.getenv("PINECONE_REGION", "us-east-1")

# AWS_REGION          = os.getenv("AWS_REGION", "ap-south-1")

TITAN_MODEL_ID      = "amazon.titan-embed-text-v2:0"
PINECONE_DIMENSION  = 1024   # Titan Text Embeddings V2 output dimension

def _build_scheme_text(scheme: dict) -> str:
    """
    Serialize a scheme into a single text blob for embedding.
    Include all semantically useful fields.
    Repeat Bengali name to boost multilingual matching.

    STRATEGY: Each scheme = ONE vector. Schemes are ~300 tokens max.
    Titan V2 handles 8192 tokens. No chunking needed.
    """
    el = scheme.get("eligibility", {})
    ben = scheme.get("benefits", {})
    docs = [d["label"] for d in scheme.get("documents", []) if d.get("required")]
    apply_locs = [a.get("office", "") for a in scheme.get("apply_at", [])]

    # Collect Q&A texts for richer semantic coverage
    qa_texts = []
    for qa in scheme.get("static_qa", []):
        qa_texts.append(qa["answer"].get("en-IN", ""))

    parts = [
        # Names in all 3 languages → matches multilingual queries
        scheme.get("scheme_name", ""),
        scheme.get("scheme_name_bn", ""),
        scheme.get("scheme_name_hi", ""),
        scheme.get("department", ""),
        f"Tag: {scheme.get('tag', '')}",
        f"Benefit: {scheme.get('benefit_display', '')}",
        ben.get("note_en", ""),

        # Eligibility signal
        f"For {el.get('gender', 'all')} applicants" if el.get("gender") else "For all genders",
        f"Age {el['age_min']} to {el.get('age_max', 'no limit')} years" if el.get("age_min") else "",
        el.get("note_en", ""),
        el.get("caste_note", ""),

        # Documents signal
        f"Required documents: {', '.join(docs)}" if docs else "",

        # Application location
        f"Apply at: {', '.join(filter(None, apply_locs))}" if apply_locs else "",

        # Bengali scheme name again (boosts weight for Bengali queries)
        scheme.get("scheme_name_bn", ""),

        # Q&A content for semantic richness
        " ".join(qa_texts[:2])   # max 2 Q&A answers to keep token count controlled
    ]

    return ". ".join(filter(None, [p.strip() for p in parts]))

from src.config.aws_clients import get_bedrock_client
def _embed_text( text: str) -> list[float]:
    """
    Call Amazon Titan Text Embeddings V2 and return the embedding vector.
    Returns list of 1024 floats.
    """
    body = json.dumps({
        "inputText": text,
        "dimensions": PINECONE_DIMENSION,
        "normalize": True
    })
    client =get_bedrock_client()
    response = client.invoke_model(
        modelId=TITAN_MODEL_ID,
        body=body,
    )
    result = json.loads(response["body"].read())
    return result["embedding"]


def _build_metadata(scheme: dict) -> dict:
    """
    Build Pinecone vector metadata for a scheme.
    Metadata is used for filtering + display in search results.
    Keep it flat and small — Pinecone metadata limit is 40KB per vector.
    """
    el = scheme.get("eligibility", {})

    return {
        "scheme_id":      scheme["scheme_id"],
        "scheme_name":    scheme["scheme_name"],
        "scheme_name_bn": scheme.get("scheme_name_bn", ""),
        "tag":            scheme.get("tag", ""),
        "benefit":        scheme.get("benefit_display", ""),
        "gender":         el.get("gender", "any"),
        "age_min":        el.get("age_min", 0),
        "age_max":        el.get("age_max", 999),
        "state_resident": el.get("state_resident", True),
    }


def get_or_create_index(pc: Pinecone) -> object:
    """
    Get Pinecone index or create it if it doesn't exist.
    Uses Serverless spec (no pods to manage).
    """
    existing = [idx.name for idx in pc.list_indexes()]
    if settings.PINECONE_INDEX_NAME not in existing:
        logger.info(f"Creating Pinecone index: {settings.PINECONE_INDEX_NAME}")
        pc.create_index(
            name=settings.PINECONE_INDEX_NAME,
            dimension=PINECONE_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud=settings.PINECONE_CLOUD, region=settings.PINECONE_REGION)
        )
        logger.info(f"Index created: {settings.PINECONE_INDEX_NAME}")
    else:
        logger.info(f"Index already exists: {settings.PINECONE_INDEX_NAME}")
    return pc.Index(settings.PINECONE_INDEX_NAME)


def seed_vectors(dry_run: bool = False, delete_all: bool = False):
    """Main seed function."""
    # Load schemes
    with open(SCHEMES_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    schemes = data["schemes"]
    logger.info(f"Loaded {len(schemes)} schemes from schemes.json")

    if dry_run:
        logger.info("DRY RUN — showing text blobs that would be embedded:\n")
        for scheme in schemes:
            text = _build_scheme_text(scheme)
            logger.info(f"\n{'─'*50}")
            logger.info(f"Scheme:  {scheme['scheme_id']}")
            logger.info(f"Tokens:  ~{len(text.split())} words")
            logger.info(f"Text:\n{text[:400]}...")
        return

    # Init Bedrock
    # bedrock = boto3.client("bedrock-runtime", region_name=settings.AWS_REGION)

    # Init Pinecone
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    index = get_or_create_index(pc)

    if delete_all:
        logger.warning("Deleting all vectors from index...")
        index.delete(delete_all=True)
        logger.info("Index cleared.")

    # Embed and upsert
    vectors = []
    for scheme in schemes:
        scheme_id = scheme["scheme_id"]
        text = _build_scheme_text(scheme)
        logger.info(f"Embedding: {scheme_id} (~{len(text.split())} words)")

        try:
            embedding = _embed_text( text)
            metadata = _build_metadata(scheme)
            print(metadata)
            vectors.append({
                "id": scheme_id,
                "values": embedding,
                "metadata": metadata
            })
            logger.info(f"  ✅ Embedded: {scheme_id}")
        except Exception as e:
            logger.error(f"  ❌ Embedding failed for {scheme_id}: {e}")

    # Batch upsert to Pinecone
    if vectors:
        index.upsert(vectors=vectors)
        logger.info(f"\n✅ Upserted {len(vectors)} vectors to Pinecone index '{settings.PINECONE_INDEX_NAME}'")
    else:
        logger.error("No vectors to upsert — check embedding errors above")


def main():
    parser = argparse.ArgumentParser(description="Seed Pinecone with scheme embeddings")
    parser.add_argument("--dry-run",    action="store_true", help="Show text blobs, no API calls")
    parser.add_argument("--delete-all", action="store_true", help="Clear index before seeding")
    args = parser.parse_args()
    print(settings.PINECONE_API_KEY)
    if not settings.PINECONE_API_KEY and not args.dry_run:
        logger.error("PINECONE_API_KEY not set. Cannot proceed.")
        sys.exit(1)

    seed_vectors(dry_run=args.dry_run, delete_all=args.delete_all)


if __name__ == "__main__":
    main()