"""
career_fit.py — Career Fit Scoring Dimension (weight: 0.35)

Evaluates how well a candidate's career trajectory aligns with the target
role. This is the heaviest-weighted dimension because career trajectory is
the strongest signal for role fit.

Sub-scores and their internal weights:
    title_score      (0.25) — fuzzy match against target/red-flag titles
    desc_relevance   (0.30) — system-building keyword hits in role descriptions
    industry_score   (0.15) — product-company vs services/consulting ratio
    tenure_score     (0.10) — average tenure stability across roles
    experience_score (0.20) — years of experience vs ideal bell curve

A consulting-only multiplier (0.3) is applied when every career entry is at
a known consulting/services firm.
"""

import math

from config.jd_config import JD_CONFIG

# ── Import reference lists from JD_CONFIG (single source of truth) ───

TARGET_TITLES: list[str] = JD_CONFIG["target_titles"]
RED_FLAG_TITLES: list[str] = JD_CONFIG["red_flag_titles"]
SYSTEM_BUILDING_KEYWORDS: list[str] = JD_CONFIG["system_building_keywords"]
PRODUCT_INDUSTRIES: list[str] = JD_CONFIG["product_industries"]
CONSULTING_FIRMS: list[str] = JD_CONFIG["consulting_firms"]

# ML/AI keywords for contextual title matching (e.g., "Backend Engineer")
_ML_CONTEXT_KEYWORDS = {
    'ml', 'machine learning', 'ai', 'ranking', 'recommendation',
    'search', 'retrieval', 'embedding', 'nlp', 'data science',
    'deep learning', 'inference', 'neural', 'vector', 'model',
}


# ── Sub-score helpers ────────────────────────────────────────────────


def _title_score(candidate: dict) -> float:
    """Score title alignment using substring/containment matching.

    Returns 0.0-1.0, with a hard 0.1× penalty for red-flag titles.
    Applies seniority multipliers:
        - Junior/Intern/Trainee: 0.6×
        - Staff/Principal/Lead/Head/Director: 1.1× (capped at 1.0)
    Backend Engineer gets context-aware scoring.
    """
    profile = candidate.get("profile", {})
    raw_title: str = (profile.get("current_title") or "").lower().strip()
    if not raw_title:
        return 0.0

    # Red-flag check (hard penalty)
    for red in RED_FLAG_TITLES:
        if red in raw_title or raw_title in red:
            return 0.1  # hard penalty: multiply effective score by 0.1

    # Positive match against target titles
    best: float = 0.0
    matched_target: str = ""
    for target in TARGET_TITLES:
        if target in raw_title or raw_title in target:
            best = 1.0
            matched_target = target
            break
        # Partial overlap — check if any significant word matches
        target_words = set(target.split())
        title_words = set(raw_title.split())
        overlap = target_words & title_words
        if overlap:
            score = len(overlap) / max(len(target_words), len(title_words))
            if score > best:
                best = score
                matched_target = target

    # Context check for "Backend Engineer" — only full score if ML/AI context
    if matched_target == "backend engineer" and best >= 0.8:
        career: list[dict] = candidate.get("career_history", [])
        has_ml_context = False
        for role in career:
            desc: str = (role.get("description") or "").lower()
            if any(kw in desc for kw in _ML_CONTEXT_KEYWORDS):
                has_ml_context = True
                break
        if not has_ml_context:
            best *= 0.5  # generic backend, no ML context

    # Seniority multiplier
    if any(word in raw_title for word in ("junior", "intern", "trainee", "fresher")):
        best *= 0.6
    elif any(word in raw_title for word in ("staff", "principal", "head", "director")):
        best = min(best * 1.1, 1.0)
    # "lead" gets a small boost but not as much as staff/principal
    elif "lead" in raw_title:
        best = min(best * 1.05, 1.0)

    return best


