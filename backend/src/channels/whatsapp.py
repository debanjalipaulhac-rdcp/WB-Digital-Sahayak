"""
src/channels/whatsapp.py
========================
Twilio WhatsApp webhook — the full pipeline in one file.

FLOW:
  POST /webhook/whatsapp
    → return 200 immediately           # Twilio timeout = 15s, we can't block
    → background thread runs pipeline:
        guardrails → STT/language detect → session load → intent route
        → handler → translate → chunk → cache → TTS → assemble → send

SESSION (DynamoDB):
  - Key: phone_number
  - TTL: 5 minutes of inactivity → new session on next message
  - Sliding window: last 5 messages stored for context
  - Stores: language_code, last_active, history[], session_context{}

5-MIN SESSION LOGIC:
  On every message:
    if (now - last_active) > 300 seconds → reset session, treat as new user
    else → continue existing session
"""

import json
import logging
import threading
import time
import requests as http_requests
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

# Pipeline imports
from src.voice.stt                  import transcribe_audio, STTResult
from src.engine.scoring             import calculate_score, get_readiness_label_bn
from src.storage.dynamo             import get_user, save_user, update_session_state
# from src.engine.mismatch            import check_name_mismatch,generate_mismatch_script
from src.cache.audio_cache          import resolve_chunks, fill_misses
from src.router.guardrails          import validate_input
from src.engine.eligibility         import check_eligibility
from src.cache.tts_generator        import generate_for_misses
from src.voice.chunk_splitter       import split_into_chunks
from src.router.intent_router       import route, IntentType
from src.static.scheme_lookup       import lookup as static_lookup
from src.translate.translator       import translate_text
from src.voice.language_detect      import detect_language, is_greeting
from src.voice.audio_assembler      import assemble_audio
from src.dynamic.vector_search      import search as vector_search
from src.cache.background_saver     import save_new_chunks_async
from src.dynamic.nova_responder     import generate_response
from src.static.greeting_handler    import get_greeting_response
from src.dynamic.keyword_extractor  import extract_keywords

from src.config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# ─────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────
SESSION_TTL_SECONDS  = 300        # 5 minutes inactivity → new session
HISTORY_WINDOW_SIZE  = 5          # Sliding window: last N exchanges
MAX_AUDIO_SECONDS    = 45         # Safety buffer under 50s SLA

ERROR_MSG_BN = "দুঃখিত, কিছু সমস্যা হয়েছে। একটু পরে আবার চেষ্টা করুন।"
ERROR_MSG_EN = "Sorry, something went wrong. Please try again."


# ─────────────────────────────────────────────────────────────
# TWILIO CLIENT
# ─────────────────────────────────────────────────────────────

from src.config.twilio_client import get_twilio_client


def _wa_number(phone: str) -> str:
    """Ensure number is in whatsapp:+91XXXXXXXXXX format."""
    if not phone.startswith("whatsapp:"):
        return f"whatsapp:{phone}"
    return phone


