"""
src/dynamic/vector_search.py
Pinecone vector search for scheme retrieval.
Includes confidence threshold — low-confidence results are rejected
instead of passing garbage context to Nova Lite.
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

import boto3
from pinecone import Pinecone

from src.config.settings import settings

logger = logging.getLogger(__name__)

_pinecone_index = None
_bedrock_client = None

CONFIDENCE_THRESHOLD = settings.VECTOR_CONFIDENCE_THRESHOLD  # default 0.6
TOP_K = 2   # Fetch top 2 schemes — Nova Lite context is small, don't flood it


@dataclass
class SearchResult:
    scheme_id:   str
    scheme_name: str
    score:       float       # cosine similarity 0.0–1.0
    metadata:    dict        # full Pinecone metadata


@dataclass
class VectorSearchResult:
    results:      list[SearchResult]  # sorted by score desc
    top_score:    float               # highest similarity score
    is_confident: bool                # True if top_score >= threshold
    query_used:   str                 # keywords that were searched


def _get_bedrock():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=settings.AWS_REGION
        )
    return _bedrock_client


def _get_index():
    global _pinecone_index
    if _pinecone_index is None:
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        _pinecone_index = pc.Index(settings.PINECONE_INDEX_NAME)
    return _pinecone_index


def _embed_query(text: str) -> list[float]:
    """Embed query text using Titan V2. Same model used at seed time."""
    body = json.dumps({
        "inputText": text,
        "dimensions": 1024,
        "normalize": True
    })
    response = _get_bedrock().invoke_model(
        modelId=settings.TITAN_EMBED_MODEL_ID,
        body=body,
        contentType="application/json",
        accept="application/json"
    )
    return json.loads(response["body"].read())["embedding"]


def search(keywords: str) -> VectorSearchResult:
    """
    Search Pinecone for relevant schemes using keyword embedding.

    If top result score < CONFIDENCE_THRESHOLD (0.6):
      → is_confident=False
      → caller should return "I don't have information on that" static response
      → NEVER pass low-confidence results to Nova Lite

    This prevents hallucination on off-topic queries that happen to
    partially match a scheme embedding.

    Args:
        keywords: English keyword string from keyword_extractor

    Returns VectorSearchResult with is_confident flag.
    """
    if not keywords or not keywords.strip():
        return VectorSearchResult(
            results=[], top_score=0.0,
            is_confident=False, query_used=""
        )

    try:
        # Embed the keywords
        embedding = _embed_query(keywords)

        # Query Pinecone
        index = _get_index()
        response = index.query(
            vector=embedding,
            top_k=TOP_K,
            include_metadata=True
        )

        matches = response.get("matches", [])
        if not matches:
            logger.info(f"Vector search: no matches for '{keywords}'")
            return VectorSearchResult(
                results=[], top_score=0.0,
                is_confident=False, query_used=keywords
            )

        results = [
            SearchResult(
                scheme_id=m["metadata"].get("scheme_id", ""),
                scheme_name=m["metadata"].get("scheme_name", ""),
                score=float(m["score"]),
                metadata=m["metadata"]
            )
            for m in matches
        ]

        top_score    = results[0].score
        is_confident = top_score >= CONFIDENCE_THRESHOLD

        logger.info(
            f"Vector search: '{keywords}' → top={results[0].scheme_id} "
            f"score={top_score:.3f} confident={is_confident}"
        )

        return VectorSearchResult(
            results=results,
            top_score=top_score,
            is_confident=is_confident,
            query_used=keywords
        )

    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        return VectorSearchResult(
            results=[], top_score=0.0,
            is_confident=False, query_used=keywords
        )