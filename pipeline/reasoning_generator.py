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

# Keywords used to identify the most JD-relevant career role.
_RELEVANCE_KEYWORDS = {
    'ranking', 'search', 'recommendation', 'retrieval', 'ml',
    'machine learning', 'nlp', 'data science', 'deep learning',
    'information retrieval', 'personalization', 'relevance',
    'embeddings', 'vector', 'inference', 'pipeline',
}

# Consulting firm names for gap detection
_CONSULTING_FIRMS = {"tcs", "infosys", "wipro", "accenture", "cognizant",
                     "capgemini", "hcl", "tech mahindra"}


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
    profile_completeness = signals.get('profile_completeness_score', 0) or 0

    # ── Variation seed ──────────────────────────────────────────────
    cid = candidate.get('candidate_id', '')
    variant = _candidate_hash(cid)

    # ── Relevant career role ────────────────────────────────────────
    relevant_role = _find_relevant_role(career)
    matched_skills = _matched_skills_detailed(candidate)

    # ── Build reasoning parts ───────────────────────────────────────
    parts: list[str] = []

    # ── 1. Identity with rank-aware opener ──────────────────────────
    if rank <= 5:
        openers = [
            f"Strong match: {current_title} at {current_company} with {yoe:.1f} years",
            f"Top candidate — {yoe:.1f}-year {current_title} at {current_company}",
            f"Excellent fit: {current_title} ({yoe:.1f} yrs) currently at {current_company}",
        ]
    elif rank <= 15:
        openers = [
            f"Solid fit: {current_title} at {current_company} ({yoe:.1f} yrs)",
            f"{yoe:.1f}-year {current_title} at {current_company} — strong profile",
            f"Well-aligned: {current_title} with {yoe:.1f} years at {current_company}",
        ]
    elif rank <= 40:
        openers = [
            f"{current_title} at {current_company} ({yoe:.1f} yrs experience)",
            f"Relevant background: {yoe:.1f}-year {current_title} at {current_company}",
            f"{current_title} with {yoe:.1f} yrs, currently at {current_company}",
        ]
    else:
        openers = [
            f"{current_title} at {current_company} ({yoe:.1f} yrs)",
            f"{yoe:.1f}-year {current_title}, based at {current_company}",
            f"Currently {current_title} at {current_company} with {yoe:.1f} yrs total",
        ]
    parts.append(openers[variant % len(openers)])

    # ── 2. Career highlight — varied formats ────────────────────────
    if relevant_role:
        role_title = relevant_role.get('title', '') or ''
        role_company = relevant_role.get('company', '') or ''
        role_dur = relevant_role.get('duration_months', 0) or 0
        role_desc = (relevant_role.get('description', '') or '').strip()
        role_industry = relevant_role.get('industry', '') or ''

        is_past_role = (role_company.lower() != current_company.lower())
        prefix_a = "past experience: " if is_past_role else "key experience: "
        prefix_b = "previously: " if is_past_role else ""
        prefix_c = f"former role at {role_company}: " if is_past_role else f"at {role_company}: "

        if variant % 3 == 0 and role_desc:
            # Format A: Description excerpt
            excerpt = _truncate_text(role_desc, 110)
            parts.append(f"{prefix_a}{excerpt} ({role_company}, {role_dur}mo)")
        elif variant % 3 == 1:
            # Format B: Role + company + duration focus
            parts.append(f"{prefix_b}served {role_dur}mo as {role_title} at {role_company}")
            if role_industry:
                parts.append(f"industry: {role_industry}")
        else:
            # Format C: Company + accomplishment hint
            if role_desc:
                first_verb = role_desc.split('.')[0][:80]
                parts.append(f"{prefix_c}{_truncate_text(first_verb, 80)}")
            else:
                parts.append(f"{prefix_b}worked as {role_title} at {role_company} ({role_dur}mo)")
    elif career:
        latest = career[0]
        industry = latest.get('industry', '') or ''
        if industry:
            parts.append(f"background in {industry}")

    # ── 3. Skills — specific names with details ─────────────────────
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
            parts.append("relevant skills: " + ", ".join(skill_strs))
        else:
            # Format B: Names with duration
            skill_strs = []
            for s in matched_skills[:3]:
                dur = s['duration_months']
                if dur > 0:
                    skill_strs.append(f"{s['name']} ({dur}mo)")
                else:
                    skill_strs.append(s['name'])
            parts.append("skills match: " + ", ".join(skill_strs))

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

    # ── 6. Gaps — only for rank > 25, with variety ──────────────────
    if rank > 25:
        gaps = []
        # Consulting-only
        if career and all(
            (r.get('company', '') or '').lower() in _CONSULTING_FIRMS
            for r in career
        ):
            gaps.append("consulting-only career history")

        # Low response rate
        if response_rate < 0.3 and response_rate > 0:
            gaps.append(f"low response rate ({response_rate:.0%})")
        elif response_rate == 0 and rank > 50:
            gaps.append("no response data")

        # Experience concerns
        if yoe < 4:
            gaps.append(f"limited experience ({yoe:.1f} yrs)")
        elif yoe > 12:
            gaps.append(f"overqualified concern ({yoe:.1f} yrs vs 5-9 ideal)")

        # Location concerns
        loc_lower = location.lower() if location else ''
        country_lower = country.lower()
        if country_lower and country_lower != 'india' and rank > 40:
            gaps.append(f"located outside India ({country})")

        # High notice period (general)
        if notice is not None and notice > 90 and rank > 50:
            gaps.append(f"long notice period ({notice}d)")

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
    if rank > 80:
        flags.append("below cutoff; included as filler")

    if flags:
        parts.append("| flags: " + "; ".join(flags))

    return "; ".join(parts)
