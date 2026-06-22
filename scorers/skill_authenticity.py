"""
skill_authenticity.py — Skill Authenticity Scoring Dimension (weight: 0.25)

Unlike a naive "count matching skills" approach, this module evaluates how
*authentic* each claimed skill is by combining four signals:

    1. Proficiency level   (beginner → expert)
    2. Endorsement count   (log-scaled)
    3. Duration of use     (months, capped at 48)
    4. Assessment score    (from Redrob platform signals)

It also detects **keyword stuffing** — candidates who list many skills at
beginner level with zero endorsements and zero duration. When ≥ 5 such
skills are detected, the final score is heavily penalised (× 0.3).

Must-have skills receive a 1.5× multiplier before aggregation so they
carry more weight than nice-to-have skills.
"""

import math

from config.jd_config import JD_CONFIG, ALL_JD_SKILLS

# ── Proficiency mapping ──────────────────────────────────────────────────

PROFICIENCY_MAP: dict[str, float] = {
    "beginner": 0.25,
    "intermediate": 0.50,
    "advanced": 0.75,
    "expert": 1.00,
}


# ── Helpers ──────────────────────────────────────────────────────────────


def _skill_matches(skill_name: str, reference_list: list[str]) -> bool:
    """Case-insensitive substring match of *skill_name* against any entry
    in *reference_list*."""
    skill_lower = skill_name.lower().strip()
    for ref in reference_list:
        ref_lower = ref.lower().strip()
        if skill_lower in ref_lower or ref_lower in skill_lower:
            return True
    return False


def _per_skill_authenticity(
    skill: dict,
    assessment_scores: dict[str, float],
) -> float:
    """Compute authenticity score for a single candidate skill.

    Returns a value in [0.0, 1.0] by equally weighting:
        proficiency  (0.25)
        endorsements (0.25)
        duration     (0.25)
        assessment   (0.25)
    """
    # 1. Proficiency
    prof_label: str = (skill.get("proficiency") or "").lower().strip()
    proficiency: float = PROFICIENCY_MAP.get(prof_label, 0.0)

    # 2. Endorsements — log-scaled, capped at 1.0
    endorsements_raw: int = skill.get("endorsements", 0) or 0
    endorsements: float = min(math.log(1 + endorsements_raw) / 4.0, 1.0)

    # 3. Duration — months / 48, capped at 1.0
    duration_months: float = skill.get("duration_months", 0) or 0
    duration: float = min(duration_months / 48.0, 1.0)

    # 4. Assessment from Redrob signals
    skill_name_lower: str = skill.get("name", "").lower().strip()
    assessment: float = 0.0
    for key, val in assessment_scores.items():
        if key.lower().strip() == skill_name_lower:
            assessment = min(val / 100.0, 1.0)
            break

    return 0.25 * proficiency + 0.25 * endorsements + 0.25 * duration + 0.25 * assessment


def _is_keyword_stuffed(skill: dict) -> bool:
    """Detect a single stuffed-keyword entry: beginner + 0 endorsements +
    0/missing duration."""
    prof: str = (skill.get("proficiency") or "").lower().strip()
    endorsements: int = skill.get("endorsements", 0) or 0
    duration: float = skill.get("duration_months", 0) or 0

    return prof == "beginner" and endorsements == 0 and duration == 0


# ── Public API ───────────────────────────────────────────────────────────


def score_skill_authenticity(candidate: dict, jd: dict) -> float:
    """Compute skill-authenticity score for *candidate*.

    Parameters
    ----------
    candidate : dict
        Candidate profile.  Expected keys:
        - ``skills``: list of dicts each with ``name``, ``proficiency``,
          ``endorsements``, ``duration_months``.
        - ``redrob_signals.skill_assessment_scores``: dict mapping skill
          names to numeric scores (0-100).
    jd : dict
        Job-description config (typically ``JD_CONFIG``).

    Returns
    -------
    float
        Score in [0.0, 1.0].
    """
    must_have: list[str] = jd.get("must_have_skills", [])
    nice_to_have: list[str] = jd.get("nice_to_have_skills", [])

    # Assessment scores from Redrob platform signals
    redrob_signals: dict = candidate.get("redrob_signals") or {}
    assessment_scores: dict[str, float] = redrob_signals.get(
        "skill_assessment_scores", {}
    )

    candidate_skills: list[dict] = candidate.get("skills") or []

    weighted_auth_sum: float = 0.0
    keyword_stuff_count: int = 0

    for skill in candidate_skills:
        skill_name: str = skill.get("name", "")

        is_must_have: bool = _skill_matches(skill_name, must_have)
        is_nice_to_have: bool = _skill_matches(skill_name, nice_to_have)

        if not (is_must_have or is_nice_to_have):
            continue  # skill doesn't match any JD requirement

        # Per-skill authenticity
        auth: float = _per_skill_authenticity(skill, assessment_scores)

        # Must-have skills get a 1.5× boost
        if is_must_have:
            auth *= 1.5

        weighted_auth_sum += auth

        # Keyword-stuffing detection (only for matching skills)
        if _is_keyword_stuffed(skill):
            keyword_stuff_count += 1

    # Normalize by matched skills count (capped at 10) rather than total
    # must-have list size (~30). Prevents score compression.
    matched_count = sum(
        1 for skill in candidate_skills
        if _skill_matches(skill.get('name', ''), must_have)
        or _skill_matches(skill.get('name', ''), nice_to_have)
    )
    denominator: int = min(max(matched_count, 1), 10)
    base: float = weighted_auth_sum / denominator

    # Keyword-stuffing penalty
    if keyword_stuff_count >= 5:
        base *= 0.3

    return round(min(max(base, 0.0), 1.0), 4)
