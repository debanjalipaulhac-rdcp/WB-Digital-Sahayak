#\src\engine\mismatch.py
import re
from dataclasses import dataclass

from rapidfuzz import fuzz


@dataclass
class MismatchResult:
    status: str           # "match" | "partial" | "mismatch"
    score: int            # 0-100
    aadhaar_name: str
    bank_name: str
    suggestion: str       # What to tell the user to do


def _normalize_name(name: str) -> str:
    """Lowercase, strip, remove extra spaces."""
    name = name.lower()
    name = name.strip()
    name = re.sub(r'\s+', ' ', name)
    return name


def check_name_mismatch(aadhaar_name: str, bank_name: str) -> MismatchResult:
    """
    Fuzzy name matching between Aadhaar name and Bank name.
    Normalize both names, run rapidfuzz ratio and token_sort_ratio.
    Take MAX of both scores.
    Score >= 90 → MATCH
    Score 70-89 → PARTIAL
    Score < 70  → MISMATCH
    """
    norm_aadhaar = _normalize_name(aadhaar_name)
    norm_bank = _normalize_name(bank_name)

    ratio_score = fuzz.ratio(norm_aadhaar, norm_bank)
    token_sort_score = fuzz.token_sort_ratio(norm_aadhaar, norm_bank)

    score = max(ratio_score, token_sort_score)

    if score >= 90:
        status = "match"
        suggestion = "Your Aadhaar name and bank account name match. You are good to proceed with the application."
    elif score >= 70:
        status = "partial"
        suggestion = (
            "Your Aadhaar name and bank account name are slightly different. "
            "This may cause issues during processing. "
            "Please visit your bank branch and request a name correction to match your Aadhaar card exactly."
        )
    else:
        status = "mismatch"
        suggestion = (
            "Your Aadhaar name and bank account name do not match. "
            "This will likely cause your application to be rejected. "
            "Please visit your bank branch immediately and request a name correction to exactly match your Aadhaar card."
        )

    return MismatchResult(
        status=status,
        score=int(score),
        aadhaar_name=aadhaar_name,
        bank_name=bank_name,
        suggestion=suggestion
    )


def generate_mismatch_script(result: MismatchResult, language: str) -> str:
    """
    Returns pre-written script in given language.
    Script = exact words user should say at bank counter.
    language: "bn-IN" | "hi-IN" | "en-IN"
    Pulls from hardcoded dict (no DB call, no AI).
    """
    SCRIPTS = {
        "bn-IN": {
            "match": (
                "আপনার আধার কার্ড এবং ব্যাংক অ্যাকাউন্টের নাম মিলে গেছে। আপনি আবেদন করতে পারেন।"
            ),
            "partial": (
                "আমার আধার কার্ডে নাম '{aadhaar}' কিন্তু ব্যাংক অ্যাকাউন্টে নাম '{bank}'। "
                "আমি নাম সংশোধন করতে চাই যাতে দুটো একই হয়। "
                "অনুগ্রহ করে আমাকে নাম পরিবর্তনের ফর্ম দিন।"
            ),
            "mismatch": (
                "আমার আধার কার্ডে নাম '{aadhaar}' কিন্তু ব্যাংক অ্যাকাউন্টে নাম '{bank}'। "
                "সরকারি প্রকল্পের সুবিধা পেতে হলে দুটো নাম একই হতে হবে। "
                "অনুগ্রহ করে আমাকে নাম সংশোধনের ফর্ম দিন এবং প্রক্রিয়াটি বুঝিয়ে দিন।"
            )
        },
        "hi-IN": {
            "match": (
                "आपके आधार कार्ड और बैंक खाते का नाम मेल खाता है। आप आवेदन कर सकते हैं।"
            ),
            "partial": (
                "मेरे आधार कार्ड में नाम '{aadhaar}' है लेकिन बैंक खाते में नाम '{bank}' है। "
                "मैं नाम सुधार करवाना चाहता/चाहती हूँ ताकि दोनों एक जैसे हों। "
                "कृपया मुझे नाम बदलाव का फॉर्म दें।"
            ),
            "mismatch": (
                "मेरे आधार कार्ड में नाम '{aadhaar}' है लेकिन बैंक खाते में नाम '{bank}' है। "
                "सरकारी योजना का लाभ लेने के लिए दोनों नाम एक जैसे होने चाहिए। "
                "कृपया मुझे नाम सुधार का फॉर्म दें और प्रक्रिया समझाएं।"
            )
        },
        "en-IN": {
            "match": (
                "Your Aadhaar name and bank account name match. You can proceed with the application."
            ),
            "partial": (
                "My Aadhaar card has the name '{aadhaar}' but my bank account has the name '{bank}'. "
                "I would like to correct the name so both are the same. "
                "Please give me the name change request form."
            ),
            "mismatch": (
                "My Aadhaar card has the name '{aadhaar}' but my bank account has the name '{bank}'. "
                "To receive government scheme benefits, both names must match exactly. "
                "Please provide me the name correction form and explain the process."
            )
        }
    }

    if language not in SCRIPTS:
        language = "en-IN"

    script_template = SCRIPTS[language].get(result.status, SCRIPTS[language]["mismatch"])
    script = script_template.format(
        aadhaar=result.aadhaar_name,
        bank=result.bank_name
    )
    return script