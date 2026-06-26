"""
honeypot_detector.py - Detect honeypot candidates with subtly impossible profiles.

Approximately ~80 candidates in the dataset have fabricated profiles.
If >10% of the top 100 ranked candidates are honeypots, the submission
is disqualified. Each check increments a flags counter; flags >= 2
means honeypot.
"""

from datetime import date, datetime

import yaml
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "ranking_config.yaml")
with open(CONFIG_PATH, "r") as f:
    RANKING_CONFIG = yaml.safe_load(f)

# Reference year for timeline calculations (hackathon dataset year)
CURRENT_YEAR = RANKING_CONFIG["honeypot"]["dataset_year"]

# Technologies and the year they were first publicly available.
# Used to detect impossible skill duration claims.
TECH_BIRTH_YEARS = RANKING_CONFIG["honeypot"]["tech_birth_years"]

def _parse_date(date_str: str) -> date | None:
    """Try common date formats and return a date object, or None."""
    if not date_str:
        return None
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y', '%d-%m-%Y', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def detect_honeypot(candidate: dict) -> bool:
    """Return True if the candidate profile looks fabricated.

    Runs five independent checks, each incrementing a *flags* counter.
    A candidate is considered a honeypot when ``flags >= 2``.
    """
    try:
        return _detect_honeypot_inner(candidate)
    except (ValueError, TypeError, KeyError, AttributeError):
        # Never crash the pipeline on a malformed record.
        return False


def _detect_honeypot_inner(candidate: dict) -> bool:
    flags = 0

    profile = candidate.get('profile', {})
    career_history = candidate.get('career_history', []) or []
    skills = candidate.get('skills', []) or []
    education = candidate.get('education', []) or []
    years_of_experience = profile.get('years_of_experience', 0) or 0

    # ------------------------------------------------------------------
    # 1. Overlapping employment dates
    # ------------------------------------------------------------------
    non_current_roles = [
        role for role in career_history
        if not role.get('is_current', False)
    ]
    for i in range(len(non_current_roles)):
        for j in range(i + 1, len(non_current_roles)):
            role_a = non_current_roles[i]
            role_b = non_current_roles[j]

            start_a = _parse_date(role_a.get('start_date', ''))
            end_a = _parse_date(role_a.get('end_date', ''))
            start_b = _parse_date(role_b.get('start_date', ''))
            end_b = _parse_date(role_b.get('end_date', ''))

            if not all([start_a, end_a, start_b, end_b]):
                continue

            overlap_start = max(start_a, start_b)
            overlap_end = min(end_a, end_b)
            overlap_days = (overlap_end - overlap_start).days

            if overlap_days > 30:
                flags += 1
                break  # One overlap pair is enough for this check.
        if flags:
            break

    # ------------------------------------------------------------------
    # 2. Skill duration exceeds total career
    # ------------------------------------------------------------------
    max_skill_months = (years_of_experience * 12) + 12
    for skill in skills:
        duration = skill.get('duration_months', 0) or 0
        if duration > max_skill_months:
            flags += 1
            break  # One violation is sufficient.

    # ------------------------------------------------------------------
    # 3. Recent-technology impossibilities
    # ------------------------------------------------------------------
    for skill in skills:
        skill_name = (skill.get('name', '') or '').lower()
        duration = skill.get('duration_months', 0) or 0
        for tech_keyword, birth_year in TECH_BIRTH_YEARS.items():
            if tech_keyword in skill_name:
                max_months = (CURRENT_YEAR - birth_year) * 12
                if duration > max_months + 6:
                    flags += 2  # Strong signal.
                break  # Only match the first matching tech per skill.

    # ------------------------------------------------------------------
    # 4. Education timeline vs career length
    # ------------------------------------------------------------------
    earliest_end_year = None
    for edu in education:
        end_year = edu.get('end_year')
        if end_year is not None:
            try:
                end_year = int(end_year)
            except (ValueError, TypeError):
                continue
            if earliest_end_year is None or end_year < earliest_end_year:
                earliest_end_year = end_year

    if earliest_end_year is not None:
        if years_of_experience > (CURRENT_YEAR - earliest_end_year) + 2:
            flags += 1

    # ------------------------------------------------------------------
    # 5. Total career duration mismatch
    # ------------------------------------------------------------------
    total_career_months = sum(
        (role.get('duration_months', 0) or 0) for role in career_history
    )
    if total_career_months > (years_of_experience * 12) + 24:
        flags += 1

    return flags >= 2
