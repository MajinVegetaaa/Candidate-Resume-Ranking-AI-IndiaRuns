"""Scorer modules for the 5 ranking dimensions.

Each scorer returns a float between 0.0 and 1.0.

Dimensions and weights:
    career_fit       (0.35) — Career trajectory alignment
    skill_authenticity (0.25) — Skill verification & anti-stuffing
    behavioral       (0.20) — Availability & engagement signals
    education        (0.10) — Academic background relevance
    logistics        (0.10) — Location, notice period, work mode
"""

from scorers.career_fit import score_career_fit
from scorers.skill_authenticity import score_skill_authenticity
from scorers.behavioral import score_behavioral
from scorers.education import score_education
from scorers.logistics import score_logistics
