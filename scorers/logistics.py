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
    """
    Evaluates if the candidate meets the strict logistical requirements of the JD.
    Uses a 'Kill Switch' (-100.0) to instantly disqualify candidates who cannot 
    legitimately be hired based on location or notice period.
    """
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    
    location = str(profile.get("location", "")).lower()
    
    in_target_city = "pune" in location or "noida" in location
    will_relocate = bool(signals.get("willing_to_relocate", False))
    
    if not in_target_city and not will_relocate:
        return -100.0  
        
    notice_days = signals.get("notice_period_days", 0)
    if notice_days > 30:
        return -100.0
        
    return 1.0