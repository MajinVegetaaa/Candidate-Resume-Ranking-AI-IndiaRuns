"""
Logistics Fit Scorer
=====================
Evaluates how well a candidate's logistics — notice period, work mode,
and relocation willingness — align with the strict job requirements.

Note: Location is already hard-gated in pipeline/honeypot_detector.py.
This scorer is a soft scorer evaluating availability/friction for those who survive.

Module weight in final ranking: 0.10
"""

from config.jd_config import JD_CONFIG

# ── sub-score weights ───────────────────────────────────────────────
W_NOTICE      = 0.55
W_WORK_MODE   = 0.45


def score_logistics(candidate: dict, jd: dict) -> float:
    """
    Computes a 0.0 to 1.0 logistics score using a delta-additive model.
    Base score is 0.50. Deltas are added based on notice period and work mode.
    """
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    
    delta = 0.0

    # 1. Notice Period (W = 55%)
    # JD explicitly requires max 30 days. High friction otherwise.
    notice = signals.get("notice_period_days", 90)
    if notice <= 30:    delta += 0.30    # JD preferred max — ideal
    elif notice <= 60:  delta -= 0.15    # Moderate delay — manageable
    elif notice <= 90:  delta -= 0.30    # JD explicitly flags this as a problem
    else:               delta -= 0.45    # Severely delays hiring velocity

    # 2. Preferred Work Mode (W = 45%)
    # JD explicitly requires hybrid.
    mode = str(signals.get("preferred_work_mode", "")).lower()
    if mode == "hybrid":
        delta += 0.20    # Exact match
    elif mode == "flexible":
        delta += 0.10    # Can adapt
    elif mode == "onsite":
        delta += 0.05    # Over-committed but complies
    elif mode == "remote":
        delta -= 0.25    # Direct conflict with JD

    score = 0.50 + delta
    return round(max(0.0, min(1.0, score)), 4)