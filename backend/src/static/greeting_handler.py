"""
src/static/greeting_handler.py
Returns instant pre-built greeting response.
Zero API calls. Zero DB reads. Zero latency.
Fires when user sends "hi", "hello", "নমস্কার" etc.
"""

from dataclasses import dataclass


@dataclass
class GreetingResponse:
    text: str        # The greeting message text
    language: str    # Language code
    audio_key: str   # S3 object key (NOT full URL — resolved at runtime via s3.get_audio_url)


# FIX: audio_key format aligned with schemes.json "greetings" section
# schemes.json uses: "greetings/welcome_bn.opus"  (not "greetings/bn-IN_welcome.opus")
# S3 key format: greetings/welcome_{lang_short}.opus
GREETING_RESPONSES = {
    "bn-IN": {
        "text": (
            "নমস্কার! আমি WB Digital Sahayak। "
            "আমি আপনাকে পশ্চিমবঙ্গের সরকারি প্রকল্প সম্পর্কে সাহায্য করতে পারি। "
            "লক্ষ্মীর ভাণ্ডার, স্বাস্থ্যসাথী বা অন্য কোনো প্রকল্পের বিষয়ে জানতে চাইলে বলুন।"
        ),
        "audio_key": "greetings/welcome_bn.opus"   # matches schemes.json
    },
    "hi-IN": {
        "text": (
            "नमस्कार! मैं WB Digital Sahayak हूँ। "
            "मैं आपको पश्चिम बंगाल की सरकारी योजनाओं के बारे में सहायता कर सकता हूँ। "
            "लक्ष्मीर भाण्डार, स्वास्थ्यसाथी या किसी अन्य योजना के बारे में जानना हो तो पूछें।"
        ),
        "audio_key": "greetings/welcome_hi.opus"   # matches schemes.json
    },
    "en-IN": {
        "text": (
            "Hello! I am WB Digital Sahayak. "
            "I can help you with West Bengal government schemes. "
            "Ask me about Lakshmir Bhandar, Swasthya Sathi, Kanyashree, or any other scheme."
        ),
        "audio_key": "greetings/welcome_en.opus"   # matches schemes.json
    }
}


def get_greeting_response(language_code: str) -> GreetingResponse:
    """
    Returns instant pre-built greeting response for given language.
    Unknown / unsupported language → defaults to en-IN.
    """
    if language_code not in GREETING_RESPONSES:
        language_code = "en-IN"

    data = GREETING_RESPONSES[language_code]
    return GreetingResponse(
        text=data["text"],
        language=language_code,
        audio_key=data["audio_key"]
    )