def _description_relevance(candidate: dict) -> float:
    """Score system-building keyword hits across role descriptions.

    Scores each role independently, then combines:
        0.7 × best_role_score + 0.3 × average_role_score

    This rewards candidates with one deeply relevant role while still
    giving credit for breadth.
    """
    career: list[dict] = candidate.get("career_history", [])
    if not career:
        return 0.0

    num_keywords = len(SYSTEM_BUILDING_KEYWORDS)
    if num_keywords == 0:
        return 0.0

    role_scores: list[float] = []
    for role in career:
        desc: str = (role.get("description") or "").lower()
        hits: int = sum(1 for kw in SYSTEM_BUILDING_KEYWORDS if kw in desc)
        role_scores.append(min(hits / num_keywords, 1.0))

    max_score = max(role_scores)
    avg_score = sum(role_scores) / len(role_scores)

    return min(0.70 * max_score + 0.30 * avg_score, 1.0)


def _industry_score(candidate: dict) -> float:
    """Ratio of product-industry roles to total roles."""
    career: list[dict] = candidate.get("career_history", [])
    if not career:
        return 0.0

    product_count: int = 0
    for role in career:
        industry: str = (role.get("industry") or "").lower().strip()
        if "services" in industry or "consulting" in industry:
            continue
        if any(pi in industry for pi in PRODUCT_INDUSTRIES):
            product_count += 1

    return product_count / len(career)


def _tenure_score(candidate: dict) -> float:
    """Average tenure stability.

    < 18 months avg → title-chaser penalty (linear ramp 0→1 over 0-18).
    18-36 months    → linear ramp from 0.5 to 1.0.
    36+ months      → perfect 1.0.
    """
    career: list[dict] = candidate.get("career_history", [])
    durations = [
        r.get("duration_months", 0)
        for r in career
        if r.get("duration_months") is not None
    ]
    if not durations:
        return 0.0

    avg: float = sum(durations) / len(durations)

    if avg >= 36:
        return 1.0
    if avg >= 18:
        # Linear ramp from 0.5 at 18 to 1.0 at 36
        return 0.5 + 0.5 * ((avg - 18) / 18)
    # Below 18 months — title-chaser penalty zone
    return max(avg / 18 * 0.5, 0.0)


def _consulting_multiplier(candidate: dict) -> float:
    """Return 0.3 if ALL career entries are at known consulting firms.

    Mixed backgrounds are fine (returns 1.0).
    """
    career: list[dict] = candidate.get("career_history", [])
    if not career:
        return 1.0

    for role in career:
        company: str = (role.get("company") or "").lower().strip()
        if not any(cf in company for cf in CONSULTING_FIRMS):
            return 1.0  # at least one non-consulting role → no penalty

    return 0.3


def _experience_score(candidate: dict) -> float:
    """Bell-curve score centred at 7 years.

    Ideal range:      5-9 years  → score ≥ 0.9
    Acceptable range:  4-15 years → score ≥ 0.5
    Outside:           tapers toward 0.
    """
    profile = candidate.get("profile", {})
    yoe: float = profile.get("years_of_experience", 0) or 0

    # Gaussian centred at 7, σ chosen so that 5-9 ≈ 0.9+
    sigma: float = 3.0
    centre: float = 7.0
    score = math.exp(-0.5 * ((yoe - centre) / sigma) ** 2)
    return round(min(max(score, 0.0), 1.0), 4)


# ── Public API ───────────────────────────────────────────────────────


def score_career_fit(candidate: dict, jd: dict) -> float:
    """Compute career-fit score for *candidate* against the job description.

    Parameters
    ----------
    candidate : dict
        Parsed candidate profile containing keys like ``current_title``,
        ``career_history``, ``years_of_experience``.
    jd : dict
        Job-description config (typically ``JD_CONFIG``).

    Returns
    -------
    float
        A score in [0.0, 1.0].
    """
    title: float = _title_score(candidate)
    desc: float = _description_relevance(candidate)
    industry: float = _industry_score(candidate)
    tenure: float = _tenure_score(candidate)
    experience: float = _experience_score(candidate)
    consulting: float = _consulting_multiplier(candidate)

    # Weighted combination
    combined: float = (
        0.25 * title
        + 0.30 * desc
        + 0.15 * industry
        + 0.10 * tenure
        + 0.20 * experience
    )

    # Apply consulting-only penalty
    final: float = combined * consulting

    return round(min(max(final, 0.0), 1.0), 4)
