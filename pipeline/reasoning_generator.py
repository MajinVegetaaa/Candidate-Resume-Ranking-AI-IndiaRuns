"""
reasoning_generator.py - Natural Language Generation (NLG) for Candidate Reasoning

Dynamically generates short, punchy, brutally honest, and fact-grounded sentences 
based on exact candidate data. Evaluates candidates across 5 granular tiers.
"""

from config.jd_config import JD_CONFIG, ALL_JD_SKILLS

def _matched_skills_detailed(candidate: dict) -> list[str]:
    """Return up to 3 candidate skills that match JD skills."""
    matched = []
    for skill in (candidate.get('skills', []) or []):
        name = (skill.get('name', '') or '')
        name_lower = name.lower()
        for jd_skill in ALL_JD_SKILLS:
            if jd_skill.lower() in name_lower or name_lower in jd_skill.lower():
                matched.append(name)
                break
        if len(matched) >= 3:
            break
    return matched

def _format_list(items: list[str]) -> str:
    """Format a list of strings into a proper English list (e.g. A, B, and C)."""
    if not items: return ""
    if len(items) == 1: return items[0]
    if len(items) == 2: return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"

def _candidate_hash(candidate_id: str) -> int:
    """Simple hash from candidate_id for deterministic sentence variation."""
    return sum(ord(c) for c in candidate_id) % 7

def generate_reasoning(candidate: dict, rank: int, jd: dict) -> str:
    """Produce a concise, grammatically flowing, and brutally honest reasoning string."""
    profile = candidate.get('profile', {})
    signals = candidate.get('redrob_signals', {})
    
    title = profile.get('current_title', 'Professional')
    if not title: title = 'Professional'
    
    company = profile.get('current_company', 'their current company')
    if not company or company.lower() == 'n/a': 
        company = 'their current company'
        
    yoe = profile.get('years_of_experience', 0) or 0
    
    notice = signals.get('notice_period_days', 0) or 0
    response_rate = signals.get('recruiter_response_rate', 0) or 0
    
    matched_skills = _matched_skills_detailed(candidate)
    skills_str = _format_list(matched_skills) if matched_skills else "related competencies"
    
    variant = _candidate_hash(candidate.get('candidate_id', ''))
    
    # Analyze core strengths and weaknesses
    has_good_yoe = yoe >= 4.0
    has_bad_notice = notice > 30
    has_bad_response = 0.0 < response_rate < 0.30
    
    # Formulate drawback string early so it can be injected anywhere
    drawbacks = []
    if has_bad_notice: drawbacks.append(f"a {notice}-day notice period")
    if has_bad_response: drawbacks.append(f"low historical responsiveness ({response_rate:.0%})")
    if not has_good_yoe: drawbacks.append(f"below-target experience ({yoe:.1f} yrs)")
    drawback_str = _format_list(drawbacks)

    # ─── TIER 1: Top 3 (Empirical Standouts) ──────────────────────────────────
    if rank <= 3:
        templates = [
            f"Highest empirical match. This {title} aligns {yoe:.1f} years of experience at {company} directly with core requirements like {skills_str}.",
            f"Top-scoring profile characterized by {yoe:.1f} years of direct experience as a {title} and demonstrated proficiency in {skills_str}.",
        ]
        base = templates[variant % len(templates)]
        if drawback_str:
            base += f" Note: Contains minor friction points regarding {drawback_str}."
        return base
        
    # ─── TIER 2: Rank 4 - 15 (Strong Baseline) ────────────────────────────────
    elif rank <= 15:
        templates = [
            f"Strong baseline match. A {title} with {yoe:.1f} years of tenure at {company}, possessing verified skills in {skills_str}.",
            f"Highly relevant {title} offering {yoe:.1f} years of experience. Their background at {company} strongly supports their {skills_str} capabilities.",
        ]
        base = templates[variant % len(templates)]
        if drawback_str:
            base += f" However, they carry logistical risk due to {drawback_str}."
        return base

    # ─── TIER 3: Rank 16 - 40 (Viable but Flawed) ──────────────────────────────
    elif rank <= 40:
        if drawback_str:
            templates = [
                f"A viable {title} with {yoe:.1f} years of experience and {skills_str}. They would rank higher if not penalized for {drawback_str}.",
                f"Despite possessing {skills_str}, this {yoe:.1f}-year {title} from {company} is heavily discounted by {drawback_str}.",
            ]
            return templates[variant % len(templates)]
        else:
            return f"A structurally sound {title} with {yoe:.1f} years of experience and {skills_str}, but lacks the deep semantic relevance of higher-ranked peers."

    # ─── TIER 4: Rank 41 - 80 (Partial Match) ──────────────────────────────────
    elif rank <= 80:
        templates = [
            f"Partial match. This {title} has {yoe:.1f} years of experience at {company} and some exposure to {skills_str}",
            f"An adequate {title} offering {yoe:.1f} years of experience and baseline {skills_str}"
        ]
        base = templates[variant % len(templates)]
        if drawback_str:
            return f"{base}, but their overall score is severely suppressed by {drawback_str}."
        else:
            return f"{base}, though their profile lacks sufficient depth compared to the top quartile."

    # ─── TIER 5: Rank 81 - 100 (Borderline Inclusion) ──────────────────────────
    else:
        templates = [
            f"Borderline inclusion. This {title} made the top 100 primarily due to {skills_str} keyword matching",
            f"Lowest priority shortlist candidate. While they possess {skills_str} and {yoe:.1f} years of experience"
        ]
        base = templates[variant % len(templates)]
        if drawback_str:
            return f"{base}, their viability is fundamentally compromised by {drawback_str}."
        else:
            return f"{base}, their career history fails to demonstrate strong semantic alignment with the JD."
