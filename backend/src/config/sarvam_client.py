
import logging
from src.config.settings import settings

logger = logging.getLogger(__name__)


def get_sarvam_client():
    """
    Returns an initialised Sarvam AI client.

    Requires: pip install sarvamai
    API key must be set in .env.local as SARVAM_API_KEY

    Returns None in MOCK_MODE so voice pipeline
    can fall back to text without crashing.

    Example:
        client = get_sarvam_client()
        if client is None:
            return "Mock TTS response"  # MOCK_MODE fallback
    """
    if settings.MOCK_MODE:
        logger.warning("MOCK_MODE=true — Sarvam AI client not initialised. Voice will use fallback.")
        return None

    if not settings.SARVAM_API_KEY:
        logger.error("SARVAM_API_KEY is not set. Voice pipeline will fail.")
        return None

    try:
        from sarvamai import SarvamAI
        client = SarvamAI(api_subscription_key=settings.SARVAM_API_KEY)
        logger.info("✅ Sarvam AI client initialised")
        return client

    except ImportError:
        logger.error("sarvamai package not installed. Run: pip install sarvamai")
        return None

    except Exception as e:
        logger.error(f"Failed to initialise Sarvam AI client: {e}")
        return None



# ── Language code constants ────────────────────────────────────────────────────
# Use these instead of raw strings to avoid typos
BENGALI    = "bn-IN"
HINDI      = "hi-IN"
ENGLISH_IN = "en-IN"
ODIA       = "or-IN"
SANTALI    = "sat-IN"   # Phase 3 — tribal dialect support
