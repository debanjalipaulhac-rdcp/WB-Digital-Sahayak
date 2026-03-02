"""
src/channels/whatsapp.py
=========================
Twilio WhatsApp webhook handler + conversation state machine.

ARCHITECTURE:
  Twilio → POST /webhook/whatsapp → this handler
  Handler reads session from DynamoDB → processes message → sends reply via Twilio → saves session

CONVERSATION STATES (conversation_step):
  START              → New user. Send welcome + ask which scheme.
  AWAITING_SCHEME    → User said "hi". Waiting for scheme choice.
  AWAITING_PROFILE   → Have scheme. Collecting: age, gender, caste, district.
  AWAITING_DOCS      → Have profile. Asking which documents they have.
  AWAITING_NAMES     → Have docs. Collecting names on each doc (for mismatch check).
  AWAITING_BANK      → Have names. Checking bank status.
  RESULT_SHOWN       → Sent the result. Waiting for "what next?" follow-ups.
  AWAITING_SCRIPT    → User asked for office script for a specific issue.

VOICE HIERARCHY (Strategy 3):
  Tier 1 (TTS audio): score_reveal, mismatch_alert, welcome, office_script
  Tier 2 (text only): confirmations, prompts, acknowledgements

COST GUARDS:
  - 15s audio cap enforced by sarvam_stt.py
  - Cache-first TTS via sarvam_tts.py + s3.py
  - Short-circuit: ineligible users terminated immediately (no further STT spend)
"""

import json
import logging
from typing import Optional
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import PlainTextResponse

from src.voice.response_router import should_send_audio, format_whatsapp_response
from src.ai.language_detector import get_response_lang
from src.storage.dynamo import (
    get_session, save_session, clear_session,
    get_profile, save_profile, save_result
)
from src.engine.eligibility import run_eligibility_check, get_all_schemes, get_scheme
from src.ai.vector_search import search as vector_search
from src.config.bedrock_client import generate_explanation
from src.config.twilio_client import (
    get_twilio_client, get_twilio_whatsapp_number, format_whatsapp_number,
    build_score_message, build_issue_message, build_roadmap_message
)
from src.config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Twilio Webhook Entry Point ─────────────────────────────────────────────────

