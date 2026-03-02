"""
src/config/pinecone_client.py
==========================
Standardized for Titan V2 (1024 dims).
"""
import logging
from src.config.settings import settings

logger = logging.getLogger(__name__)

_pinecone_index = None

def get_pinecone_index():
    global _pinecone_index
    if _pinecone_index is not None:
        return _pinecone_index

    if settings.MOCK_MODE or not settings.PINECONE_API_KEY:
        logger.warning("Pinecone disabled (Mock Mode or missing API Key)")
        return None

    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        _pinecone_index = pc.Index(settings.PINECONE_INDEX_NAME)
        logger.info(f"✅ Pinecone index '{settings.PINECONE_INDEX_NAME}' connected")
        return _pinecone_index
    except Exception as e:
        logger.error(f"Failed to connect to Pinecone: {e}")
        return None

# ── Titan V2 Config ────────────────────────────────────────────────────────────
EMBEDDING_DIMENSION = 1024         # Matches amazon.titan-embed-text-v2:0
SIMILARITY_METRIC   = "cosine"
TOP_K_RESULTS       = 3
MIN_SIMILARITY      = 0.5