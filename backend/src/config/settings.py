"""
config/settings.py
==================
Single source of truth for ALL environment variables in the app.

Usage anywhere in the project:
    from config.settings import settings

    print(settings.SARVAM_API_KEY)
    print(settings.DYNAMODB_TABLE_NAME)

Never import os.getenv() directly in your feature files.
Always go through this file — makes testing and debugging clean.
"""

import os
from pathlib import Path
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent.parent

# load_dotenv(BASE_DIR / ".env.local", override=True)   # local secrets first
load_dotenv(BASE_DIR / ".env", override=True)         # fallback defaults
print(BASE_DIR)
print(os.getenv("AWS_REGION"))
# ── Settings Class ────────────────────────────────────────────────────────────
class Settings:

    # ── App ───────────────────────────────────────────────────────────────────
    ENV: str                    = os.getenv("ENV", "development")
    DEBUG: bool                 = os.getenv("DEBUG", "true").lower() == "true"
    MOCK_MODE: bool             = os.getenv("MOCK_MODE", "false").lower() == "true"
    CACHE_TTS: bool             = os.getenv("CACHE_TTS", "true").lower() == "true"

    # ── AWS Core ──────────────────────────────────────────────────────────────
    AWS_REGION: str             = os.getenv("AWS_REGION", "ap-south-1")
    AWS_ACCESS_KEY_ID: str      = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str  = os.getenv("AWS_SECRET_ACCESS_KEY", "")

    # ── DynamoDB ──────────────────────────────────────────────────────────────
    DYNAMODB_TABLE_NAME: str    = os.getenv("DYNAMODB_TABLE_NAME", "wb-sahayak-users")

    # ── S3 ────────────────────────────────────────────────────────────────────
    S3_BUCKET_NAME: str         = os.getenv("S3_BUCKET_NAME", "wb-sahayak-schemes")
    S3_AUDIO_CACHE_PREFIX: str  = os.getenv("S3_AUDIO_CACHE_PREFIX", "audio-cache/")

    # ── Amazon Bedrock ────────────────────────────────────────────────────────
    BEDROCK_MODEL_ID: str       = os.getenv(
                                    "BEDROCK_MODEL_ID",
                                    "anthropic.claude-haiku-20240307-v1:0"
                                  )
    BEDROCK_KNOWLEDGE_BASE_ID: str = os.getenv("BEDROCK_KNOWLEDGE_BASE_ID", "")

    # ── Sarvam AI ─────────────────────────────────────────────────────────────
    SARVAM_API_KEY: str         = os.getenv("SARVAM_API_KEY", "")
    SARVAM_STT_ENDPOINT: str    = os.getenv(
                                    "SARVAM_STT_ENDPOINT",
                                    "https://api.sarvam.ai/speech-to-text"
                                  )
    SARVAM_TTS_ENDPOINT: str    = os.getenv(
                                    "SARVAM_TTS_ENDPOINT",
                                    "https://api.sarvam.ai/text-to-speech"
                                  )
    SARVAM_LANGUAGE_CODE: str   = os.getenv("SARVAM_LANGUAGE_CODE", "bn-IN")

    # ── Twilio WhatsApp ───────────────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: str     = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str      = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_WHATSAPP_NUMBER: str = os.getenv(
                                    "TWILIO_WHATSAPP_NUMBER",
                                    "whatsapp:+14155238886"
                                  )

    # ── Pinecone ──────────────────────────────────────────────────────────────
    PINECONE_API_KEY: str       = os.getenv("PINECONE_API_KEY", "")
    PINECONE_INDEX_NAME: str    = os.getenv("PINECONE_INDEX_NAME", "wb-sahayak-schemes")
    PINECONE_ENVIRONMENT: str   = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")

    # ── Paths (engine data files) ─────────────────────────────────────────────
    SCHEMES_JSON_PATH: str      = str(BASE_DIR / "src" / "engine" / "schemes.json")
    SCRIPTS_JSON_PATH: str      = str(BASE_DIR / "src" / "engine" / "scripts.json")

    # ── Validation: called once at startup ───────────────────────────────────
    def validate(self) -> None:
        """
        Warn loudly if critical keys are missing at startup.
        Does NOT crash the app — allows stubs to run in development.
        """
        required_for_production = {
            "AWS_ACCESS_KEY_ID":      self.AWS_ACCESS_KEY_ID,
            "AWS_SECRET_ACCESS_KEY":  self.AWS_SECRET_ACCESS_KEY,
            "SARVAM_API_KEY":         self.SARVAM_API_KEY,
            "TWILIO_ACCOUNT_SID":     self.TWILIO_ACCOUNT_SID,
            "TWILIO_AUTH_TOKEN":      self.TWILIO_AUTH_TOKEN,
            "PINECONE_API_KEY":       self.PINECONE_API_KEY,
        }

        missing = [k for k, v in required_for_production.items() if not v]

        if missing:
            if self.ENV == "production":
                raise EnvironmentError(
                    f"PRODUCTION STARTUP BLOCKED. Missing env vars: {', '.join(missing)}"
                )
            else:
                print(f"⚠️  [DEV MODE] Missing keys (stubs will run): {', '.join(missing)}")
        else:
            print("✅ All environment variables loaded.")

    def __repr__(self) -> str:
        """Safe repr — never prints secret values."""
        return (
            f"Settings(ENV={self.ENV}, "
            f"MOCK_MODE={self.MOCK_MODE}, "
            f"AWS_REGION={self.AWS_REGION}, "
            f"SARVAM_KEY={'SET' if self.SARVAM_API_KEY else 'MISSING'}, "
            f"TWILIO_SID={'SET' if self.TWILIO_ACCOUNT_SID else 'MISSING'}, "
            f"PINECONE_KEY={'SET' if self.PINECONE_API_KEY else 'MISSING'})"
        )


# ── Singleton — import this everywhere ───────────────────────────────────────
settings = Settings()