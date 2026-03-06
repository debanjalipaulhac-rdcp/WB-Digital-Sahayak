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
from src.config.aws_clients import get_bedrock_nova_client

SYSTEM_PROMPT = """You are a keyword extractor for a West Bengal government scheme chatbot.
Input is always English — translated from Bengali/Hindi by STT before reaching you.
Your job: extract clean English keywords for searching a scheme database.

Output ONLY a JSON object: {"keywords": "extracted english keywords here"}
No explanations. No other text. Just the JSON.

Rules:
- Input is always English — no translation needed
- Keep scheme names exactly (Lakshmir Bhandar, Kanyashree, Swasthya Sathi, Yuva Sathi, Rupashree, Samajik Suraksha)
- Focus on: scheme name, document type, eligibility criteria, benefit type, application process
- Remove filler words (I want to know, tell me, what is, please, hello)
- Max 10 words in keywords
- If query is a greeting or completely out of scope, return {"keywords": ""}"""

# All examples use English — STT mode="translate" converts everything before this point
EXAMPLES = [
    {"role": "user",      "content": [{"text":  "what documents are needed for lakshmir bhandar"}]},
    {"role": "assistant", "content": [{"text": '{"keywords": "Lakshmir Bhandar documents required"}'}]},
    {"role": "user",      "content": [{"text": "I want to know about yuva sathi scheme"}]},
    {"role": "assistant", "content": [{"text": '{"keywords": "Yuva Sathi eligibility benefit"}'}]},
    {"role": "user",      "content": [{"text": "how much money do you get from swasthya sathi"}]},
    {"role": "assistant", "content": [{"text": '{"keywords": "Swasthya Sathi benefit amount coverage"}'}]},
    {"role": "user",      "content": [{"text": "I am 30 years old female SC caste what scheme can I get"}]},
    {"role": "assistant", "content": [{"text": '{"keywords": "eligible schemes female age 30 SC caste"}'}]},

    {"role": "user",      "content": [{"text": "where do I apply for kanyashree"}]},

    {"role": "assistant", "content": [{"text":'{"keywords": "Kanyashree application office how to apply"}'}]},

    {"role": "user",      "content": [{"text": "hello"}]},
    {"role": "assistant", "content": [{"text": '{"keywords": ""}'}]},
    {"role": "user",      "content": [{"text": "rupashree marriage grant documents and eligibility"}]},
    {"role": "assistant", "content": [{"text": '{"keywords": "Rupashree marriage grant eligibility documents"}'}]},
]





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
        # client = _get_client()

        # Build messages with few-shot examples for better extraction
        body = EXAMPLES + [
            {
                "role": "user", 
                "content": [{"text":user_query.strip()}]
            }
        ]

        # body = json.dumps({
        #     "messages": messages,
        #     "system": [{"text": SYSTEM_PROMPT}],
        #     "inferenceConfig": {
        #         "maxTokens": 50,      # Keywords are short
        #         "temperature": 0.0,   # Deterministic extraction
        #         "topP": 1.0
        #     }
        # })
        client = get_bedrock_nova_client() 
        response = client.converse(
            modelId=settings.BEDROCK_NOVA_MICRO_MODEL_ID,
            messages = body,
            system = [{"text": SYSTEM_PROMPT}],
            inferenceConfig={
            "maxTokens": 256, 
            "temperature": 0.0,
        }
        )
        print(response["output"]["message"]["content"][0]["text"])
        # return None
        # result = json.loads(response["output"]["message"]["content"][0]["text"])
        # raw_text = result["output"]["message"]["content"][0]["text"].strip()
        
        # # Parse JSON response
        parsed = json.loads(response["output"]["message"]["content"][0]["text"])
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