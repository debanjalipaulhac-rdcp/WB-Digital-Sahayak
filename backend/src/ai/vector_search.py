"""
src/ai/vector_search.py
========================
Scheme discovery via Amazon Titan Embeddings V2 + Pinecone.

WHY THIS EXISTS:
  The eligibility engine handles: "Check Lakshmir Bhandar for me"
  This module handles:           "I need help for my sick mother"

  Freeform queries from voice → embed → find closest scheme → run eligibility.

EMBEDDING MODEL: Amazon Titan Text Embeddings V2
  - Model ID: amazon.titan-embed-text-v2:0
  - Output: 1024-dimensional vector
  - Endpoint: Bedrock (same client we already use)
  - Cost: $0.024 per 1M tokens = ~$0.012/month at our scale
  - ZERO cold start (pure API call, no model loading)

FLOW:
  User voice: "scheme for my 38-year-old wife"
       ↓
  Titan V2 → 1024-dim vector
       ↓
  Pinecone cosine similarity → top 3 schemes
       ↓
  Return: [{"scheme_id": "lakshmir_bhandar", "score": 0.94, ...}]
       ↓
  WhatsApp: "Lakshmir Bhandar মনে হয় আপনার জন্য ঠিক আছে। চেক করব?"

SETUP (one-time):
  1. Enable Titan Embeddings V2 in AWS Bedrock console (Model Access)
  2. Create Pinecone index:
       Name: wb-sahayak-schemes
       Dimensions: 1024
       Metric: cosine
       Cloud: AWS, Region: us-east-1
  3. Run: python -m src.ai.vector_search --setup
     (populates the index with all 4 scheme vectors)
"""

import json
import logging
from typing import Optional

from src.config.settings import settings

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
TITAN_MODEL_ID      = "amazon.titan-embed-text-v2:0"
EMBEDDING_DIM       = 1024
TOP_K               = 3
MIN_SCORE           = 0.50    # below this = not relevant, discard
NAMESPACE           = ""      # Pinecone free tier has no namespaces


# ── Titan V2 embedding ─────────────────────────────────────────────────────────

def embed(text: str) -> list[float]:
    """
    Convert text to 1024-dim vector using Amazon Titan Embeddings V2 via Bedrock.

    Serverless-safe: pure API call, zero model loading, ~150ms latency.
    Falls back to zero-vector in MOCK_MODE or when AWS credentials missing.

    Args:
        text: Any string — scheme description, user query, office script text

    Returns:
        List of 1024 floats. Empty list on failure.

    Example:
        vec = embed("scheme for 38-year-old woman in rural Bengal")
        # vec = [0.023, -0.145, ...] (1024 floats)
    """
    if not text or not text.strip():
        return []

    if settings.MOCK_MODE or not settings.AWS_ACCESS_KEY_ID:
        logger.debug("MOCK_MODE or no AWS key — returning zero vector")
        return [0.0] * EMBEDDING_DIM

    try:
        from src.config.aws_clients import get_bedrock_client
        client = get_bedrock_client()

        body = json.dumps({
            "inputText": text[:8192],   # Titan V2 max input length
            "dimensions": EMBEDDING_DIM,
            "normalize": True           # unit-length for accurate cosine similarity
        })

        response = client.invoke_model(
            modelId=TITAN_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=body
        )

        result = json.loads(response["body"].read())
        vector = result.get("embedding", [])

        if len(vector) != EMBEDDING_DIM:
            logger.error(f"Titan returned {len(vector)} dims, expected {EMBEDDING_DIM}")
            return []

        logger.debug(f"Embedded {len(text)} chars → {EMBEDDING_DIM}-dim vector")
        return vector

    except Exception as e:
        logger.error(f"Titan embedding failed: {e}")
        return []


# ── Pinecone operations ────────────────────────────────────────────────────────

