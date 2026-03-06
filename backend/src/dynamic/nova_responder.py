"""
src/dynamic/nova_responder.py
Nova Lite generates English response from vector search context + user query.
Called ONLY when:
  - Static lookup missed AND
  - Vector search returned confident results (score >= 0.6)

Output is always English — translate/translator.py handles language conversion.
Responses are kept SHORT (2-3 sentences max) for audio delivery.
"""

import json
import logging
import boto3
from src.config.settings import settings
from src.dynamic.vector_search import VectorSearchResult
from src.config.aws_clients import get_bedrock_nova_client

logger = logging.getLogger(__name__)

_bedrock_client = None

SYSTEM_PROMPT = """You are WB Digital Sahayak, a helpful assistant for West Bengal government schemes.
Answer questions based ONLY on the scheme information provided to you.
Keep answers SHORT — maximum 3 sentences. This response will be spoken aloud.
Do NOT make up information. If the answer is not in the provided context, say so.
Always be specific: mention exact amounts, exact document names, exact office names."""

# Fallback for when vector search returns no confident result
OUT_OF_SCOPE_RESPONSE = "I don't have specific information about that. Please ask about West Bengal schemes like Lakshmir Bhandar, Swasthya Sathi, or Kanyashree."





def _build_context(search_result: VectorSearchResult) -> str:
    """
    Read 'content' field (full scheme JSON) from Pinecone metadata.
    Nova now has all docs, eligibility, benefits, Q&A to answer any question.
    """
    if not search_result.results:
        return ""

    parts = []
    for r in search_result.results[:2]:
        meta        = r.metadata
        raw_content = meta.get("content", "")

        if raw_content:
            try:
                scheme_data = json.loads(raw_content)
                part = json.dumps(scheme_data, indent=2, ensure_ascii=False)
            except (json.JSONDecodeError, ValueError):
                part = raw_content
        else:
            # Old format fallback — re-run seed_pinecone --delete-all to fix
            part = (
                f"Scheme: {meta.get('scheme_name', '')}\n"
                f"Benefit: {meta.get('benefit', '')}\n"
                f"Gender: {meta.get('gender', 'any')}\n"
                f"Age: {meta.get('age_min')} to {meta.get('age_max')}\n"
            )
        parts.append(part)

    return "\n\n--- NEXT SCHEME ---\n\n".join(parts)
def generate_response(
    user_query: str,
    search_result: VectorSearchResult,
    language_hint: str = "en-IN"
) -> str:
    """
    Generate English response using Nova Lite.
    Always returns English — caller translates if needed.

    Returns OUT_OF_SCOPE_RESPONSE if search is not confident.
    Returns error fallback string if Nova Lite call fails.

    Args:
        user_query:    Original user question (any language)
        search_result: From vector_search.search()
        language_hint: User's language (for future multilingual Nova support)
    """
    # Guard: don't call Nova Lite for low-confidence results
    if not search_result.is_confident:
        logger.info("Nova responder skipped — low confidence vector search")
        return OUT_OF_SCOPE_RESPONSE

    context = _build_context(search_result)
    if not context:
        return OUT_OF_SCOPE_RESPONSE

    user_message = (
        f"Scheme information:\n{context}\n\n"
        f"User question: {user_query}\n\n"
        f"Answer in English, maximum 3 short sentences suitable for audio."
    )

    try:
        client = get_bedrock_nova_client()
        body = json.dumps({
            "messages": [{"role": "user", "content": [{"text":user_message}]}],
            "system": [{"text": SYSTEM_PROMPT}],
            "inferenceConfig": {
                "maxTokens": 512,     # Short audio responses only
                "temperature": 0.1,   # Low temp = consistent, factual
                "topP": 0.9
            }
        })

        response = client.converse(
            modelId=settings.BEDROCK_NOVA_LITE_MODEL_ID,
            messages= [{"role": "user", "content": [{"text":user_message}]}],
            system= [{"text": SYSTEM_PROMPT}],
            inferenceConfig= {
                "maxTokens": 200,     # Short audio responses only
                "temperature": 0.1,   # Low temp = consistent, factual
                "topP": 0.9
            }
        )

        # result   = json.loads(response["body"].read())
        answer   = response["output"]["message"]["content"][0]["text"].strip()

        logger.info(
            f"Nova Lite response: '{user_query[:40]}' → '{answer[:80]}'"
        )
        return answer

    except Exception as e:
        logger.error(f"Nova Lite call failed: {e}")
        return "I'm having trouble answering that right now. Please try again."