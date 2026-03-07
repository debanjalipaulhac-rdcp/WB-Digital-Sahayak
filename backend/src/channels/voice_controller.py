"""
src/channels/voice_controller.py
POST /search-from-audio — accepts raw audio, returns transcript.

Called by the web frontend after the user stops speaking.
Uses the same Sarvam STT wrapper used by WhatsApp.
"""

import logging
from fastapi import APIRouter, UploadFile, File, Query, HTTPException
from fastapi.responses import JSONResponse

from src.voice.stt import transcribe_audio

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/search-from-audio")
async def search_from_audio(
    audio: UploadFile = File(..., description="Audio file (ogg/webm/wav/mp3)"),
    lang:  str        = Query("bn-IN", description="Language hint: bn-IN | en-IN | hi-IN"),
):
    """
    Receive audio blob from the browser after silence is detected.
    Run Sarvam STT and return the transcript.

    Frontend flow:
      1. User speaks into VoiceSearchModal
      2. 1.5s silence detected → MediaRecorder stops
      3. Blob POSTed here as multipart `audio` field
      4. Returns { transcript, language_code, confidence, is_fallback }
      5. Frontend redirects to /search?q=<transcript>
    """
    audio_bytes = await audio.read()

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file received")

    if len(audio_bytes) < 1000:           # < 1 KB → probably silence/noise only
        return JSONResponse({
            "transcript":    "",
            "language_code": lang,
            "confidence":    0.0,
            "is_fallback":   True,
            "detail":        "Audio too short — no speech detected",
        })

    logger.info(f"STT request: {len(audio_bytes)} bytes, hint_lang={lang}")

    result = transcribe_audio(audio_bytes, hint_language=lang)

    if result.is_fallback or not result.transcript.strip():
        logger.warning("STT returned empty transcript or fallback")
        return JSONResponse({
            "transcript":    "",
            "language_code": result.language_code or lang,
            "confidence":    result.confidence,
            "is_fallback":   True,
            "detail":        "Could not understand audio — please try again",
        })

    logger.info(f"STT success: '{result.transcript[:60]}' ({result.language_code})")

    return JSONResponse({
        "transcript":    result.transcript,
        "language_code": result.language_code,
        "confidence":    result.confidence,
        "is_fallback":   False,
    })