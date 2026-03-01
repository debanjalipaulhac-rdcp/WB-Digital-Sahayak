"""
config/pinecone_client.py
==========================
Pinecone vector database client for scheme similarity search.

What is Pinecone:
  A vector database. We store scheme descriptions as
  mathematical vectors (embeddings). When a user says
  "scheme for sick mother", we embed that query and find
  the most similar scheme vectors in the database.

Why we need it:
  Rule-based search: "I want Lakshmir Bhandar" — works fine
  Freeform search: "something for my 38-year-old wife" — needs vectors

Setup (one-time):
  1. Go to https://app.pinecone.io
  2. Create a free account
  3. Create index named "wb-sahayak-schemes"
     - Dimensions: 384  (all-MiniLM-L6-v2 output size)
     - Metric: cosine
     - Cloud: AWS  Region: us-east-1 (free tier)
  4. Copy API key → paste in .env.local

Usage:
    from config.pinecone_client import get_pinecone_index
    index = get_pinecone_index()
    if index:
        results = index.query(vector=[...], top_k=3)
"""

import logging
from config.settings import settings

logger = logging.getLogger(__name__)

# Cached index — connect once, reuse across requests
_pinecone_index = None


def get_pinecone_index():
    """
    Returns the Pinecone index for scheme vector search.
    Caches the connection after first call.
    Returns None if API key missing or MOCK_MODE is on.

    The index stores 4 scheme description vectors at MVP.
    At scale: 20+ scheme vectors + sub-scheme variants.

    Example:
        index = get_pinecone_index()
        if index:
            results = index.query(
                vector=query_embedding,   # 384-dim float list
                top_k=3,
                include_metadata=True
            )
            # results.matches[0].metadata["scheme_id"]
    """
    global _pinecone_index

    if _pinecone_index is not None:
        return _pinecone_index

    if settings.MOCK_MODE:
        logger.warning("MOCK_MODE=true — Pinecone not initialised.")
        return None

    if not settings.PINECONE_API_KEY:
        logger.warning("PINECONE_API_KEY not set — vector search disabled.")
        return None

    try:
        from pinecone import Pinecone

        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        _pinecone_index = pc.Index(settings.PINECONE_INDEX_NAME)
        logger.info(f"✅ Pinecone index '{settings.PINECONE_INDEX_NAME}' connected")
        return _pinecone_index

    except ImportError:
        logger.error("pinecone-client not installed. Run: pip install pinecone-client")
        return None

    except Exception as e:
        logger.error(f"Failed to connect to Pinecone: {e}")
        return None


def get_embedding_model():
    """
    Returns the sentence-transformers model for generating embeddings.
    Model: all-MiniLM-L6-v2
      - Output: 384-dimensional vector
      - Size: ~90MB (fast to load)
      - Good for semantic similarity of short sentences

    Cached after first load — loading takes ~2 seconds.

    Example:
        model = get_embedding_model()
        vector = model.encode("scheme for sick mother").tolist()
        # vector is a list of 384 floats
    """
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("✅ Embedding model loaded (all-MiniLM-L6-v2)")
        return model

    except ImportError:
        logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
        return None

    except Exception as e:
        logger.error(f"Failed to load embedding model: {e}")
        return None


# ── Index config constants ─────────────────────────────────────────────────────
EMBEDDING_DIMENSION = 384         # Must match index creation setting
EMBEDDING_MODEL     = "all-MiniLM-L6-v2"
SIMILARITY_METRIC   = "cosine"
TOP_K_RESULTS       = 3           # How many schemes to return per query
MIN_SIMILARITY      = 0.5         # Below this score = not relevant, discard