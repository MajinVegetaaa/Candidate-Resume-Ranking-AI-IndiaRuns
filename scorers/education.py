"""
Education Background Scorer
============================
Evaluates a candidate's educational background by scoring
institution tier, field-of-study relevance, and degree level.

The best score across all education entries is returned.

Module weight in final ranking: 0.10
"""

# ── institution tier mapping ─────────────────────────────────────────
TIER_SCORES = {
    "tier_1":  1.00,
    "tier_2":  0.75,
    "tier_3":  0.50,
    "tier_4":  0.25,
    "unknown": 0.35,
}

# ── relevant fields of study (lowercased keywords) ──────────────────
RELEVANT_FIELDS = {
    "computer science",
    "cs",
    "information technology",
    "it",
    "data science",
    "artificial intelligence",
    "ai",
    "machine learning",
    "ml",
    "mathematics",
    "statistics",
    "electronics",
    "electrical",
}

# ── degree level mapping (checked via case-insensitive *contains*) ───
# Order matters: more specific strings are checked first so that
# e.g. "m.tech" is matched before the shorter "m." prefix.
DEGREE_SCORES = [
    (["ph.d", "phd", "doctorate"],          1.00),
    (["m.tech", "mtech"],                   0.90),
    (["m.e.", "me "],                        0.85),
    (["m.sc", "msc"],                       0.80),
    (["mba"],                               0.60),
    (["b.tech", "btech"],                   0.70),
    (["b.e.", "be "],                        0.65),
    (["b.sc", "bsc"],                       0.60),
]
DEFAULT_DEGREE_SCORE = 0.50

# ── sub-score weights ───────────────────────────────────────────────
W_TIER  = 0.40
W_FIELD = 0.35
W_DEGREE = 0.25


def _tier_score(tier: str) -> float:
    """Map institution tier label to a 0-1 score."""
    return TIER_SCORES.get(tier.lower().strip(), TIER_SCORES["unknown"])


def _field_relevance(field_of_study: str) -> float:
    """1.0 if the field matches a known relevant keyword, else 0.3."""
    field_lower = field_of_study.lower()
    for keyword in RELEVANT_FIELDS:
        if keyword in field_lower:
            return 1.0
    return 0.3


def _degree_score(degree: str) -> float:
    """Map a degree string to a 0-1 score via substring matching."""
    degree_lower = degree.lower()
    for substrings, score in DEGREE_SCORES:
        for s in substrings:
            if s in degree_lower:
                return score
    return DEFAULT_DEGREE_SCORE


def _score_single_entry(entry: dict) -> float:
    """Score one education entry: 0.40*tier + 0.35*field + 0.25*degree."""
    tier  = _tier_score(entry.get("tier", "unknown"))
    field = _field_relevance(entry.get("field_of_study", ""))
    degree = _degree_score(entry.get("degree", ""))
    return W_TIER * tier + W_FIELD * field + W_DEGREE * degree


# ── public entry point ───────────────────────────────────────────────

def score_education(candidate: dict) -> float:
    """Return a 0.0-1.0 education score for *candidate*.

    Scores each education entry on tier, field relevance, and degree
    level, then returns the **best** score.  Defaults to 0.3 when
    no education data is present.
    """
    education_list = candidate.get("education", [])
    if not education_list:
        return 0.3

    best = max(_score_single_entry(entry) for entry in education_list)
    return round(min(max(best, 0.0), 1.0), 4)
