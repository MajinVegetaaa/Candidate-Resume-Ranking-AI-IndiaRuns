"""Scorer modules for Phase 1 rule-based ranking.

Each scorer returns a float between 0.0 and 1.0.

Primary dimensions (weighted additive):
    career_fit         (0.50) — 4 sub-scores: work_evidence, trajectory, company_quality, stability
    behavioral         (0.35) — 3 delta groups: availability, engagement, trust
    skill_authenticity (0.15) — 3 sub-scores: relevance, depth, summary

Legacy dimensions (weight = 0, kept for pipeline compatibility):
    education          (0.00)
    logistics          (0.00)

Gates (hard rejects) live exclusively in pipeline/honeypot_detector.py.
"""

from scorers.career_fit import score_career_fit
from scorers.skill_authenticity import score_skill_authenticity
from scorers.behavioral import score_behavioral
from scorers.education import score_education
from scorers.logistics import score_logistics
