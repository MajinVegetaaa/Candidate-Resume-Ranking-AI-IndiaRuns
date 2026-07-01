"""
behavioral.py — Behavioral Scoring (Phase 1)

All 23 redrob_signals scored across 6 tiers, ordered by JD priority:

    behavioral = clamp(0.50 + tier1 + tier2 + tier3 + tier4 + tier5 + tier6, 0, 1)

Tiers (by JD priority):
    Tier 1 — Assessments  : skill_assessments (logistics moved to scorers/logistics.py)
    Tier 2 — Intent        : last_active, open_to_work, github, applications_30d, interview_rate
    Tier 3 — Responsiveness: recruiter_response_rate, avg_response_time, offer_acceptance_rate
    Tier 4 — Trust         : profile_completeness, verified_email, verified_phone, linkedin
    Tier 5 — Social Proof  : saved_by_recruiters, endorsements, profile_views, connection_count
    Tier 6 — Noise         : search_appearance, signup_date, salary_range

Design rules:
    - No hard gates — penalties only. All hard rejects live in honeypot_detector.py.
    - Missing data (-1 sentinel or absent key) → neutral delta (0.0). Never penalise absence.
    - JD skill matching is dynamic via ALL_JD_SKILLS from config.jd_config (not hardcoded).
    - Delta budget: Tier 1 carries the highest weight; Tier 6 carries near-zero weight.
"""

from datetime import datetime, date
from typing import Dict

from config.jd_config import ALL_JD_SKILLS

REFERENCE_DATE = date.today()
# Lowercase set for fast O(1) membership checks
_JD_SKILLS_LOWER: set = {s.lower() for s in ALL_JD_SKILLS}


# ══════════════════════════════════════════════════════════════════════════════
# HELPER
# ══════════════════════════════════════════════════════════════════════════════

