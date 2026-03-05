"""
src/engine/scoring.py
Calculates 0-100 application readiness score.
Pure math. Zero AI. Zero external calls.

Score breakdown:
  Eligibility rules  → 50 points  (proportional per rule)
  Documents present  → 30 points  (proportional per doc)
  Name mismatch      → 20 points  (0 / 10 / 20 based on match status)
"""

from dataclasses import dataclass, field


@dataclass
class ScoreResult:
    total: int                       # 0-100
    eligibility_points: int          # max 50
    document_points: int             # max 30
    mismatch_points: int             # 0 | 10 | 20
    missing_documents: list[str]     # doc labels that are False/missing
    failed_rules: list[str]          # rule descriptions that failed
    readiness_label: str             # "Ready to Apply" | "Almost Ready" | "Not Ready"
    breakdown: dict = field(default_factory=dict)  # full detail for API response


def calculate_score(
    eligibility_result: dict,
    documents: dict,
    mismatch_status: str = "match"
) -> ScoreResult:
    """
    eligibility_result:
        {
          "passed_rules": ["Age: 38 ✓", "Gender: Female ✓"],
          "failed_rules": ["Income: ₹1.8L exceeds limit ✗"],
          "required_documents": ["Aadhaar", "Bank Passbook", "Voter ID"]
        }

    documents:
        { "Aadhaar": True, "Bank Passbook": False, "Voter ID": True }
        True = user has it, False = missing

    mismatch_status: "match" | "partial" | "mismatch"
        Comes from mismatch.MismatchResult.status

    Returns ScoreResult with total 0-100.
    """

    passed_rules = eligibility_result.get("passed_rules", [])
    failed_rules = eligibility_result.get("failed_rules", [])
    required_docs = eligibility_result.get("required_documents", [])

    # ── ELIGIBILITY POINTS (max 50) ───────────────────────────────────────
    total_rules = len(passed_rules) + len(failed_rules)
    if total_rules == 0:
        eligibility_points = 50   # No rules = assume eligible
    else:
        eligibility_points = round((len(passed_rules) / total_rules) * 50)

    # ── DOCUMENT POINTS (max 30) ──────────────────────────────────────────
    missing_documents = []
    if not required_docs:
        document_points = 30   # No required docs = full points
    else:
        present_count = 0
        for doc in required_docs:
            has_doc = documents.get(doc, False)
            if has_doc:
                present_count += 1
            else:
                missing_documents.append(doc)
        document_points = round((present_count / len(required_docs)) * 30)

    # ── MISMATCH POINTS (max 20) ──────────────────────────────────────────
    mismatch_points_map = {
        "match":    20,
        "partial":  10,
        "mismatch": 0
    }
    mismatch_points = mismatch_points_map.get(mismatch_status, 0)

    # ── TOTAL ─────────────────────────────────────────────────────────────
    total = eligibility_points + document_points + mismatch_points
    # Clamp to 0-100 (defensive)
    total = max(0, min(100, total))

    readiness_label = get_readiness_label(total)

    breakdown = {
        "eligibility": {
            "points": eligibility_points,
            "max": 50,
            "passed": len(passed_rules),
            "failed": len(failed_rules),
            "total_rules": total_rules
        },
        "documents": {
            "points": document_points,
            "max": 30,
            "present": len(required_docs) - len(missing_documents),
            "missing": len(missing_documents),
            "total": len(required_docs)
        },
        "name_mismatch": {
            "points": mismatch_points,
            "max": 20,
            "status": mismatch_status
        }
    }

    return ScoreResult(
        total=total,
        eligibility_points=eligibility_points,
        document_points=document_points,
        mismatch_points=mismatch_points,
        missing_documents=missing_documents,
        failed_rules=failed_rules,
        readiness_label=readiness_label,
        breakdown=breakdown
    )


def get_readiness_label(score: int) -> str:
    """
    80-100 → "Ready to Apply"
    50-79  → "Almost Ready"
    0-49   → "Not Ready"
    """
    if score >= 80:
        return "Ready to Apply"
    elif score >= 50:
        return "Almost Ready"
    else:
        return "Not Ready"


def get_readiness_label_bn(score: int) -> str:
    """Bengali label for WhatsApp responses."""
    if score >= 80:
        return "আবেদনের জন্য প্রস্তুত"
    elif score >= 50:
        return "প্রায় প্রস্তুত"
    else:
        return "এখনই আবেদন করবেন না"


def get_readiness_label_hi(score: int) -> str:
    """Hindi label for WhatsApp responses."""
    if score >= 80:
        return "आवेदन के लिए तैयार"
    elif score >= 50:
        return "लगभग तैयार"
    else:
        return "अभी आवेदन न करें"