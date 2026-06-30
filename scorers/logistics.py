"""
Logistics Fit Scorer
=====================
Evaluates how well a candidate's logistics — location and preferred 
work mode — align with the job requirements. Notice period is handled 
as a late-stage multiplier in the main ranking loop.
"""

# ── location buckets ─────────────────────────────────────────────────
PREFERRED_LOCATIONS = {"noida", "pune"}

ACCEPTABLE_LOCATIONS = {
    "hyderabad", "mumbai", "delhi", "ncr",
    "gurgaon", "gurugram",
    "bangalore", "bengaluru",
    "chennai", "kolkata",
}

# ── renormalized sub-score weights ──────────────────────────────────
W_LOCATION    = 0.65
W_WORK_MODE   = 0.35

def score_logistics(candidate: dict, jd: dict) -> float:
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    
    # --- 1. Location Score ---
    location = str(profile.get("location", "")).lower()
    will_relocate = bool(signals.get("willing_to_relocate", False))
    
    in_preferred = any(city in location for city in PREFERRED_LOCATIONS)
    in_acceptable = any(city in location for city in ACCEPTABLE_LOCATIONS)
    
    if in_preferred:
        location_score = 1.0
    elif in_acceptable or will_relocate:
        # JD: "Open to relocation candidates from Tier-1 Indian cities"
        location_score = 0.75
    else:
        # 🚨 THE LOGISTICS KILL SWITCH
        return 0.0
        
    # It lives in redrob_signals and is called preferred_work_mode
    work_mode = str(signals.get("preferred_work_mode", "hybrid")).lower()
    
    if "hybrid" in work_mode or "flexible" in work_mode:
        work_mode_score = 1.0
    elif "onsite" in work_mode:
        work_mode_score = 0.8
    elif "remote" in work_mode:
        work_mode_score = 0.4  # Heavy penalty, JD specifically wants Hybrid
    else:
        work_mode_score = 1.0 # Default fallback
        
    # Return perfectly normalized composite
    return (W_LOCATION * location_score) + (W_WORK_MODE * work_mode_score)
