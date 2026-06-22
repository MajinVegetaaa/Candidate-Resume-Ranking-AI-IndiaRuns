"""
Behavioral Availability Scorer
===============================
Scores how reachable and engaged a candidate currently is,
based on redrob_signals such as recency, responsiveness,
profile completeness, and verification status.

Module weight in final ranking: 0.20
"""

import math
from datetime import date, datetime

# ── reference date for recency calculations ──────────────────────────
REFERENCE_DATE = date(2026, 6, 1)

# ── sub-score weights (must sum to 1.0) ──────────────────────────────
WEIGHTS = {
    "recency":              0.20,
    "response_rate":        0.15,
    "response_time":        0.10,
    "open_to_work":         0.10,
    "interview_completion": 0.10,
    "completeness":         0.10,
    "saved":                0.05,
    "github":               0.15,
    "verification":         0.05,
}


def score_behavioral(candidate: dict) -> float:
    """Return a 0.0-1.0 behavioral availability score for *candidate*.

    Combines nine sub-signals with fixed weights to estimate how
    reachable and responsive the candidate is likely to be.
    """
    signals = candidate.get("redrob_signals", {})

    # 1. Recency — days since last_active_date
    last_active_str = signals.get("last_active_date", "")
    if last_active_str:
        try:
            last_active = datetime.strptime(last_active_str, "%Y-%m-%d").date()
            days_since = (REFERENCE_DATE - last_active).days
            if days_since < 0:
                recency = 1.0
            elif days_since <= 30:
                recency = 1.0
            elif days_since >= 180:
                recency = 0.0
            else:
                recency = max(0.0, 1.0 - (days_since - 30) / 150.0)
        except (ValueError, TypeError):
            recency = 0.0
    else:
        recency = 0.0

    # 2. Open to work
    open_to_work = 1.0 if signals.get("open_to_work_flag", False) else 0.3

    # 3. Recruiter response rate (direct 0-1)
    response_rate = float(signals.get("recruiter_response_rate", 0.0))

    # 4. Response time
    hours = signals.get("avg_response_time_hours", 72)
    response_time = max(0.0, 1.0 - hours / 72.0)

    # 5. Interview completion rate (direct 0-1)
    interview_completion = float(signals.get("interview_completion_rate", 0.0))

    # 6. Profile completeness
    completeness = signals.get("profile_completeness_score", 0) / 100.0

    # 7. Saved by recruiters
    saved_count = signals.get("saved_by_recruiters_30d", 0)
    saved = min(math.log(1 + saved_count) / 3.0, 1.0)

    # 8. GitHub activity
    github_raw = signals.get("github_activity_score", 0)
    github = max(0, github_raw) / 100.0

    # 9. Verification
    email = 1.0 if signals.get("verified_email", False) else 0.0
    phone = 1.0 if signals.get("verified_phone", False) else 0.0
    linkedin = 1.0 if signals.get("linkedin_connected", False) else 0.0
    verification = (email + phone + linkedin) / 3.0

    sub_scores = {
        "recency":              recency,
        "open_to_work":         open_to_work,
        "response_rate":        response_rate,
        "response_time":        response_time,
        "interview_completion": interview_completion,
        "completeness":         completeness,
        "saved":                saved,
        "github":               github,
        "verification":         verification,
    }

    final = sum(WEIGHTS[k] * sub_scores[k] for k in WEIGHTS)
    return round(min(max(final, 0.0), 1.0), 4)