def _days_since(date_str: str) -> int:
    """Days elapsed since *date_str*. Returns 9999 on parse failure."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return (REFERENCE_DATE - d).days
    except Exception:
        return 9999


# ══════════════════════════════════════════════════════════════════════════════
# TIER 1 — ASSESSMENTS  (max reward: +0.08 | max penalty: −0.08)
# Verified technical proof of ability to do the job.
# Work mode, notice period, and relocation are now in scorers/logistics.py.
# ══════════════════════════════════════════════════════════════════════════════

def _delta_tier1_assessments(signals: dict) -> float:
    delta = 0.0

    # ── Skill assessment scores (only verified technical proof) ───────────────
    # Dynamic match against ALL_JD_SKILLS; -1 sentinel treated as neutral.
    assessments = signals.get("skill_assessment_scores", {})
    relevant = [
        v for k, v in assessments.items()
        if any(kw in k.lower() for kw in _JD_SKILLS_LOWER)
    ]
    if relevant:
        avg = sum(relevant) / len(relevant)
        if avg < 30:
            delta -= 0.08   # Proved they cannot do the job
        elif len(relevant) >= 2 and avg > 65:
            delta += 0.08   # Multi-skill verified excellence
        elif avg > 65:
            delta += 0.04   # Single verified skill
        elif avg >= 50:
            delta += 0.01   # Modest passing performance
        # avg < 50 and not < 30 → neutral (no delta)
    # No assessments → neutral (most candidates skip this)

    return delta


# ══════════════════════════════════════════════════════════════════════════════
# TIER 2 — INTENT  (max reward: +0.27 | max penalty: −0.27)
# Measures whether the candidate is genuinely and actively in the job market.
# ══════════════════════════════════════════════════════════════════════════════

def _delta_tier2_intent(signals: dict) -> float:
    delta = 0.0

    # ── Last active date (strongest intent signal) ────────────────────────────
    days = _days_since(signals.get("last_active_date", "2020-01-01"))
    if days <= 14:      delta += 0.08    # Very recently active — hot candidate
    elif days <= 30:    delta += 0.04    # Active this month
    elif days <= 90:    pass             # Active last quarter — neutral
    elif days <= 180:   delta -= 0.07    # Gone cold
    else:               delta -= 0.14   # Dormant — likely no longer looking

    # ── Open to work flag ─────────────────────────────────────────────────────
    # NOT a hard reject (68% of top candidates are passive/employed).
    # Strong penalty to separate intent, not to eliminate.
    if signals.get("open_to_work_flag", False):
        delta += 0.07
    else:
        delta -= 0.10

    # ── GitHub activity score ─────────────────────────────────────────────────
    # -1 = no GitHub linked (common for 66% of candidates).
    gh = signals.get("github_activity_score", -1)
    if gh == -1:        delta -= 0.04   # No public coding presence (mild concern)
    elif gh > 60:       delta += 0.08   # Highly active open-source contributor
    elif gh >= 30:      delta += 0.04   # Regular commits / projects
    elif gh >= 10:      delta += 0.01   # Some activity
    # gh < 10 but linked → neutral

    # ── Applications submitted in last 30 days (2 subgroups) ─────────────────
    # Binary: in the job market or not.
    apps = signals.get("applications_submitted_30d", 0)
    if apps >= 1:
        delta += 0.04   # Actively in the market
    else:
        delta -= 0.07   # Zero applications → ghost profile / truly passive

    # ── Interview completion rate ─────────────────────────────────────────────
    # -1 = no interview history yet → neutral.
    icr = signals.get("interview_completion_rate", -1)
    if icr == -1:       pass             # New user — no history, neutral
    elif icr > 0.75:    delta += 0.04   # Reliable — shows up and engages
    elif icr >= 0.50:   delta += 0.01   # Average
    else:               delta -= 0.05   # Frequently ghosts interviews

    return delta


# ══════════════════════════════════════════════════════════════════════════════
# TIER 3 — RESPONSIVENESS  (max reward: +0.09 | max penalty: −0.07)
# Will they professionally engage once contacted?
# ══════════════════════════════════════════════════════════════════════════════

def _delta_tier3_responsiveness(signals: dict) -> float:
    delta = 0.0

    # ── Recruiter response rate ───────────────────────────────────────────────
    rrr = signals.get("recruiter_response_rate", -1)
    if rrr == -1:       pass             # No history → neutral
    elif rrr > 0.70:    delta += 0.04   # Highly responsive
    elif rrr >= 0.40:   delta += 0.01   # Average
    else:               delta -= 0.03   # Low — regularly ghosts

    # ── Average response time ─────────────────────────────────────────────────
    rt = signals.get("avg_response_time_hours", -1)
    if rt == -1:        pass             # No history → neutral
    elif rt <= 24:      delta += 0.03   # Lightning fast — extremely engaged
    elif rt <= 72:      delta += 0.01   # Quick
    else:               delta -= 0.02   # Slow (median is ~111 hrs)

    # ── Offer acceptance rate ─────────────────────────────────────────────────
    # Very sparse: 68% of candidates have -1 (never received an offer here).
    # Small deltas to avoid over-weighting sparse signal.
    oar = signals.get("offer_acceptance_rate", -1)
    if oar == -1:       pass             # No history → neutral
    elif oar > 0.60:    delta += 0.02   # Usually commits when they decide
    elif oar >= 0.30:   pass             # Sometimes → neutral
    else:               delta -= 0.02   # Rarely accepts — collects offers

    return delta


# ══════════════════════════════════════════════════════════════════════════════
# TIER 4 — TRUST  (max reward: +0.08 | max penalty: −0.05)
# Is this a real, serious person with a verifiable identity?
# ══════════════════════════════════════════════════════════════════════════════

def _delta_tier4_trust(signals: dict) -> float:
    delta = 0.0

    # ── Profile completeness ──────────────────────────────────────────────────
    pcs = signals.get("profile_completeness_score", 50)
    if pcs > 80:        delta += 0.04   # Invested serious effort — serious candidate
    elif pcs >= 60:     delta += 0.01   # Mostly complete
    else:               delta -= 0.03   # Sparse — lazy or hiding something

    # ── Email verification ────────────────────────────────────────────────────
    if signals.get("verified_email", False):
        delta += 0.01
    else:
        delta -= 0.02   # Can't confirm identity at all

    # ── Phone verification ────────────────────────────────────────────────────
    # Optional signal — many genuine candidates skip this.
    if signals.get("verified_phone", False):
        delta += 0.01
    # Not verified → neutral (no penalty)

    # ── LinkedIn connected ────────────────────────────────────────────────────
    # Strongest trust signal when present: career history can be cross-verified.
    if signals.get("linkedin_connected", False):
        delta += 0.02
    # Not connected → neutral

    return delta


# ══════════════════════════════════════════════════════════════════════════════
# TIER 5 — SOCIAL PROOF  (max reward: +0.08 | max penalty: 0.00)
# Does the market independently agree this person is worth hiring?
# All rewards, no penalties — absence of social proof ≠ bad candidate.
# ══════════════════════════════════════════════════════════════════════════════

def _delta_tier5_social_proof(signals: dict) -> float:
    delta = 0.0

    # ── Saved by recruiters in last 30 days ───────────────────────────────────
    # Unmanipulable — other recruiters voted on who looks good.
    sbr = signals.get("saved_by_recruiters_30d", 0)
    if sbr > 10:        delta += 0.04
    elif sbr >= 3:      delta += 0.01

    # ── Total endorsements received ───────────────────────────────────────────
    end = signals.get("endorsements_received", 0)
    if end > 80:        delta += 0.02
    elif end >= 30:     delta += 0.01

    # ── Profile views received in last 30 days ────────────────────────────────
    pv = signals.get("profile_views_received_30d", 0)
    if pv > 100:        delta += 0.02
    elif pv >= 30:      delta += 0.01

    # ── Connection count ──────────────────────────────────────────────────────
    # Weak signal — minimal weight.
    cc = signals.get("connection_count", 0)
    if cc > 500:        delta += 0.01

    return delta


# ══════════════════════════════════════════════════════════════════════════════
# TIER 6 — NOISE  (max reward: +0.02 | max penalty: −0.02)
# Near-zero JD signal. Minimal weights to avoid distorting the score.
# ══════════════════════════════════════════════════════════════════════════════

def _delta_tier6_noise(signals: dict) -> float:
    delta = 0.0

    # ── Search appearances in last 30 days ────────────────────────────────────
    # Platform-controlled: the algorithm decides who appears — weak candidate signal.
    sa = signals.get("search_appearance_30d", 0)
    if sa > 400:        delta += 0.01

    # ── Signup date (platform tenure) ─────────────────────────────────────────
    # Spread across 2022–2026; very weak JD signal.
    sd = _days_since(signals.get("signup_date", "2020-01-01"))
    if sd < 90:         delta += 0.01   # Recent signup — fresh motivated job seeker

    # ── Expected salary range ─────────────────────────────────────────────────
    # 26% of candidates have min > max (data bug) — treat as neutral.
    # Only penalise clearly above-market asks.
    sal = signals.get("expected_salary_range_inr_lpa", {})
    smin = sal.get("min", 0)
    smax = sal.get("max", 0)
    if smax > smin and smax > 60:
        delta -= 0.02   # Likely out of budget for this role

    return delta


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def score_behavioral(candidate: dict) -> float:
    """Compute behavioral score from redrob_signals.

    Formula:
        behavioral = clamp(0.50 + Σ(tier_deltas), 0.0, 1.0)

    All 23 redrob_signals are scored across 6 priority tiers aligned with
    the JD for a Senior AI/ML Ranking Systems Engineer (hybrid, Noida/Pune).

    No hard gates — all rejections live exclusively in honeypot_detector.py.
    Missing data (-1 sentinel) is always treated as a neutral 0.0 delta.

    Parameters
    ----------
    candidate : dict
        Full candidate profile dict (must contain 'redrob_signals' key).

    Returns
    -------
    float
        Score in [0.0, 1.0].
    """
    signals = candidate.get("redrob_signals", {})

    total_delta = (
        _delta_tier1_assessments(signals)
        + _delta_tier2_intent(signals)
        + _delta_tier3_responsiveness(signals)
        + _delta_tier4_trust(signals)
        + _delta_tier5_social_proof(signals)
        + _delta_tier6_noise(signals)
    )

    score = 0.50 + total_delta
    return round(max(0.0, min(1.0, score)), 4)