# ─────────────────────────────────────────────────────────────
# WEBHOOK ENTRY POINT — returns 200 immediately
# ─────────────────────────────────────────────────────────────
@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Receive Twilio webhook. Return 200 immediately.
    Actual processing runs in a background thread.

    Twilio form fields:
      From:                  "whatsapp:+919876543210"
      Body:                  "লক্ষ্মীর ভাণ্ডার কি আমার জন্য?"
      NumMedia:              "1" if voice/media attached
      MediaUrl0:             voice note URL
      MediaContentType0:     "audio/ogg"
    """
    try:
        form       = await request.form()
        phone      = str(form.get("From", "")).strip()
        body       = str(form.get("Body", "")).strip()
        num_media  = int(form.get("NumMedia", 0))
        media_url  = str(form.get("MediaUrl0", "")).strip() if num_media > 0 else ""
        media_type = str(form.get("MediaContentType0", "")).strip()
        print(form)
        if not phone:
            logger.error("Webhook received with no From field")
            return PlainTextResponse("", status_code=200)

        logger.info(f"[webhook] from={phone} | text='{body[:40]}' | audio={bool(media_url)}")

        # Fire background thread — never block Twilio
        thread = threading.Thread(
            target=_safe_pipeline,
            args=(phone, body, media_url, media_type),
            daemon=True
        )
        thread.start()

    except Exception as e:
        logger.error(f"[webhook] outer exception: {e}", exc_info=True)

    # Always return 200 to Twilio regardless of what happens
    return PlainTextResponse("", status_code=200)


# ─────────────────────────────────────────────────────────────
# SAFE WRAPPER — catches everything so thread never crashes silently
# ─────────────────────────────────────────────────────────────
def _safe_pipeline(phone: str, body: str, media_url: str, media_type: str):
    """Wraps full pipeline in try/except. Sends error message on failure."""
    try:
        _pipeline(phone, body, media_url, media_type)
    except Exception as e:
        logger.error(f"[pipeline] CRASH for {phone}: {e}", exc_info=True)
        try:
            # Try to get user language for error message
            user = get_user(phone) or {}
            lang = user.get("language_code", "bn-IN")
            error_msg = ERROR_MSG_BN if lang == "bn-IN" else ERROR_MSG_EN
            _send_text(phone, error_msg)
        except Exception:
            pass   # If even error send fails, swallow silently


# ─────────────────────────────────────────────────────────────
# FULL PIPELINE
# ─────────────────────────────────────────────────────────────
def _pipeline(phone: str, body: str, media_url: str, media_type: str):
    """
    Complete message processing pipeline.
    Steps are numbered for easy debugging in CloudWatch logs.
    """

    # ── STEP 1: Load session ──────────────────────────────────
    user     = get_user(phone) or {}
    session  = _load_or_reset_session(phone, user)
    language = session.get("language_code", "bn-IN")
    is_voice = bool(media_url and "audio" in media_type)

    logger.info(f"[1] session={session.get('state')} lang={language} voice={is_voice}")

    # ── STEP 2: Get text (STT or raw) ────────────────────────
    if is_voice:
        text, language = _handle_audio_input(phone, media_url, media_type, language)
        if text is None:
            # STT failed — ask user to resend
            _send_text(phone, _t(
                language,
                bn="আপনার অডিও শুনতে পাইনি। একটু জোরে বলুন বা টেক্সটে লিখুন।",
                en="Could not hear your audio. Please speak louder or type your message."
            ))
            return
    else:
        text = body.strip()
        if not text:
            logger.info(f"[2] empty text body, ignoring")
            return
        # Detect language from text
        detected = detect_language(text)
        if detected != "en-IN":   # trust detection for non-English
            language = detected

    logger.info(f"[2] text='{text[:60]}' detected_lang={language}")

    # ── STEP 3: Update session language if changed ───────────
    if language != session.get("language_code"):
        session["language_code"] = language
        user["language_code"]    = language

    # ── STEP 4: Guardrails ───────────────────────────────────
    guard = validate_input(text)
    if not guard.valid:
        logger.info(f"[4] guardrail blocked: {guard.reason}")
        _respond(phone, guard.response or ERROR_MSG_EN, language, is_voice)
        return

    # ── STEP 5: Reset command check ──────────────────────────
    if _is_reset_command(text):
        _reset_session(phone, language)
        _respond(phone, _t(
            language,
            bn="নতুন কথোপকথন শুরু হলো। কীভাবে সাহায্য করতে পারি?",
            en="Starting a new conversation. How can I help you?"
        ), language, is_voice)
        return

    # ── STEP 6: Intent routing ───────────────────────────────
    decision = route(text, language)
    logger.info(f"[6] intent={decision.intent} scheme={decision.scheme_id} "
                f"qa_type={decision.qa_type} conf={decision.confidence:.2f}")

    # ── STEP 7: Handle by intent ─────────────────────────────
    response_text = None
    audio_url_direct = None   # If we already have a pre-cached URL (greeting/static)

    if decision.intent == IntentType.GREETING:
        # GREETING PATH — zero API calls
        greeting = get_greeting_response(language)
        _send_text(phone, greeting.text)
        if is_voice and greeting.audio_key:
            from src.storage.s3 import get_audio_url
            _send_audio(phone, get_audio_url(greeting.audio_key))
        _save_session(phone, session, text, greeting.text)
        return

    elif decision.intent == IntentType.STATIC_QA:
        # STATIC Q&A — DynamoDB lookup, no AI
        # Translate to English for lookup if needed
        lookup_q = translate_text(text, language, "en-IN") if language != "en-IN" else text
        static   = static_lookup(lookup_q, language)

        if static:
            logger.info(f"[7] static HIT: {static.qa_id}")
            response_text = static.answer_text
            if static.audio_url:
                audio_url_direct = static.audio_url
        else:
            # Static miss → fall through to dynamic
            logger.info(f"[7] static MISS → escalating to dynamic")
            response_text = _dynamic_path(text, language, decision)

    elif decision.intent == IntentType.ELIGIBILITY:
        # ELIGIBILITY PATH — deterministic engine
        response_text = _eligibility_path(phone, text, language, decision, session, is_voice)

    else:
        # DYNAMIC PATH — vector search + Nova Lite
        response_text = _dynamic_path(text, language, decision)

    if not response_text:
        response_text = _t(
            language,
            bn="দুঃখিত, এই মুহূর্তে উত্তর দিতে পারছি না।",
            en="Sorry, I could not find an answer right now."
        )

    # ── STEP 8: Deliver response ─────────────────────────────
    if audio_url_direct:
        # Pre-cached audio available — send both text and audio directly
        _send_text(phone, response_text)
        if is_voice:
            _send_audio(phone, audio_url_direct)
    else:
        _respond(phone, response_text, language, is_voice)

    # ── STEP 9: Save session ─────────────────────────────────
    _save_session(phone, session, text, response_text)
    _save_user(phone, user, language)


# ─────────────────────────────────────────────────────────────
# PATH HANDLERS
# ─────────────────────────────────────────────────────────────

def _dynamic_path(text: str, language: str, decision) -> str:
    """
    Vector search + Nova Lite path.
    Returns English response text (translated by caller if needed).
    """
    # Translate to English for keyword extraction if not already
    en_text = translate_text(text, language, "en-IN") if language != "en-IN" else text

    keywords      = extract_keywords(en_text)
    search_result = vector_search(keywords)
    en_response   = generate_response(en_text, search_result)

    # Translate back to user language
    if language != "en-IN":
        return translate_text(en_response, "en-IN", language)
    return en_response


def _eligibility_path(
    phone: str, text: str, language: str,
    decision, session: dict, is_voice: bool
) -> str:
    """
    Eligibility check path. Tries to extract profile from text or
    asks user for missing fields. Returns formatted response.
    """
    ctx = session.get("session_context", {})

    # Try to extract profile fields from text
    profile = _extract_profile_from_text(text, ctx)

    if not profile.get("age") or not profile.get("gender"):
        # Missing required fields — ask for them
        session["session_context"] = ctx
        return _t(
            language,
            bn="আপনার বয়স এবং লিঙ্গ জানান। যেমন: '৩৫ বছর মহিলা'",
            en="Please tell me your age and gender. Example: '35 year old female'"
        )

    # Run eligibility check
    scheme_id = decision.scheme_id or "lakshmir_bhandar"
    result    = check_eligibility(scheme_id, profile)


    score_res = calculate_score(
        {"passed_rules": result.passed_rules, "failed_rules": result.failed_rules,
         "required_documents": result.required_documents},
        {},   # documents not collected in voice flow yet
        mismatch_status="match"
    )

    # Format response
    if result.eligible:
        response = _t(
            language,
            bn=f"✅ আপনি {result.scheme_name} এর জন্য যোগ্য। "
               f"প্রস্তুতি স্কোর: {score_res.total}/100। "
               f"দরকারি কাগজ: {', '.join(result.required_documents[:3])}।",
            en=f"✅ You are eligible for {result.scheme_name}. "
               f"Readiness score: {score_res.total}/100. "
               f"Required documents: {', '.join(result.required_documents[:3])}."
        )
    else:
        failed = "; ".join(result.failed_rules[:2])
        response = _t(
            language,
            bn=f"❌ আপনি এখন {result.scheme_name} এর জন্য যোগ্য নন। "
               f"কারণ: {failed}।",
            en=f"❌ You are not currently eligible for {result.scheme_name}. "
               f"Reason: {failed}."
        )

    return response


# ─────────────────────────────────────────────────────────────
# AUDIO RESPONSE ASSEMBLER
# ─────────────────────────────────────────────────────────────

def _respond(phone: str, text: str, language: str, is_voice: bool):
    """
    Full response delivery:
    1. Always send text
    2. If voice user → chunk → cache → TTS → assemble → send audio
    """
    # Always send text first (instant, no wait)
    _send_text(phone, text)

    if not is_voice:
        return

    # Audio path
    chunks      = split_into_chunks(text)
    if not chunks:
        logger.warning(f"[respond] No chunks from text: '{text[:40]}'")
        return

    # Guard: estimate duration
    from src.voice.chunk_splitter import estimate_audio_duration
    est_seconds = estimate_audio_duration(chunks)
    if est_seconds > MAX_AUDIO_SECONDS:
        logger.warning(f"[respond] Response too long for audio ({est_seconds:.1f}s), skipping")
        return

    # Cache lookup
    resolution  = resolve_chunks(chunks, language)

    # TTS for misses only
    generated   = {}
    if resolution.misses:
        generated = generate_for_misses(resolution.misses, language)

    # Fill URLs in order
    all_urls    = fill_misses(resolution, generated)
    if not all_urls:
        logger.error("[respond] No audio URLs available after cache+TTS")
        return

    # Assemble and send
    final_url   = assemble_audio(all_urls)
    if final_url:
        _send_audio(phone, final_url)
    else:
        logger.error("[respond] assemble_audio returned None")

    # Background: save new chunks to DynamoDB cache
    if generated:
        new_chunks = [
            {"chunk_text": chunk, "audio_url": url}
            for chunk, url in generated.items()
        ]
        save_new_chunks_async(new_chunks, language)


# ─────────────────────────────────────────────────────────────
# TWILIO SEND HELPERS
# ─────────────────────────────────────────────────────────────

def _send_text(phone: str, text: str):
    """Send text message via Twilio."""
    try:
        client = get_twilio_client()
        client.messages.create(
            from_=_wa_number(settings.TWILIO_WHATSAPP_NUMBER),
            to=_wa_number(phone),
            body=text
        )
        logger.info(f"[send_text] → {phone}: '{text[:60]}'")
    except Exception as e:
        logger.error(f"[send_text] Failed for {phone}: {e}")


def _send_audio(phone: str, audio_url: str):
    """Send audio message via Twilio."""
    try:
        client = get_twilio_client()
        client.messages.create(
            from_=_wa_number(settings.TWILIO_WHATSAPP_NUMBER),
            to=_wa_number(phone),
            media_url=[audio_url]
        )
        logger.info(f"[send_audio] → {phone}: {audio_url}")
    except Exception as e:
        logger.error(f"[send_audio] Failed for {phone}: {e}")


# ─────────────────────────────────────────────────────────────
# SESSION MANAGEMENT
# ─────────────────────────────────────────────────────────────

def _load_or_reset_session(phone: str, user: dict) -> dict:
    """
    Load session from user record.
    If last_active > 5 minutes ago → reset session (new conversation).
    Returns session dict with guaranteed keys.
    """
    now = time.time()
    last_active = float(user.get("last_active", 0))

    if (now - last_active) > SESSION_TTL_SECONDS and last_active != 0:
        logger.info(f"[session] {phone} session expired ({now - last_active:.0f}s ago) → reset")
        return _fresh_session()

    session = {
        "state":           user.get("session_state", "START"),
        "language_code":   user.get("language_code", "bn-IN"),
        "history":         json.loads(user.get("history", "[]")),
        "session_context": json.loads(user.get("session_context", "{}"))
    }
    return session


def _fresh_session() -> dict:
    return {
        "state":           "START",
        "language_code":   "bn-IN",
        "history":         [],
        "session_context": {}
    }


def _reset_session(phone: str, language: str):
    """Hard reset — wipe session, keep phone + language."""
    save_user(phone, {
        "language_code":   language,
        "session_state":   "START",
        "history":         "[]",
        "session_context": "{}",
        "last_active":     str(time.time())
    })


def _save_session(phone: str, session: dict, user_msg: str, bot_msg: str):
    """
    Append exchange to history (sliding window of HISTORY_WINDOW_SIZE).
    Save back to DynamoDB user record.
    """
    history: list = session.get("history", [])
    history.append({"role": "user",      "text": user_msg[:200]})
    history.append({"role": "assistant", "text": bot_msg[:200]})

    # Sliding window — keep only last N pairs
    if len(history) > HISTORY_WINDOW_SIZE * 2:
        history = history[-(HISTORY_WINDOW_SIZE * 2):]

    session["history"] = history
    _save_user(phone, {
        "session_state":   session.get("state", "START"),
        "language_code":   session.get("language_code", "bn-IN"),
        "history":         json.dumps(history),
        "session_context": json.dumps(session.get("session_context", {})),
        "last_active":     str(time.time())
    }, session.get("language_code", "bn-IN"))


def _save_user(phone: str, updates: dict, language: str = "bn-IN"):
    """Save user record with updates."""
    save_user(phone, {"phone_number": phone, **updates})


# ─────────────────────────────────────────────────────────────
# AUDIO INPUT HANDLING
# ─────────────────────────────────────────────────────────────

def _handle_audio_input(
    phone: str, media_url: str, media_type: str, hint_lang: str
) -> tuple[Optional[str], str]:
    """
    Download audio from Twilio URL and transcribe with Sarvam STT.
    Returns (transcript_text, detected_language) or (None, hint_lang) on failure.
    """
    try:
        # Download audio bytes from Twilio
        resp = http_requests.get(
            media_url,
            auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
            timeout=15
        )
        resp.raise_for_status()
        audio_bytes = resp.content
    except Exception as e:
        logger.error(f"[audio] Failed to download from Twilio: {e}")
        return None, hint_lang

    stt: STTResult = transcribe_audio(audio_bytes, hint_language=hint_lang)

    if stt.is_fallback or not stt.transcript.strip():
        logger.warning(f"[audio] STT fallback for {phone}")
        return None, hint_lang

    return stt.transcript, stt.language_code


# ─────────────────────────────────────────────────────────────
# PROFILE EXTRACTION FROM TEXT
# ─────────────────────────────────────────────────────────────

def _extract_profile_from_text(text: str, existing_ctx: dict) -> dict:
    """
    Simple heuristic extraction of profile fields from free text.
    Merges with existing session context.
    e.g. "35 year old female SC caste" → {age:35, gender:'female', caste:'sc'}
    """
    import re
    profile = dict(existing_ctx)   # start from existing context
    lower   = text.lower()

    # Age extraction: "35" or "৩৫" or "35 years"
    age_match = re.search(r'\b(\d{1,3})\s*(year|বছর|yr|yrs)?', text)
    if age_match:
        age = int(age_match.group(1))
        if 5 < age < 120:
            profile["age"] = age

    # Gender
    if any(w in lower for w in ["female", "woman", "mahila", "মহিলা", "lady", "wife"]):
        profile["gender"] = "female"
    elif any(w in lower for w in ["male", "man", "পুরুষ", "purush"]):
        profile["gender"] = "male"

    # Caste
    if any(w in lower for w in ["sc", "scheduled caste", "তফসিলি জাতি"]):
        profile["caste"] = "sc"
    elif any(w in lower for w in ["st", "scheduled tribe", "তফসিলি উপজাতি"]):
        profile["caste"] = "st"
    elif any(w in lower for w in ["obc", "অন্যান্য পিছিয়ে পড়া"]):
        profile["caste"] = "obc"
    elif any(w in lower for w in ["general", "সাধারণ"]):
        profile["caste"] = "general"

    # Defaults
    profile.setdefault("state",                            "west_bengal")
    profile.setdefault("is_govt_employee",                 False)
    profile.setdefault("is_income_tax_payer",              False)
    profile.setdefault("is_enrolled_in_other_cash_scheme", False)
    profile.setdefault("is_student",                       False)
    profile.setdefault("is_unemployed",                    False)
    profile.setdefault("is_unmarried",                     True)

    return profile


# ─────────────────────────────────────────────────────────────
# UTILITY
# ─────────────────────────────────────────────────────────────

def _is_reset_command(text: str) -> bool:
    """Detect restart/reset intent."""
    lower = text.strip().lower()
    return lower in {
        "reset", "restart", "start over", "new", "start",
        "নতুন", "আবার শুরু", "শুরু", "cancel", "বাতিল"
    }


def _t(language: str, bn: str, en: str) -> str:
    """Simple bilingual string selector. Add hi-IN support if needed."""
    if language == "bn-IN":
        return bn
    return en