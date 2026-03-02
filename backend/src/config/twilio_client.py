"""
config/twilio_client.py
========================
Twilio client for WhatsApp messaging.

What Twilio does for us:
  - Provides a WhatsApp number (sandbox for dev, real number for prod)
  - Receives incoming messages/voice notes via webhook (POST to our Lambda)
  - Sends outgoing text messages and media (voice notes) back to users

How it works:
  1. User sends WhatsApp message to our Twilio number
  2. Twilio makes a POST request to our webhook URL (API Gateway → Lambda)
  3. Lambda processes the message, generates response
  4. Lambda calls Twilio API to send response back to user

Setup (free sandbox):
  1. Go to https://console.twilio.com
  2. Sign up (free $15 credit)
  3. Messaging → Try it out → Send a WhatsApp message
  4. Follow sandbox join instructions
  5. Set webhook URL: your API Gateway URL + /webhook/whatsapp
  6. Copy Account SID and Auth Token → .env.local

Usage:
    from config.twilio_client import get_twilio_client, get_twilio_whatsapp_number
    client = get_twilio_client()
    client.messages.create(
        from_=get_twilio_whatsapp_number(),
        to="whatsapp:+919876543210",
        body="আপনার score: 42/100 🔴"
    )
"""

import logging
from src.config.settings import settings

logger = logging.getLogger(__name__)


def get_twilio_client():
    """
    Returns an initialised Twilio REST client.
    Returns None in MOCK_MODE — WhatsApp channel uses
    simulated responses instead of real Twilio calls.

    Example:
        client = get_twilio_client()
        if client is None:
            print("Mock mode — skipping Twilio send")
            return

        message = client.messages.create(
            from_=get_twilio_whatsapp_number(),
            to="whatsapp:+919876543210",
            body="Your readiness score is 42/100"
        )
        print(f"Message SID: {message.sid}")
    """
    if settings.MOCK_MODE:
        logger.warning("MOCK_MODE=true — Twilio client not initialised. WhatsApp will be simulated.")
        return None

    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.error("TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN not set.")
        return None

    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        logger.info("✅ Twilio client initialised")
        return client

    except ImportError:
        logger.error("twilio not installed. Run: pip install twilio")
        return None

    except Exception as e:
        logger.error(f"Failed to initialise Twilio client: {e}")
        return None


def get_twilio_whatsapp_number() -> str:
    """
    Returns the Twilio WhatsApp sender number in the correct format.
    Twilio requires the "whatsapp:" prefix.

    Sandbox number:  whatsapp:+14155238886  (testing)
    Production:      whatsapp:+91XXXXXXXXXX (your verified WA Business number)
    """
    number = settings.TWILIO_WHATSAPP_NUMBER
    if not number.startswith("whatsapp:"):
        number = f"whatsapp:{number}"
    return number


def format_whatsapp_number(phone: str) -> str:
    """
    Formats a user's phone number for Twilio WhatsApp.
    Handles Indian numbers with or without country code.

    Examples:
        "9876543210"     → "whatsapp:+919876543210"
        "+919876543210"  → "whatsapp:+919876543210"
        "whatsapp:+91..."→ "whatsapp:+919876543210"  (already formatted)
    """
    phone = phone.strip().replace(" ", "").replace("-", "")

    if phone.startswith("whatsapp:"):
        return phone

    if not phone.startswith("+"):
        if phone.startswith("91") and len(phone) == 12:
            phone = f"+{phone}"
        elif len(phone) == 10:
            phone = f"+91{phone}"    # assume India
        else:
            phone = f"+{phone}"

    return f"whatsapp:{phone}"


# ── Message template helpers ───────────────────────────────────────────────────

def build_score_message(score: int, band: str, scheme_name: str) -> str:
    """
    Returns a formatted score message for WhatsApp.
    Keeps it short — WhatsApp users don't read long messages.

    Example output:
        "🔴 Lakshmir Bhandar Readiness Score: 42/100
         আপনি এখনই যাওয়ার জন্য প্রস্তুত নন।"
    """
    emoji = {"GREEN": "🟢", "AMBER": "🟡", "RED": "🔴"}.get(band, "⚪")
    bn_verdict = {
        "GREEN": "আপনি প্রস্তুত! আগামীকাল অফিসে যেতে পারেন।",
        "AMBER": "আগে সমস্যাগুলো ঠিক করুন, তারপর যান।",
        "RED":   "এখনই যাবেন না। আগে নিচের কাজগুলো করুন।"
    }.get(band, "")

    return f"{emoji} *{scheme_name} Readiness Score: {score}/100*\n{bn_verdict}"


def build_issue_message(issues: list) -> str:
    """
    Returns formatted issue list for WhatsApp.
    Each fatal issue gets a ⚠️, warnings get a 📝.
    """
    if not issues:
        return "✅ কোনো সমস্যা পাওয়া যায়নি।"

    lines = ["*সমস্যা পাওয়া গেছে:*"]
    for i, issue in enumerate(issues, 1):
        icon = "⚠️" if issue.get("type") == "fatal" else "📝"
        lines.append(f"{icon} {i}. {issue.get('message', '')}")
    return "\n".join(lines)


def build_roadmap_message(roadmap: list) -> str:
    """
    Returns formatted roadmap for WhatsApp.

    Example output:
        "📋 *আপনার Action Plan:*
         1️⃣ Bank Branch → নাম ঠিক করুন
         2️⃣ Bank Branch → Account reactivate করুন
         3️⃣ BDO Office → Application জমা দিন"
    """
    if not roadmap:
        return ""

    step_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    lines = ["📋 *আপনার Action Plan:*"]

    for step in roadmap:
        n = step.get("step", 1) - 1
        emoji = step_emojis[n] if n < len(step_emojis) else "▶️"
        where = step.get("where", "")
        what  = step.get("what_bn") or step.get("what", "")
        lines.append(f"{emoji} {where} → {what}")

    return "\n".join(lines)