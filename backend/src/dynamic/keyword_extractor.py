"""
src/dynamic/keyword_extractor.py
Uses Nova Micro to extract clean search keywords from raw user query.
Nova Micro is cheap — this is the ONLY cheap model call before vector search.
Input: raw user text (may be Bengalish/Hinglish/mixed)
Output: clean English keyword string for Pinecone query
"""

import json
import logging
import boto3
from src.config.settings import settings

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a keyword extractor for a West Bengal government scheme chatbot.
Your job: take a user query (may be Bengali, Hindi, English or mixed) and extract
clean English keywords for searching a scheme database.

Output ONLY a JSON object: {"keywords": "extracted english keywords here"}
No explanations. No other text. Just the JSON.

Rules:
- Translate key concepts to English
- Keep scheme names (Lakshmir Bhandar, Kanyashree, etc.)
- Focus on: scheme name, document type, eligibility criteria, benefit type
- Max 10 words in keywords
- If query is a greeting or out of scope, return {"keywords": ""}"""

EXAMPLES = [
    {"role": "user",      "content": "লক্ষ্মীর ভাণ্ডারের জন্য কী কী কাগজ লাগে"},
    {"role": "assistant", "content": '{"keywords": "Lakshmir Bhandar documents required"}'},
    {"role": "user",      "content": "kanyashree scheme k liye kaun eligible hai"},
    {"role": "assistant", "content": '{"keywords": "Kanyashree eligibility criteria girl student"}'},
    {"role": "user",      "content": "স্বাস্থ্যসাথীতে কত টাকা পাওয়া যায়"},
    {"role": "assistant", "content": '{"keywords": "Swasthya Sathi benefit amount health coverage"}'},
    {"role": "user",      "content": "my age is 30 female sc caste what scheme can i get"},
    {"role": "assistant", "content": '{"keywords": "eligible schemes female age 30 SC caste"}'},
]

from src.config.aws_clients import get_bedrock_nova_client


def extract_keywords(user_query: str) -> str:
    """
    Extract search keywords from raw user query using Nova Micro.
    Returns English keyword string for Pinecone vector search.
    Returns empty string on failure — caller should handle gracefully.

    Nova Micro is used here (not Nova Lite) because:
    - Keyword extraction is simple, structured task
    - Nova Micro is ~4x cheaper than Nova Lite
    - Output is tiny (< 20 tokens)
    """
    if not user_query or not user_query.strip():
        return ""

    try:
        client = get_bedrock_nova_client()

        # Build messages with few-shot examples for better extraction
        messages = EXAMPLES + [
            {
                "role": "user", 
                "content":[{"text": user_query.strip()}]
            }
        ]


        response = client.converse(
            modelId=settings.BEDROCK_NOVA_MICRO_MODEL_ID,
            messages=messages,
            system=[{"text":SYSTEM_PROMPT}],
            inferenceConfig= {
                "maxTokens": 256,      # Keywords are short
                "temperature": 0.0,   # Deterministic extraction
                "topP": 1.0
            }
        )

        result = response["output"]["message"]["content"][0]["text"].strip()
        print("🤖 BEDROCK_NOVA_MICRO_MODEL_ID -> ",result)

    

        # Parse JSON response
        parsed = json.loads(result)
        keywords = parsed.get("keywords", "").strip()

        logger.info(f"Keywords extracted: '{user_query[:40]}' → '{keywords}'")
        return keywords

    except json.JSONDecodeError as e:
        logger.error(f"Nova Micro returned non-JSON: {e}")
        # Fallback: return the raw query as keywords
        return user_query[:100]

    except Exception as e:
        logger.error(f"keyword_extractor failed: {e}")
        return user_query[:100]   # Fallback to raw query