"""
reasoning_generator.py - Generate human-readable reasoning for top-100 candidates.

Each reasoning string references *specific* facts from the candidate's
profile, connects them to JD requirements, and varies in tone by rank
(positive for top candidates, acknowledges gaps for lower-ranked ones).

Key design principles:
    - Every reasoning must be unique and substantively different
    - Reference specific profile facts (YoE, title, named skills, signal values)
    - Connect to specific JD requirements, not generic praise
    - Acknowledge gaps honestly where they exist
    - Vary sentence structure across candidates
"""

from config.jd_config import JD_CONFIG, ALL_JD_SKILLS

import yaml
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "reasoning_templates.yaml")
with open(CONFIG_PATH, "r") as f:
    REASONING_TEMPLATES = yaml.safe_load(f)

# Keywords used to identify the most JD-relevant career role.
_RELEVANCE_KEYWORDS = set(JD_CONFIG.get("system_building_keywords", []))

# Consulting firm names for gap detection
_CONSULTING_FIRMS = set(JD_CONFIG.get("consulting_firms", []))


def _truncate_text(text: str, max_len: int = 120) -> str:
    """Truncate text at the nearest word boundary, appending '…' if needed."""
    if len(text) <= max_len:
        return text
    truncated = text[:max_len].rsplit(' ', 1)[0]
    return truncated.rstrip('.,;:!? ') + '…'


def _find_relevant_role(career_history: list) -> dict | None:
    """Return the career role whose description best matches JD keywords."""
    best_role = None
    best_hits = 0
    for role in (career_history or []):
        desc = (role.get('description', '') or '').lower()
        hits = sum(1 for kw in _RELEVANCE_KEYWORDS if kw in desc)
        if hits > best_hits:
            best_hits = hits
            best_role = role
    return best_role


def _matched_skills_detailed(candidate: dict) -> list[dict]:
    """Return up to 4 candidate skills that match JD skills, with details."""
    matched = []
    for skill in (candidate.get('skills', []) or []):
        name = (skill.get('name', '') or '')
        name_lower = name.lower()
        for jd_skill in ALL_JD_SKILLS:
            if jd_skill.lower() in name_lower or name_lower in jd_skill.lower():
                matched.append({
                    'name': name,
                    'proficiency': skill.get('proficiency', ''),
                    'duration_months': skill.get('duration_months', 0) or 0,
                    'endorsements': skill.get('endorsements', 0) or 0,
                })
                break
        if len(matched) >= 4:
            break
    return matched


def _candidate_hash(candidate_id: str) -> int:
    """Simple hash from candidate_id for deterministic variation."""
    return sum(ord(c) for c in candidate_id) % 7