def search(query: str, top_k: int = TOP_K) -> list[dict]:
    """
    Find the most relevant schemes for a freeform user query.

    Used by the WhatsApp bot when the user doesn't name a specific scheme.
    Falls back to keyword matching if Pinecone is unavailable.

    Args:
        query:  Freeform text — could be Bengali or English
        top_k:  Max results to return (default 3)

    Returns:
        List of scheme dicts ordered by relevance:
        [
          {
            "scheme_id":       "lakshmir_bhandar",
            "scheme_name":     "Lakshmir Bhandar",
            "scheme_name_bn":  "লক্ষ্মীর ভান্ডার",
            "benefit_display": "₹1,000-₹1,200/month",
            "similarity":      0.94,
            "matched_by":      "vector"
          },
          ...
        ]

    Example:
        results = search("আমার বউয়ের জন্য কোনো scheme আছে?")
        if results:
            scheme_id = results[0]["scheme_id"]
            # → "lakshmir_bhandar"
    """
    vector = embed(query)

    if not vector:
        logger.warning(f"Embedding failed for query: '{query}' — using keyword fallback")
        return _keyword_fallback(query)

    try:
        from src.config.pinecone_client import get_pinecone_index
        index = get_pinecone_index()

        if not index:
            logger.warning("Pinecone unavailable — using keyword fallback")
            return _keyword_fallback(query)

        response = index.query(
            vector=vector,
            top_k=top_k,
            include_metadata=True,
            namespace=NAMESPACE
        )

        results = []
        for match in response.matches:
            if match.score < MIN_SCORE:
                continue
            results.append({
                "scheme_id":       match.metadata.get("scheme_id", ""),
                "scheme_name":     match.metadata.get("scheme_name", ""),
                "scheme_name_bn":  match.metadata.get("scheme_name_bn", ""),
                "benefit_display": match.metadata.get("benefit_display", ""),
                "tag":             match.metadata.get("tag", ""),
                "similarity":      round(match.score, 3),
                "matched_by":      "vector"
            })

        logger.info(f"Vector search '{query[:40]}' → {len(results)} results")
        return results

    except Exception as e:
        logger.error(f"Pinecone query failed: {e} — keyword fallback")
        return _keyword_fallback(query)


def setup_index() -> bool:
    """
    One-time setup: embed all 4 schemes and upsert to Pinecone.

    Run ONCE before the demo:
        python -m src.ai.vector_search --setup

    Returns:
        True if all schemes were indexed successfully.
    """
    try:
        from src.engine.eligibility import get_all_schemes
        from src.config.pinecone_client import get_pinecone_index

        index = get_pinecone_index()
        if not index:
            logger.error("Pinecone index not available. Check PINECONE_API_KEY.")
            return False

        schemes = get_all_schemes()
        vectors = []

        for scheme in schemes:
            description = _build_scheme_description(scheme)
            vector = embed(description)

            if not vector:
                logger.error(f"Failed to embed scheme: {scheme['scheme_id']}")
                continue

            vectors.append({
                "id":     scheme["scheme_id"],
                "values": vector,
                "metadata": {
                    "scheme_id":       scheme["scheme_id"],
                    "scheme_name":     scheme["scheme_name"],
                    "scheme_name_bn":  scheme.get("scheme_name_bn", ""),
                    "benefit_display": scheme.get("benefit_display", ""),
                    "tag":             scheme.get("tag", ""),
                }
            })

        if not vectors:
            logger.error("No vectors generated — index setup failed")
            return False

        index.upsert(vectors=vectors, namespace=NAMESPACE)
        logger.info(f"✅ Pinecone index populated: {len(vectors)} schemes")

        # Verify round-trip
        test_vec = embed("welfare scheme for women")
        if test_vec:
            res = index.query(vector=test_vec, top_k=1, include_metadata=True)
            if res.matches:
                logger.info(f"✅ Index verify: top match = {res.matches[0].metadata['scheme_id']}")

        return True

    except Exception as e:
        logger.error(f"setup_index failed: {e}")
        return False


