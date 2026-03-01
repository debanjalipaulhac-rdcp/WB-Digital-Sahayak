"""
config/bedrock_client.py
=========================
Amazon Bedrock client for AI-powered explanations.

IMPORTANT — what Bedrock does and does NOT do in this project:
  ✅ DOES: Generates natural language explanations in Bengali
  ✅ DOES: Explains WHY a score is low (from deterministic result)
  ❌ DOES NOT: Calculate eligibility (that's eligibility.py)
  ❌ DOES NOT: Make decisions (those are already made by the engine)

Why this separation matters:
  LLMs can hallucinate. If Bedrock calculated eligibility,
  it might say "you are eligible" when you're not.
  The engine is always right. Bedrock just explains it nicely.

Model: Claude Haiku (anthropic.claude-haiku-20240307-v1:0)
  - Cheapest Claude model on Bedrock
  - Fast (< 2 seconds)
  - Good enough for short explanations
  - Cost: ~$0.00025 per explanation at 1K tokens

Setup:
  1. AWS Console → Amazon Bedrock → Model Access
  2. Request access to "Claude Haiku" (Anthropic)
  3. Approval is usually instant
  4. No extra API key needed — uses AWS credentials

Usage:
    from config.bedrock_client import get_bedrock_client, generate_explanation
    explanation = generate_explanation(score_result, profile, scheme_name)
"""

import json
import logging
from .settings import settings
from .aws_clients import get_bedrock_client as _get_bedrock_boto_client

logger = logging.getLogger(__name__)


def generate_explanation(
    score: int,
    band: str,
    issues: list,
    scheme_name: str,
    profile_name: str = "",
    lang: str = "bn"
) -> str:
    """
    Generate a natural language explanation of the eligibility result.
    Called AFTER the deterministic engine runs — never instead of it.

    Args:
        score:        The readiness score (0-100)
        band:         GREEN | AMBER | RED
        issues:       List of issue dicts from eligibility engine
        scheme_name:  e.g. "Lakshmir Bhandar"
        profile_name: e.g. "Sulata" (for personalisation)
        lang:         "bn" (Bengali) | "en" (English) | "hi" (Hindi)

    Returns:
        A short (2-4 sentence) explanation in the requested language.
        Falls back to a template string if Bedrock is unavailable.

    Example output (bn):
        "Sulata, আপনার Readiness Score 42/100 কারণ Aadhaar এবং Bank-এ
         নামের গরমিল আছে এবং account 8 মাস ধরে dormant। আগে bank-এ
         গিয়ে নাম ঠিক করুন এবং account reactivate করুন। তারপর
         BDO office যান।"
    """
    # Always return fallback in MOCK_MODE or if Bedrock is unavailable
    if settings.MOCK_MODE or not settings.AWS_ACCESS_KEY_ID:
        return _fallback_explanation(score, band, issues, scheme_name, profile_name, lang)

    try:
        client = _get_bedrock_boto_client()
        prompt = _build_prompt(score, band, issues, scheme_name, profile_name, lang)

        response = client.invoke_model(
            modelId=settings.BEDROCK_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 300,
                "temperature": 0.3,       # Low temp = consistent, not creative
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            })
        )

        body = json.loads(response["body"].read())
        explanation = body["content"][0]["text"].strip()
        logger.info(f"Bedrock explanation generated ({len(explanation)} chars)")
        return explanation

    except Exception as e:
        logger.error(f"Bedrock explanation failed: {e}. Using fallback.")
        return _fallback_explanation(score, band, issues, scheme_name, profile_name, lang)


def _build_prompt(score, band, issues, scheme_name, profile_name, lang) -> str:
    """
    Build the prompt for Bedrock.
    Strict prompt — tells the model exactly what to output.
    No hallucination possible because we pass in the facts.
    """
    issue_texts = [i.get("message", "") for i in issues[:3]]   # max 3 issues
    issues_str  = "\n".join(f"- {t}" for t in issue_texts)

    lang_instruction = {
        "bn": "Respond ONLY in Bengali (বাংলা). Use simple words. Not formal Bengali.",
        "en": "Respond ONLY in English. Use simple words.",
        "hi": "Respond ONLY in Hindi. Use simple words.",
    }.get(lang, "Respond ONLY in Bengali.")

    name_part = f"The applicant's name is {profile_name}. " if profile_name else ""

    return f"""You are explaining a welfare scheme eligibility check result to a rural Indian citizen.
{name_part}
Scheme: {scheme_name}
Readiness Score: {score}/100
Status: {band}
Issues found:
{issues_str if issues_str else "No major issues found."}

{lang_instruction}
Write 2-3 short sentences explaining:
1. What the score means for them
2. The most important issue to fix first (if any)
3. What to do next

Be direct and helpful. Do not use technical jargon.
Do not invent new issues. Only explain the issues listed above."""


def _fallback_explanation(score, band, issues, scheme_name, profile_name, lang) -> str:
    """
    Template-based fallback when Bedrock is unavailable.
    Always works — no network needed.
    """
    name = f"{profile_name}, " if profile_name else ""
    fatal_count = sum(1 for i in issues if i.get("type") == "fatal")

    if lang == "bn":
        if band == "GREEN":
            return f"{name}আপনার {scheme_name} Readiness Score {score}/100। আপনি প্রস্তুত — এখনই BDO office যেতে পারেন।"
        elif band == "AMBER":
            return f"{name}আপনার Score {score}/100। {fatal_count}টি সমস্যা ঠিক করুন, তারপর BDO office যান।"
        else:
            return f"{name}আপনার Score {score}/100। এখনই যাবেন না — আগে roadmap অনুসরণ করুন। {fatal_count}টি জরুরি সমস্যা আছে।"
    elif lang == "hi":
        if band == "GREEN":
            return f"{name}आपका {scheme_name} Readiness Score {score}/100 है। आप तैयार हैं — अभी BDO office जा सकते हैं।"
        else:
            return f"{name}आपका Score {score}/100 है। पहले {fatal_count} समस्याएं ठीक करें, फिर जाएं।"
    else:
        if band == "GREEN":
            return f"{name}Your {scheme_name} Readiness Score is {score}/100. You are ready — visit the BDO office now."
        else:
            return f"{name}Your Score is {score}/100. Fix {fatal_count} issue(s) first, then visit the office."