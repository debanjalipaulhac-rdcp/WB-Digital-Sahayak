"""
src/translate/translator.py
Amazon Translate wrapper.
Translates English responses → user's language.
Used ONLY on dynamic path (Nova Lite always responds in English).
Static Q&A is pre-translated in schemes.json — never touches this file.
"""

import logging
import boto3
from src.config.settings import settings

logger = logging.getLogger(__name__)


from src.config.aws_clients import get_translate_client


def get_short_lang_code(language_code: str) -> str:
    """
    Strip '-IN' suffix for Amazon Translate.
    "bn-IN" → "bn", "hi-IN" → "hi", "en-IN" → "en"
    Amazon Translate uses short codes, not BCP-47 with region.
    """
    return language_code.split("-")[0]

def translate_text(
    text: str,
    source_language: str,
    target_language: str
) -> str:
    """
    Translate text using Amazon Translate.
    source_language / target_language: full codes like "en-IN" or short like "en".
    Returns translated string.
    Returns original text on any failure (graceful degradation).

    Cost note: Only called for dynamic path (~20% of messages).
    Static Q&A responses are pre-translated and never hit this function.
    """
    if not text or not text.strip():
        return text
    print(source_language, target_language)
    # LANGUAGE={
    #     "hi-IN": "hi",
    #     "bn-IN": "bn",
    #     "en-IN": "en",
    # }
    source = get_short_lang_code(source_language)
    target = get_short_lang_code(target_language)

    # No-op if same language
    if source == target:
        return text

    try:
        client = get_translate_client()
        print("Translating ",source, target)
        response = client.translate_text(
            Text=text,
            SourceLanguageCode=source,
            TargetLanguageCode=target
        )
        translated = response["TranslatedText"]
        logger.info(f"Translated [{source}→{target}]: '{text[:40]}' → '{translated[:40]}'")
        return translated

    except Exception as e:
        logger.error(f"Amazon Translate failed [{source}→{target}]: {e} — returning original")
        return text   # Graceful degradation: return original English rather than crash