# ── Keyword fallback ───────────────────────────────────────────────────────────

# Simple keyword map — used when Pinecone is unavailable
_KEYWORD_MAP = {
    "lakshmir_bhandar": [
        "wife", "woman", "mother", "lakshmir", "লক্ষ্মী", "মা", "বউ", "মহিলা",
        "female", "1000", "1200", "monthly", "cash"
    ],
    "swasthya_sathi": [
        "health", "hospital", "sick", "doctor", "medicine", "স্বাস্থ্য", "হাসপাতাল",
        "চিকিৎসা", "অসুস্থ", "insurance", "medical", "5 lakh", "5লাখ"
    ],
    "kanyashree": [
        "daughter", "girl", "school", "study", "কন্যা", "মেয়ে", "স্কুল", "পড়াশোনা",
        "education", "scholarship", "kanyashree"
    ],
    "yuva_sathi": [
        "job", "unemployed", "youth", "young", "চাকরি", "বেকার", "যুবক", "যুবা",
        "employment", "graduate", "1500", "2000"
    ],
}


def _keyword_fallback(query: str) -> list[dict]:
    """
    Simple keyword matching fallback when Pinecone is unavailable.
    Not as accurate as vector search but always works offline.
    """
    from src.engine.eligibility import get_scheme

    query_lower = query.lower()
    scores: dict[str, int] = {}

    for scheme_id, keywords in _KEYWORD_MAP.items():
        hits = sum(1 for kw in keywords if kw.lower() in query_lower)
        if hits > 0:
            scores[scheme_id] = hits

    if not scores:
        # Return all schemes if no keywords matched — let user pick
        all_schemes = []
        from src.engine.eligibility import get_all_schemes
        for s in get_all_schemes():
            all_schemes.append({
                "scheme_id": s["scheme_id"],
                "scheme_name": s["scheme_name"],
                "scheme_name_bn": s.get("scheme_name_bn", ""),
                "benefit_display": s.get("benefit_display", ""),
                "similarity": 0.0,
                "matched_by": "default"
            })
        return all_schemes[:TOP_K]

    results = []
    for scheme_id, hit_count in sorted(scores.items(), key=lambda x: -x[1])[:TOP_K]:
        scheme = get_scheme(scheme_id)
        if scheme:
            results.append({
                "scheme_id":       scheme_id,
                "scheme_name":     scheme["scheme_name"],
                "scheme_name_bn":  scheme.get("scheme_name_bn", ""),
                "benefit_display": scheme.get("benefit_display", ""),
                "similarity":      round(hit_count / 5, 2),
                "matched_by":      "keyword"
            })
    return results


def _build_scheme_description(scheme: dict) -> str:
    """
    Build a rich text description for embedding.
    More context = better semantic matching.
    Includes Bengali name so Bengali queries match too.
    """
    el  = scheme.get("eligibility", {})
    ben = scheme.get("benefits", {})
    parts = [
        scheme.get("scheme_name", ""),
        scheme.get("scheme_name_bn", ""),
        scheme.get("benefit_display", ""),
        scheme.get("tag", ""),
    ]
    if el.get("gender"):
        parts.append(f"For {el['gender']} applicants only")
    if el.get("age_min") and el.get("age_max"):
        parts.append(f"Age {el['age_min']} to {el['age_max']} years")
    if ben.get("note"):
        parts.append(ben["note"])
    docs = [d["label"] for d in scheme.get("documents", []) if d.get("required")]
    if docs:
        parts.append(f"Documents required: {', '.join(docs)}")
    return ". ".join(filter(None, parts))


# ── CLI entrypoint ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if "--setup" in sys.argv:
        print("Setting up Pinecone index with scheme vectors...")
        ok = setup_index()
        print("✅ Done" if ok else "❌ Failed — check logs")
        sys.exit(0 if ok else 1)
    else:
        print("Usage: python -m src.ai.vector_search --setup")