@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Receives all incoming WhatsApp messages and voice notes from Twilio.

    Twilio sends a form POST with these fields:
      From:        "whatsapp:+919876543210"
      Body:        "আমি Lakshmir Bhandar জানতে চাই"
      NumMedia:    "1"  (if voice note attached)
      MediaUrl0:   "https://api.twilio.com/..."  (voice note URL)
      MediaContentType0: "audio/ogg"

    We always respond with 200 OK + empty body.
    The actual reply is sent asynchronously via Twilio REST API.
    """
    try:
        form = await request.form()
        phone     = str(form.get("From", "")).strip()
        body      = str(form.get("Body", "")).strip()
        num_media = int(form.get("NumMedia", 0))
        media_url = str(form.get("MediaUrl0", "")).strip() if num_media > 0 else ""
        media_type = str(form.get("MediaContentType0", "")).strip()

        if not phone:
            logger.error("Webhook called with no From field")
            return PlainTextResponse("", status_code=200)

        logger.info(f"Incoming: {phone} | text='{body[:40]}' | media={num_media > 0}")

        # Process in a try/except — never let a bug kill the 200 response to Twilio
        try:
            await _handle_message(phone, body, media_url, media_type)
        except Exception as e:
            logger.error(f"Message handler crashed for {phone}: {e}")
            _send_text(phone, "দুঃখিত, একটু সমস্যা হয়েছে। একটু পরে আবার চেষ্টা করুন।")

        return PlainTextResponse("", status_code=200)

    except Exception as e:
        logger.error(f"Webhook outer exception: {e}")
        return PlainTextResponse("", status_code=200)   # always 200 to Twilio


# ── Message Dispatcher ────────────────────────────────────────────────────────

async def _handle_message(phone: str, body: str, media_url: str, media_type: str):
    """
    Route the incoming message to the correct state handler.
    """
    # Step 1: Transcribe if voice note
    user_text = body
    is_voice  = False

    if media_url and "audio" in media_type:
        user_text, is_voice = _transcribe_voice(phone, media_url)
        if user_text is None:
            return   # transcription failed or was rejected — message already sent

    # Step 2: Clean and normalise
    user_text = user_text.strip()

    # Step 3: Global commands — work from any state
    if _is_restart_command(user_text):
        clear_session(phone)
        _handle_start(phone)
        return

    # Step 4: Load session — store voice flag + detected language
    session = get_session(phone) or {}
    step    = session.get("conversation_step", "START")

    # Persist voice flag so response_router can use it this turn
    session["last_input_was_voice"] = is_voice
    # Detect + store language (persists across turns)
    if not session.get("lang"):
        session["lang"] = get_response_lang(user_text, session)

    logger.info(f"State: {phone} | step={step} | text='{user_text[:40]}'")

    # Step 5: Route to handler
    handlers = {
        "START":            _handle_start,
        "AWAITING_SCHEME":  _handle_scheme_selection,
        "AWAITING_PROFILE": _handle_profile_collection,
        "AWAITING_DOCS":    _handle_doc_collection,
        "AWAITING_NAMES":   _handle_name_collection,
        "AWAITING_BANK":    _handle_bank_questions,
        "RESULT_SHOWN":     _handle_post_result,
        "AWAITING_SCRIPT":  _handle_script_request,
    }

    handler = handlers.get(step, _handle_start)
    handler(phone, user_text, session)


# ── State Handlers ────────────────────────────────────────────────────────────

def _handle_start(phone: str, text: str = "", session: dict = {}):
    """
    First contact or restart. Send welcome and ask for scheme.
    """
    from src.voice.sarvam_tts import generate_welcome_audio

    # Try to send cached welcome audio (Tier 1)
    url, _ = generate_welcome_audio()
    if url:
        _send_voice(phone, url)
    else:
        # Tier 2 fallback
        _send_text(phone,
            "🙏 স্বাগতম! আমি আপনার Digital Sahayak।\n\n"
            "আপনি কোন scheme জানতে চান?\n\n"
            "1️⃣ Lakshmir Bhandar (মহিলা - ₹1000/মাস)\n"
            "2️⃣ Swasthya Sathi (স্বাস্থ্য বীমা ₹5 লাখ)\n"
            "3️⃣ Kanyashree (মেয়েদের পড়াশোনা)\n"
            "4️⃣ Yuva Sathi (যুবক - ₹1500/মাস)\n\n"
            "নম্বর লিখুন অথবা বলুন কী দরকার।"
        )

    save_session(phone, {"conversation_step": "AWAITING_SCHEME"})


def _handle_scheme_selection(phone: str, text: str, session: dict):
    """
    User is choosing a scheme. Try number → keyword → vector search.
    """
    # Direct number mapping
    number_map = {
        "1": "lakshmir_bhandar", "১": "lakshmir_bhandar",
        "2": "swasthya_sathi",   "২": "swasthya_sathi",
        "3": "kanyashree",       "৩": "kanyashree",
        "4": "yuva_sathi",       "৪": "yuva_sathi",
    }

    scheme_id = number_map.get(text.strip())

    # Keyword shortcuts
    if not scheme_id:
        t = text.lower()
        if any(k in t for k in ["lakshmir", "লক্ষ্মী", "bhandar", "ভান্ডার", "1000"]):
            scheme_id = "lakshmir_bhandar"
        elif any(k in t for k in ["swasthya", "স্বাস্থ্য", "health", "hospital", "sathi"]):
            scheme_id = "swasthya_sathi"
        elif any(k in t for k in ["kanyashree", "কন্যাশ্রী", "daughter", "মেয়ে", "girl"]):
            scheme_id = "kanyashree"
        elif any(k in t for k in ["yuva", "যুবা", "job", "চাকরি", "unemployed", "বেকার"]):
            scheme_id = "yuva_sathi"

    # Vector search fallback
    if not scheme_id:
        results = vector_search(text, top_k=1)
        if results and results[0]["similarity"] > 0.55:
            scheme_id = results[0]["scheme_id"]
            _send_text(phone,
                f"✅ আমি বুঝতে পেরেছি — {results[0]['scheme_name_bn'] or results[0]['scheme_name']} "
                f"সম্পর্কে জানতে চান। শুরু করি?"
            )

    if not scheme_id:
        _send_text(phone,
            "দুঃখিত, বুঝতে পারলাম না। 1, 2, 3 বা 4 লিখুন:\n\n"
            "1️⃣ Lakshmir Bhandar\n2️⃣ Swasthya Sathi\n3️⃣ Kanyashree\n4️⃣ Yuva Sathi"
        )
        return

    scheme = get_scheme(scheme_id)
    el = scheme.get("eligibility", {})

    # Ask age first
    _send_text(phone,
        f"✅ {scheme['scheme_name_bn'] or scheme['scheme_name']} বেছে নিয়েছেন।\n\n"
        f"আপনার বয়স কত? (সংখ্যায় লিখুন)"
    )

    save_session(phone, {
        "conversation_step": "AWAITING_PROFILE",
        "scheme_id": scheme_id,
        "profile_stage": "age",
        "partial_profile": {},
        "partial_checks": {}
    })


def _handle_profile_collection(phone: str, text: str, session: dict):
    """
    Collect profile fields one at a time: age → gender → caste → district.
    Uses a stage machine within AWAITING_PROFILE state.
    """
    scheme_id       = session.get("scheme_id", "lakshmir_bhandar")
    stage           = session.get("profile_stage", "age")
    partial_profile = session.get("partial_profile", {})
    partial_checks  = session.get("partial_checks", {})
    scheme          = get_scheme(scheme_id)
    el              = scheme.get("eligibility", {}) if scheme else {}

    # ── Parse current field ────────────────────────────────────────────────────
    if stage == "age":
        age = _extract_number(text)
        if not age or age < 1 or age > 120:
            _send_text(phone, "বয়স সঠিকভাবে লিখুন। যেমন: 38")
            return

        # ── STRATEGY 2 SHORT-CIRCUIT: Early ineligibility check ───────────────
        age_min = el.get("age_min", 0)
        age_max = el.get("age_max", 999)
        if age < age_min or age > age_max:
            _send_text(phone,
                f"⛔ দুঃখিত। {scheme['scheme_name']} এর জন্য বয়স {age_min}-{age_max} হতে হবে।\n"
                f"আপনার বয়স {age} — আপনি eligible নন।\n\n"
                "অন্য scheme দেখতে '1' লিখুন।"
            )
            save_session(phone, {"conversation_step": "AWAITING_SCHEME"})
            return

        partial_profile["age"] = age

        # Check if scheme needs gender
        if el.get("gender"):
            _send_text(phone, "আপনি কি পুরুষ নাকি মহিলা? (পুরুষ/মহিলা)")
            save_session(phone, {**session, "profile_stage": "gender",
                                 "partial_profile": partial_profile})
        else:
            # Skip gender — go to caste
            _ask_caste(phone, session, partial_profile)

    elif stage == "gender":
        gender = _parse_gender(text)
        if not gender:
            _send_text(phone, "পুরুষ অথবা মহিলা লিখুন।")
            return

        partial_profile["gender"] = gender

        # ── SHORT-CIRCUIT: Gender mismatch ────────────────────────────────────
        required_gender = el.get("gender")
        if required_gender and gender != required_gender:
            _send_text(phone,
                f"⛔ {scheme['scheme_name']} শুধুমাত্র {required_gender} দের জন্য।\n"
                "অন্য scheme দেখতে '1' লিখুন।"
            )
            save_session(phone, {"conversation_step": "AWAITING_SCHEME"})
            return

        _ask_caste(phone, session, partial_profile)

    elif stage == "caste":
        caste = _parse_caste(text)
        partial_profile["caste"] = caste
        _send_text(phone, "আপনার জেলার নাম? (যেমন: Jalpaiguri, Kolkata, Murshidabad)")
        save_session(phone, {**session, "profile_stage": "district",
                             "partial_profile": partial_profile})

    elif stage == "district":
        partial_profile["district"] = text.strip().title()

        # Check employment
        if el.get("must_be_unemployed") or scheme_id == "yuva_sathi":
            _send_text(phone, "আপনি কি সরকারি চাকরি করেন? (হ্যাঁ/না)")
            save_session(phone, {**session, "profile_stage": "employment",
                                 "partial_profile": partial_profile})
        else:
            _start_doc_collection(phone, scheme_id, partial_profile, partial_checks)

    elif stage == "employment":
        is_govt = _parse_yes_no(text)
        partial_profile["is_govt_employee"] = is_govt
        partial_profile["pays_income_tax"]  = is_govt

        if is_govt:
            _send_text(phone,
                f"⛔ সরকারি কর্মচারীরা {scheme['scheme_name']} এর জন্য eligible নন।\n"
                "অন্য scheme দেখতে '1' লিখুন।"
            )
            save_session(phone, {"conversation_step": "AWAITING_SCHEME"})
            return

        _start_doc_collection(phone, scheme_id, partial_profile, partial_checks)


def _ask_caste(phone: str, session: dict, partial_profile: dict):
    _send_text(phone,
        "আপনার বর্গ কী?\n\n"
        "1️⃣ General\n2️⃣ SC (Scheduled Caste)\n3️⃣ ST (Scheduled Tribe)\n4️⃣ OBC"
    )
    save_session(phone, {**session, "profile_stage": "caste",
                         "partial_profile": partial_profile})


def _start_doc_collection(phone: str, scheme_id: str, partial_profile: dict, partial_checks: dict):
    """Move to document collection phase."""
    scheme = get_scheme(scheme_id)
    required_docs = [d for d in scheme.get("documents", []) if d.get("required")]
    doc_labels = [d["label"] for d in required_docs]

    _send_text(phone,
        f"✅ Profile সংগ্রহ হয়ে গেছে!\n\n"
        f"এখন documents চেক করব।\n\n"
        f"আপনার কাছে এগুলো আছে?\n"
        + "\n".join(f"✅ {label}" for label in doc_labels)
        + "\n\nসব আছে? (হ্যাঁ/না)"
    )
    save_session(phone, {
        "conversation_step": "AWAITING_DOCS",
        "scheme_id": scheme_id,
        "partial_profile": partial_profile,
        "partial_checks": partial_checks,
        "required_docs": [d["id"] for d in required_docs],
        "docs_present": [],
        "docs_missing": [],
        "doc_check_stage": "all_docs_check"
    })


def _handle_doc_collection(phone: str, text: str, session: dict):
    """Check which documents the user has."""
    scheme_id    = session.get("scheme_id")
    scheme       = get_scheme(scheme_id)
    required_docs = session.get("required_docs", [])
    docs_present  = session.get("docs_present", [])
    docs_missing  = session.get("docs_missing", [])

    has_all = _parse_yes_no(text)

    if has_all:
        docs_present = required_docs[:]
        docs_missing = []
    else:
        # For simplicity in MVP: ask about each doc individually
        # In a full implementation, this would be a multi-turn loop
        docs_present = [d for d in required_docs if "aadhaar" in d or "voter" in d]
        docs_missing = [d for d in required_docs if d not in docs_present]

    # Move to name collection for mismatch checks
    _send_text(phone,
        "ঠিক আছে। এখন আপনার নাম check করব।\n\n"
        "Aadhaar card-এ আপনার নাম কী? (বাংলা বা English)"
    )
    save_session(phone, {
        **session,
        "conversation_step": "AWAITING_NAMES",
        "name_stage": "aadhaar_name",
        "docs_present": docs_present,
        "docs_missing": docs_missing,
    })


def _handle_name_collection(phone: str, text: str, session: dict):
    """Collect names from each document for mismatch detection."""
    scheme_id     = session.get("scheme_id")
    name_stage    = session.get("name_stage", "aadhaar_name")
    partial_checks = session.get("partial_checks", {})

    if name_stage == "aadhaar_name":
        partial_checks["aadhaar_name"] = text.strip()
        _send_text(phone, "Bank passbook বা ATM card-এ নাম কী?")
        save_session(phone, {**session, "name_stage": "bank_name",
                             "partial_checks": partial_checks})

    elif name_stage == "bank_name":
        partial_checks["bank_name"] = text.strip()
        _send_text(phone,
            "Bank account কতদিন ধরে কোনো transaction হয়নি?\n\n"
            "1️⃣ ৬ মাসের কম\n"
            "2️⃣ ৬-১২ মাস\n"
            "3️⃣ ১ বছরের বেশি\n"
            "4️⃣ জানি না"
        )
        save_session(phone, {
            **session,
            "conversation_step": "AWAITING_BANK",
            "partial_checks": partial_checks
        })


def _handle_bank_questions(phone: str, text: str, session: dict):
    """Collect bank account status and run the full eligibility check."""
    scheme_id      = session.get("scheme_id")
    partial_profile = session.get("partial_profile", {})
    partial_checks  = session.get("partial_checks", {})
    docs_present   = session.get("docs_present", [])
    docs_missing   = session.get("docs_missing", [])

    # Parse bank inactivity
    months_map = {"1": 0, "১": 0, "2": 8, "২": 8, "3": 14, "৩": 14, "4": 0, "৪": 0}
    months_inactive = months_map.get(text.strip(), 0)

    partial_checks["bank_last_transaction_months_ago"] = months_inactive
    partial_checks["aadhaar_bank_linked"] = months_inactive < 6
    partial_checks["docs_present"] = docs_present
    partial_checks["docs_missing"]  = docs_missing
    partial_checks["address_match_ok"] = True    # assume OK in MVP

    _send_text(phone, "⏳ Check করছি... একটু অপেক্ষা করুন।")

    # ── Run eligibility engine ─────────────────────────────────────────────────
    result = run_eligibility_check(scheme_id, partial_profile, partial_checks)

    if "error" in result:
        _send_text(phone, f"❌ Error: {result['error']}")
        return

    # ── Generate AI explanation ────────────────────────────────────────────────
    profile_name = partial_profile.get("name", "").split()[0] if partial_profile.get("name") else ""
    lang         = session.get("lang", "bn")
    explanation  = generate_explanation(
        score        = result["score"],
        band         = result["band"],
        issues       = result.get("issues", []),
        scheme_name  = result.get("scheme_name", scheme_id),
        profile_name = profile_name,
        lang         = lang
    )

    # ── Save result ────────────────────────────────────────────────────────────
    save_result(phone, scheme_id, result)

    # ── Determine audio routing for this user ──────────────────────────────────
    # partial_profile is the best profile we have at this point
    use_audio = should_send_audio(partial_profile, session)

    # ── Send score ─────────────────────────────────────────────────────────────
    from src.voice.sarvam_tts import generate_score_audio
    score_url, _ = generate_score_audio(result["score"], result["band"],
                                        result.get("scheme_name", scheme_id))
    if use_audio and score_url:
        _send_voice(phone, score_url)

    # Always send text score too (audio not guaranteed on slow connections)
    score_msg = build_score_message(result["score"], result["band"],
                                    result.get("scheme_name", scheme_id))
    _send_text(phone, score_msg)

    # ── Send AI explanation ────────────────────────────────────────────────────
    if explanation:
        _send_text(phone, explanation)

    # ── Send issues ────────────────────────────────────────────────────────────
    issues = result.get("issues", [])
    if issues:
        issue_msg = build_issue_message(issues[:3])
        _send_text(phone, issue_msg)

        # Audio for top fatal issue — only if user qualifies for audio
        from src.voice.sarvam_tts import generate_issue_audio
        fatal_issues = [i for i in issues if i.get("type") == "fatal"]
        if use_audio and fatal_issues:
            top_code = fatal_issues[0].get("code", "")
            url, _ = generate_issue_audio(top_code)
            if url:
                _send_voice(phone, url)

    # ── Send roadmap ───────────────────────────────────────────────────────────
    roadmap = result.get("roadmap", [])
    if roadmap:
        roadmap_msg = build_roadmap_message(roadmap[:3])
        _send_text(phone, roadmap_msg)

    # ── Send recommendations ───────────────────────────────────────────────────
    recs = result.get("recommendations", [])
    if recs:
        rec_text = "💡 *অন্য schemes যা আপনার জন্য হতে পারে:*\n"
        for r in recs[:2]:
            rec_text += f"• {r['scheme_name_bn'] or r['scheme_name']}: {r['benefit_display']}\n"
        _send_text(phone, rec_text)

    # ── Post-result menu ───────────────────────────────────────────────────────
    _send_text(phone,
        "\n*আরও জানতে চান?*\n"
        "📜 'script' লিখুন — office-এ কী বলবেন\n"
        "🔄 'restart' লিখুন — নতুন scheme check করতে"
    )

    save_session(phone, {
        "conversation_step": "RESULT_SHOWN",
        "scheme_id": scheme_id,
        "last_result": {
            "score": result["score"],
            "band":  result["band"],
            "issues": [i.get("code") for i in issues[:3] if i.get("code")]
        },
        "partial_checks": partial_checks,
    })


def _handle_post_result(phone: str, text: str, session: dict):
    """Handle follow-up questions after result is shown."""
    t = text.lower().strip()

    if "script" in t or "office" in t or "বলব" in t or "বল" in t:
        issues = session.get("last_result", {}).get("issues", [])
        if issues:
            save_session(phone, {**session, "conversation_step": "AWAITING_SCRIPT",
                                  "pending_issue": issues[0]})
            _send_text(phone, f"কোন সমস্যার জন্য script চান?\n" +
                       "\n".join(f"{i+1}. {code}" for i, code in enumerate(issues)))
        else:
            _send_text(phone, "আপনার কোনো বড় সমস্যা নেই। সরাসরি office যান! ✅")

    elif "scheme" in t or "আরও" in t or "other" in t:
        clear_session(phone)
        _handle_start(phone)

    else:
        _send_text(phone,
            "📜 'script' — office-এ কী বলবেন\n"
            "🔄 'restart' — নতুন scheme check"
        )


def _handle_script_request(phone: str, text: str, session: dict):
    """Return the exact office script for an issue."""
    from src.engine.eligibility import get_script

    issue_code = session.get("pending_issue", "NAME_MISMATCH")
    checks     = session.get("partial_checks", {})

    script = get_script(
        issue_code,
        lang="bn",
        aadhaar_name=checks.get("aadhaar_name", ""),
        bank_name=checks.get("bank_name", "")
    )

    if script and script.get("script"):
        _send_text(phone, f"📋 *Office-এ এটি বলুন:*\n\n_{script['script']}_")
        if script.get("where"):
            _send_text(phone, f"📍 *কোথায় যাবেন:* {script['where']}")
        if script.get("form"):
            _send_text(phone, f"📝 *কোন form লাগবে:* {script['form']}")
    else:
        _send_text(phone, "এই সমস্যার জন্য script পাওয়া গেল না। BDO office-এ যোগাযোগ করুন।")

    save_session(phone, {**session, "conversation_step": "RESULT_SHOWN"})


# ── Voice Helpers ─────────────────────────────────────────────────────────────

def _transcribe_voice(phone: str, media_url: str):
    """
    Download and transcribe a WhatsApp voice note.
    Returns (transcript, is_voice) or (None, False) on failure.
    """
    from src.voice.sarvam_stt import transcribe_from_url

    _send_text(phone, "🎤 আপনার voice note শুনছি...")  # Tier 2

    result = transcribe_from_url(media_url, language="bn-IN")

    if result.get("rejected"):
        _send_text(phone, f"❌ {result['rejection_reason']}")
        return None, False

    if not result.get("success"):
        _send_text(phone, "দুঃখিত, voice note বুঝতে পারলাম না। Text-এ লিখুন।")
        return None, False

    transcript = result.get("transcript", "")
    logger.info(f"STT: '{transcript[:60]}'")
    return transcript, True


# ── Twilio Send Helpers ───────────────────────────────────────────────────────

def _send_text(phone: str, message: str):
    """Send a text message via Twilio WhatsApp. Tier 2 — always text."""
    if settings.MOCK_MODE:
        logger.info(f"MOCK SEND TEXT → {phone}: {message[:60]}")
        return

    try:
        client = get_twilio_client()
        if not client:
            logger.error("Twilio client unavailable")
            return

        client.messages.create(
            from_=get_twilio_whatsapp_number(),
            to=phone,
            body=message
        )
    except Exception as e:
        logger.error(f"Twilio send_text failed for {phone}: {e}")


def _send_voice(phone: str, media_url: str):
    """Send an audio file via Twilio WhatsApp. Tier 1 — S3 pre-signed URL."""
    if settings.MOCK_MODE:
        logger.info(f"MOCK SEND VOICE → {phone}: {media_url[:60]}")
        return

    try:
        client = get_twilio_client()
        if not client:
            return

        client.messages.create(
            from_=get_twilio_whatsapp_number(),
            to=phone,
            media_url=[media_url]
        )
    except Exception as e:
        logger.error(f"Twilio send_voice failed for {phone}: {e}")


# ── Parsing Helpers ───────────────────────────────────────────────────────────

def _extract_number(text: str) -> Optional[int]:
    """Extract first integer from text. Handles Bengali digits too."""
    # Normalize Bengali digits → ASCII
    bengali_digits = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
    normalized = text.translate(bengali_digits)
    import re
    match = re.search(r'\d+', normalized)
    return int(match.group()) if match else None


def _parse_gender(text: str) -> Optional[str]:
    t = text.lower()
    if any(k in t for k in ["female", "মহিলা", "woman", "lady", "মা", "বউ", "নারী"]):
        return "female"
    if any(k in t for k in ["male", "পুরুষ", "man", "boy", "ছেলে"]):
        return "male"
    return None


def _parse_caste(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["sc", "scheduled caste", "তফসিলি জাতি", "2", "২"]):
        return "sc"
    if any(k in t for k in ["st", "scheduled tribe", "তফসিলি উপজাতি", "3", "৩"]):
        return "st"
    if any(k in t for k in ["obc", "other backward", "4", "৪"]):
        return "obc"
    return "general"


def _parse_yes_no(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ["yes", "হ্যাঁ", "হা", "ha", "y", "1", "আছে", "আছে", "ok", "ঠিক"])


def _is_restart_command(text: str) -> bool:
    t = text.lower().strip()
    return any(k in t for k in ["restart", "reset", "শুরু", "নতুন", "start", "hi", "hello",
                                  "হ্যালো", "নমস্কার", "শুরু করুন"])