def generate_reasoning(candidate: dict, rank: int, jd: dict) -> str:
    """Produce a concise, fact-grounded reasoning string for *candidate*.

    Args:
        candidate: Full candidate dictionary (with nested profile, career_history, etc).
        rank: 1-based rank position in the final output.
        jd: Job description dictionary (typically ``JD_CONFIG``).

    Returns:
        A 1-2 sentence reasoning string for the output CSV.
    """
    profile = candidate.get('profile', {})
    signals = candidate.get('redrob_signals', {})
    career = candidate.get('career_history', []) or []

    current_title = profile.get('current_title', '') or 'Professional'
    current_company = profile.get('current_company', '') or 'N/A'
    yoe = profile.get('years_of_experience', 0) or 0
    location = profile.get('location', '') or ''
    country = profile.get('country', '') or ''

    response_rate = signals.get('recruiter_response_rate', 0) or 0
    github_score = signals.get('github_activity_score', 0) or 0
    notice = signals.get('notice_period_days', None)
    interview_rate = signals.get('interview_completion_rate', 0) or 0
    open_to_work = signals.get('open_to_work_flag', False)

    # ── Variation seed ──────────────────────────────────────────────
    cid = candidate.get('candidate_id', '')
    variant = _candidate_hash(cid)

    # ── Relevant career role ────────────────────────────────────────
    relevant_role = _find_relevant_role(career)
    matched_skills = _matched_skills_detailed(candidate)

    # ── Build reasoning parts ───────────────────────────────────────
    parts: list[str] = []

    # ── 1. Identity with rank-aware opener ──────────────────────────
    openers = REASONING_TEMPLATES["templates"]["openers"]["tier4"]["options"]
    if rank <= REASONING_TEMPLATES["templates"]["openers"]["tier1"]["max_rank"]:
        openers = REASONING_TEMPLATES["templates"]["openers"]["tier1"]["options"]
    elif rank <= REASONING_TEMPLATES["templates"]["openers"]["tier2"]["max_rank"]:
        openers = REASONING_TEMPLATES["templates"]["openers"]["tier2"]["options"]
    elif rank <= REASONING_TEMPLATES["templates"]["openers"]["tier3"]["max_rank"]:
        openers = REASONING_TEMPLATES["templates"]["openers"]["tier3"]["options"]

    opener_template = openers[variant % len(openers)]
    parts.append(opener_template.format(current_title=current_title, current_company=current_company, yoe=yoe))

    # ── 2. Career highlight — varied formats ────────────────────────
    hl_templates = REASONING_TEMPLATES["templates"]["career_highlights"]
    if relevant_role:
        role_title = relevant_role.get('title', '') or ''
        role_company = relevant_role.get('company', '') or ''
        role_dur = relevant_role.get('duration_months', 0) or 0
        role_desc = (relevant_role.get('description', '') or '').strip()
        role_industry = relevant_role.get('industry', '') or ''

        is_past_role = (role_company.lower() != current_company.lower())
        prefix_a = hl_templates["past_prefix_a"] if is_past_role else hl_templates["current_prefix_a"]
        prefix_b = hl_templates["past_prefix_b"] if is_past_role else hl_templates["current_prefix_b"]
        prefix_c = hl_templates["past_prefix_c"].format(role_company=role_company) if is_past_role else hl_templates["current_prefix_c"].format(role_company=role_company)

        if variant % 3 == 0 and role_desc:
            # Format A: Description excerpt
            excerpt = _truncate_text(role_desc, 110)
            parts.append(hl_templates["formats"]["format_a"].format(prefix_a=prefix_a, excerpt=excerpt, role_company=role_company, role_dur=role_dur))
        elif variant % 3 == 1:
            # Format B: Role + company + duration focus
            if role_industry:
                parts.append(hl_templates["formats"]["format_b_with_industry"].format(prefix_b=prefix_b, role_dur=role_dur, role_title=role_title, role_company=role_company, role_industry=role_industry))
            else:
                parts.append(hl_templates["formats"]["format_b_no_industry"].format(prefix_b=prefix_b, role_dur=role_dur, role_title=role_title, role_company=role_company))
        else:
            # Format C: Company + accomplishment hint
            if role_desc:
                first_verb = _truncate_text(role_desc.split('.')[0][:80], 80)
                parts.append(hl_templates["formats"]["format_c_with_desc"].format(prefix_c=prefix_c, first_verb=first_verb))
            else:
                parts.append(hl_templates["formats"]["format_c_no_desc"].format(prefix_b=prefix_b, role_title=role_title, role_company=role_company, role_dur=role_dur))
    elif career:
        latest = career[0]
        industry = latest.get('industry', '') or ''
        if industry:
            parts.append(f"background in {industry}")

    # ── 3. Skills — specific names with details ─────────────────────
    skill_templates = REASONING_TEMPLATES["templates"]["skills"]
    if matched_skills:
        if variant % 2 == 0:
            # Format A: Names with proficiency
            skill_strs = []
            for s in matched_skills[:3]:
                prof = s['proficiency']
                if prof and prof != 'beginner':
                    skill_strs.append(f"{s['name']} ({prof})")
                else:
                    skill_strs.append(s['name'])
            parts.append(skill_templates["format_a"].format(skill_strs=", ".join(skill_strs)))
        else:
            # Format B: Names with duration
            skill_strs = []
            for s in matched_skills[:3]:
                dur = s['duration_months']
                if dur > 0:
                    skill_strs.append(f"{s['name']} ({dur}mo)")
                else:
                    skill_strs.append(s['name'])
            parts.append(skill_templates["format_b"].format(skill_strs=", ".join(skill_strs)))

    # ── 4. Behavioral signals — specific values ─────────────────────
    beh_notes = []
    if response_rate > 0.5:
        beh_notes.append(f"recruiter response rate {response_rate:.0%}")
    elif response_rate > 0 and rank > 30:
        beh_notes.append(f"response rate only {response_rate:.0%}")

    if github_score > 30:
        beh_notes.append(f"GitHub activity {int(github_score)}/100")

    if interview_rate > 0.7 and variant % 2 == 0:
        beh_notes.append(f"interview completion {interview_rate:.0%}")

    if open_to_work and variant % 3 == 1:
        beh_notes.append("open to work")

    if beh_notes:
        parts.append("; ".join(beh_notes))

    # ── 5. Location + notice ────────────────────────────────────────
    loc_parts = []
    if location:
        loc_parts.append(location)
    if notice is not None and notice > 0:
        loc_parts.append(f"notice {notice}d")
    if loc_parts:
        parts.append(", ".join(loc_parts))

    # ── 6. Gaps — using rules from config ──────────────────
    gap_rules = REASONING_TEMPLATES["rules"]["gaps"]
    if rank >= gap_rules["min_rank_for_gaps"]:
        gaps = []
        # Consulting-only
        if career and all(
            (r.get('company', '') or '').lower() in _CONSULTING_FIRMS
            for r in career
        ):
            gaps.append(gap_rules["consulting_message"])

        # Low response rate
        if response_rate < gap_rules["low_response_rate_threshold"] and response_rate > 0:
            gaps.append(gap_rules["low_response_message"].format(response_rate=response_rate))
        elif response_rate == 0 and rank > gap_rules["no_response_rank_threshold"]:
            gaps.append(gap_rules["no_response_message"])

        # Experience concerns
        if yoe < gap_rules["low_yoe_threshold"]:
            gaps.append(gap_rules["low_yoe_message"].format(yoe=yoe))
        elif yoe > gap_rules["high_yoe_threshold"]:
            gaps.append(gap_rules["high_yoe_message"].format(yoe=yoe))

        # Location concerns
        country_lower = country.lower()
        if country_lower and country_lower != 'india' and rank > gap_rules["foreign_country_rank_threshold"]:
            gaps.append(gap_rules["foreign_country_message"].format(country=country))

        # High notice period (general)
        if notice is not None and notice > gap_rules["high_notice_threshold"] and rank > gap_rules["high_notice_rank_threshold"]:
            gaps.append(gap_rules["high_notice_message"].format(notice=notice))

        if gaps:
            parts.append("concerns: " + ", ".join(gaps[:2]))

    # ── 7. Spec-compliant concern-builder (ALL ranks) ────────────────
    # PREFERRED_CITIES from JD: Noida/Pune are ideal, major metros acceptable.
    PREFERRED_CITIES = {
        "noida", "pune", "mumbai", "delhi", "hyderabad",
        "bangalore", "bengaluru", "gurgaon", "gurugram", "ncr"
    }

    # Extract raw city from location string (e.g. "Jaipur, Rajasthan" → "jaipur")
    raw_city = (location.split(',')[0].strip().lower()) if location else ""

    flags = []

    # Flag 1: Notice > 30 days exceeds the stated buyout window
    if notice is not None and notice > 30:
        flags.append(f"notice {notice}d exceeds buyout")

    # Flag 2: City outside preferred hiring locations
    if raw_city and raw_city not in PREFERRED_CITIES:
        # Only flag if outside India entirely, or if within India but not a preferred city
        if country.lower() != 'india':
            flags.append(f"{location} not preferred (outside India)")
        else:
            flags.append(f"{raw_city.title()} not preferred location")

    # Flag 3: Rank > 80 — explicitly below typical shortlist cutoff
    # if rank > 80:
    #     flags.append("below cutoff; included as filler")

    if flags:
        parts.append("| flags: " + "; ".join(flags))

    return "; ".join(parts)
