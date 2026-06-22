"""
Logistics Fit Scorer
=====================
Evaluates how well a candidate's logistics — location, notice
period, and preferred work mode — align with the job requirements.

Module weight in final ranking: 0.10
"""

from config.jd_config import JD_CONFIG

# ── location buckets ─────────────────────────────────────────────────
PREFERRED_LOCATIONS = {"noida", "pune"}

ACCEPTABLE_LOCATIONS = {
    "hyderabad", "mumbai", "delhi", "ncr",
    "gurgaon", "gurugram",
    "bangalore", "bengaluru",
    "chennai", "kolkata",
}

# ── sub-score weights ───────────────────────────────────────────────
W_LOCATION    = 0.40
W_NOTICE      = 0.35
W_WORK_MODE   = 0.25


# ── public entry point ───────────────────────────────────────────────

def score_logistics(candidate: dict, jd: dict) -> float:
    """Return a 0.0-1.0 logistics fit score for *candidate* vs *jd*.

    Combines location match, notice-period feasibility, and work-mode
    alignment with fixed weights.
    """
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})

    # --- Location ---
    country = (profile.get("country", "") or "").lower().strip()
    location = (profile.get("location", "") or "").lower().strip()
    willing = signals.get("willing_to_relocate", False)

    if country == "india":
        if any(loc in location for loc in PREFERRED_LOCATIONS):
            loc_score = 1.0
        elif any(loc in location for loc in ACCEPTABLE_LOCATIONS):
            loc_score = 0.7
        else:
            loc_score = 0.4 + (0.2 if willing else 0.0)
    else:
        loc_score = 0.3 if willing else 0.1

    # --- Notice period ---
    days = signals.get("notice_period_days", 90)
    if days <= 30:
        notice_score = 1.0
    elif days <= 60:
        notice_score = 0.7
    elif days <= 90:
        notice_score = 0.4
    else:
        notice_score = 0.2

    # --- Work mode ---
    mode = (signals.get("preferred_work_mode", "") or "").lower().strip()
    if mode in ("hybrid", "flexible", "onsite"):
        mode_score = 1.0
    else:
        mode_score = 0.5

    final = W_LOCATION * loc_score + W_NOTICE * notice_score + W_WORK_MODE * mode_score
    return round(min(max(final, 0.0), 1.0), 4)
