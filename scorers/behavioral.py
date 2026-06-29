"""
behavioral.py — Behavioral Scoring (Phase 1)

Delta-based scorer with 3 signal groups:

    behavioral = clamp(0.50 + availability + engagement + trust, 0, 1)

Groups:
    availability — open_to_work, notice period, recency
    engagement   — response rate, response time, interview completion, github, verified skills
    trust        — verification status, profile completeness, saved by recruiters

No gate checks here — gates live exclusively in honeypot_detector.py.
"""

from datetime import datetime, date
from typing import Any, Dict


REFERENCE_DATE = date(2026, 6, 29)

# JD-relevant skill names for verified-skill matching
JD_SKILL_KEYWORDS = {
    "faiss", "pinecone", "qdrant", "weaviate", "milvus",
    "elasticsearch", "embedding", "embeddings", "sentence transformer",
    "recommendation", "ranking", "learning to rank", "ndcg",
    "pytorch", "tensorflow", "scikit-learn", "mlflow",
    "nlp", "natural language processing", "llm", "rag",
    "xgboost", "lightgbm", "feature engineering",
}


# ══════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════

def _days_since(date_str: str) -> int:
    """Days since a date string. Returns 9999 on parse failure."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return (REFERENCE_DATE - d).days
    except Exception:
        return 9999


# ══════════════════════════════════════════════════════════════════════════
# DELTA GROUP 1: AVAILABILITY (range: -0.20 → +0.15)
# ══════════════════════════════════════════════════════════════════════════

def _delta_availability(signals: dict) -> float:
    delta = 0.0

    # Open to work
    if signals.get("open_to_work_flag", False):
        delta += 0.05
    else:
        delta -= 0.05

    # Notice period
    notice = signals.get("notice_period_days", 60)
    if notice <= 30:    delta += 0.05
    elif notice <= 60:  delta += 0.02
    elif notice <= 90:  pass
    else:               delta -= 0.05

    # Last active
    days = _days_since(signals.get("last_active_date", "2020-01-01"))
    if days <= 14:      delta += 0.05
    elif days <= 30:    delta += 0.02
    elif days <= 90:    pass
    elif days <= 180:   delta -= 0.05
    else:               delta -= 0.10

    return delta


# ══════════════════════════════════════════════════════════════════════════
# DELTA GROUP 2: ENGAGEMENT (range: -0.15 → +0.20)
# Merges old B2 (response/interview) + B4 (github) + B5 (verified skills)
# ══════════════════════════════════════════════════════════════════════════

def _delta_engagement(signals: dict) -> float:
    delta = 0.0

    # Recruiter response rate
    rrr = signals.get("recruiter_response_rate", 0.5)
    if rrr > 0.7:       delta += 0.04
    elif rrr >= 0.4:     delta += 0.01
    else:                delta -= 0.04

    # Response time
    rt = signals.get("avg_response_time_hours", 120)
    if rt <= 24:         delta += 0.03
    elif rt <= 72:       delta += 0.01
    else:                delta -= 0.03

    # Interview completion
    icr = signals.get("interview_completion_rate", 0.5)
    if icr > 0.75:       delta += 0.03
    elif icr >= 0.5:     delta += 0.01
    else:                delta -= 0.03

    # GitHub activity
    gh = signals.get("github_activity_score", -1)
    if gh == -1:         delta -= 0.03
    elif gh > 60:        delta += 0.07
    elif gh >= 30:       delta += 0.03
    elif gh >= 10:       delta += 0.01

    # Verified skill assessments (JD-relevant only)
    assessments = signals.get("skill_assessment_scores", {})
    if assessments:
        relevant = [v for k, v in assessments.items() if any(kw in k.lower() for kw in JD_SKILL_KEYWORDS)]
        if relevant:
            avg = sum(relevant) / len(relevant)
            if len(relevant) >= 2 and avg > 65: delta += 0.06
            elif avg > 65:                       delta += 0.03
            elif avg >= 50:                      delta += 0.01

    return delta


# ══════════════════════════════════════════════════════════════════════════
# DELTA GROUP 3: TRUST (range: -0.05 → +0.10)
# Merges old B3 (platform activity) + B6 (verification)
# ══════════════════════════════════════════════════════════════════════════

def _delta_trust(signals: dict) -> float:
    delta = 0.0

    # Verification
    email = signals.get("verified_email", False)
    phone = signals.get("verified_phone", False)
    linkedin = signals.get("linkedin_connected", False)

    if not email and not phone:
        delta -= 0.03
    else:
        if email:    delta += 0.01
        if phone:    delta += 0.01
        if linkedin: delta += 0.01

    # Profile completeness
    pcs = signals.get("profile_completeness_score", 50)
    if pcs > 80:     delta += 0.03
    elif pcs >= 60:  delta += 0.01
    else:            delta -= 0.02

    # Saved by recruiters (social proof)
    sbr = signals.get("saved_by_recruiters_30d", 0)
    if sbr > 10:     delta += 0.03
    elif sbr >= 3:   delta += 0.01

    return delta


# ══════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════

def score_behavioral(candidate: dict) -> float:
    """Compute behavioral score from redrob_signals.

    behavioral = clamp(0.50 + availability + engagement + trust, 0, 1)

    No gate checks — gates live exclusively in honeypot_detector.py.

    Parameters
    ----------
    candidate : dict
        Candidate profile.

    Returns
    -------
    float
        Score in [0.0, 1.0].
    """
    signals = candidate.get("redrob_signals", {})

    total_delta = (
        _delta_availability(signals)
        + _delta_engagement(signals)
        + _delta_trust(signals)
    )

    score = 0.50 + total_delta
    return round(max(0.0, min(1.0, score)), 4)
