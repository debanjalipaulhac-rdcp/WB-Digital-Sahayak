"""
src/config/pinecone_client.py
==========================
Standardized for Titan V2 (1024 dims).
"""
"""
src/config/pinecone_client.py
==========================
Standardized for Titan V2 (1024 dims) with Auto-Index Creation.
"""
import logging
import time
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
        from pinecone import Pinecone, ServerlessSpec
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)

        # ── Check if index exists, create if not ──────────────────────────────
        existing_indexes = [index.name for index in pc.list_indexes()]
        
        if settings.PINECONE_INDEX_NAME not in existing_indexes:
            logger.info(f"Creating new Pinecone index: {settings.PINECONE_INDEX_NAME}...")
            pc.create_index(
                name=settings.PINECONE_INDEX_NAME,
                dimension=1024, # Titan V2 Dimensions
                metric='cosine',
                spec=ServerlessSpec(
                    cloud='aws', 
                    region='us-east-1' # Pinecone Free Tier Region
                )
            )
            # Wait for index to be ready
            while not pc.describe_index(settings.PINECONE_INDEX_NAME).status['ready']:
                time.sleep(1)
            logger.info("✅ New index created and ready")

        _pinecone_index = pc.Index(settings.PINECONE_INDEX_NAME)
        logger.info(f"✅ Connected to Pinecone index: {settings.PINECONE_INDEX_NAME}")
        return _pinecone_index

    except Exception as e:
        logger.error(f"Failed to connect/create Pinecone: {e}")
        return None

# Titan V2 Config
EMBEDDING_DIMENSION = 1024
SIMILARITY_METRIC   = "cosine"
TOP_K_RESULTS       = 3
MIN_SIMILARITY      = 0.5