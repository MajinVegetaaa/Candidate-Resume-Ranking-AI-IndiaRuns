"""
honeypot_detector.py - Detect honeypot candidates with subtly impossible profiles or severe domain mismatches.

Each check increments a flags counter; flags >= 2 means the candidate is disqualified (composite score = 0.0).
Severe domain mismatches (G1-G6 gates) add 2 flags immediately to force a hard reject.
"""

from datetime import date, datetime
import yaml
import os

# Import classification helpers for domain gates
from scorers.career_fit import _classify_title, _classify_company
from config.jd_config import PREFERRED_LOCATIONS, ACCEPTABLE_LOCATIONS

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "ranking_config.yaml")
with open(CONFIG_PATH, "r") as f:
    RANKING_CONFIG = yaml.safe_load(f)

# Reference year for timeline calculations
CURRENT_YEAR = RANKING_CONFIG["honeypot"]["dataset_year"]
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
    """Return True if the candidate profile looks fabricated or triggers a hard gate.

    Runs timeline checks (1 flag each) and domain gates (2 flags each).
    A candidate is considered a honeypot/reject when ``flags >= 2``.
    """
    try:
        return _detect_honeypot_inner(candidate)
    except (ValueError, TypeError, KeyError, AttributeError):
        return False


def _detect_honeypot_inner(candidate: dict) -> bool:
    flags = 0

    profile = candidate.get('profile', {})
    career_history = candidate.get('career_history', []) or []
    skills = candidate.get('skills', []) or []
    education = candidate.get('education', []) or []
    years_of_experience = profile.get('years_of_experience', 0) or 0
    signals = candidate.get("redrob_signals", {})

    # ==================================================================
    # DOMAIN GATES (G1, G2, G3, G4, G6) — Add 2 flags (Instant Reject)
    # ==================================================================

    # G1: Location Mismatch (Wrong city & won't relocate)
    location = profile.get("location", "")
    country = profile.get("country", "")
    relocate = signals.get("willing_to_relocate", False)
    
    city = (location.split(",")[0].strip().lower()) if location else ""
    country_n = country.lower().strip() if country else ""
    
    if country_n == "india":
        if not relocate and city not in PREFERRED_LOCATIONS and city not in ACCEPTABLE_LOCATIONS:
            flags += 2
    else:
        if not relocate:
            flags += 2

    # G2: All career titles non-technical
    if career_history and all(_classify_title(j.get("title", "")) == "non_tech" for j in career_history):
        flags += 2

    # G4: Entire career at consulting firms
    if career_history and all(_classify_company(j.get("company", ""), j.get("industry", "")) == "consulting" for j in career_history):
        flags += 2

    # G6: Every single job < 12 months (Job Hopper)
    if career_history and all(j.get("duration_months", 12) < 12 for j in career_history):
        flags += 2

    # G7: Copy-Pasted Job Descriptions
    if career_history:
        descs = [j.get("description", "").strip() for j in career_history if j.get("description", "").strip()]
        if len(descs) > 1 and len(descs) != len(set(descs)):
            flags += 2

    # G3: Honeypot Transition (Current tech, all prior non-tech)
    current_title = profile.get("current_title", "")
    if len(career_history) >= 2 and _classify_title(current_title) in ("ml_search", "swe", "data_cloud"):
        prior = [j for j in career_history if not j.get("is_current", False)]
        if prior:
            all_prior_nontech = all(_classify_title(j.get("title", "")) == "non_tech" for j in prior)
            tech_kw = {"model", "algorithm", "data", "code", "pipeline", "api", "machine learning", "python", "cloud", "deploy", "software", "system", "ml", "ai"}
            all_desc_nontech = all(not any(kw in (j.get("description", "") or "").lower() for kw in tech_kw) for j in prior)
            if all_prior_nontech and all_desc_nontech:
                flags += 2

    if flags >= 2:
        return True

    # ==================================================================
    # TIMELINE CHECKS (Honeypot specific) — Add 1 flag each
    # ==================================================================

    # 1. Overlapping employment dates
    non_current_roles = [r for r in career_history if not r.get('is_current', False)]
    for i in range(len(non_current_roles)):
        for j in range(i + 1, len(non_current_roles)):
            start_a = _parse_date(non_current_roles[i].get('start_date', ''))
            end_a = _parse_date(non_current_roles[i].get('end_date', ''))
            start_b = _parse_date(non_current_roles[j].get('start_date', ''))
            end_b = _parse_date(non_current_roles[j].get('end_date', ''))

            if not all([start_a, end_a, start_b, end_b]):
                continue

            overlap_start = max(start_a, start_b)
            overlap_end = min(end_a, end_b)
            if (overlap_end - overlap_start).days > 30:
                flags += 2
                break
        if flags >= 2: break

    if flags >= 2: return True

    # 2. Skill duration exceeds total career
    max_skill_months = (years_of_experience * 12) + 12
    for skill in skills:
        if (skill.get('duration_months', 0) or 0) > max_skill_months:
            flags += 1
            break

    if flags >= 2: return True

    # 3. Recent-technology impossibilities
    for skill in skills:
        skill_name = (skill.get('name', '') or '').lower()
        duration = skill.get('duration_months', 0) or 0
        for tech_keyword, birth_year in TECH_BIRTH_YEARS.items():
            if tech_keyword in skill_name:
                max_months = (CURRENT_YEAR - birth_year) * 12
                if duration > max_months + 6:
                    flags += 2  # Strong signal
                break
        if flags >= 2: break

    if flags >= 2: return True

    # 4. Education timeline vs career length
    earliest_end_year = None
    for edu in education:
        end_year = edu.get('end_year')
        if end_year is not None:
            try:
                end_year = int(end_year)
                if earliest_end_year is None or end_year < earliest_end_year:
                    earliest_end_year = end_year
            except (ValueError, TypeError):
                continue

    if earliest_end_year is not None:
        if years_of_experience > (CURRENT_YEAR - earliest_end_year) + 2:
            flags += 2

    if flags >= 2: return True

    # 5. Total career duration mismatch
    total_career_months = sum((role.get('duration_months', 0) or 0) for role in career_history)
    if total_career_months > (years_of_experience * 12) + 24:
        flags += 2

    return flags >= 2
