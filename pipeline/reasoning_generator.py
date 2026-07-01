"""
reasoning_generator.py - Natural Language Generation (NLG) for Candidate Reasoning

Dynamically generates short, punchy, human-like sentences without relying on 
rigid YAML templates or semicolons. Uses proper grammar and context-aware tone.
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
    """Produce a concise, grammatically flowing reasoning string for *candidate*."""
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
    open_to_work = signals.get('open_to_work_flag', False)
    
    matched_skills = _matched_skills_detailed(candidate)
    skills_str = _format_list(matched_skills) if matched_skills else "relevant core competencies"
    
    variant = _candidate_hash(candidate.get('candidate_id', ''))
    
    # Analyze core strengths and weaknesses
    has_good_yoe = yoe >= 4.0
    has_bad_notice = notice > 30
    has_bad_response = 0.0 < response_rate < 0.30
    
    # ─── Top Tier (Rank 1 - 15) ───────────────────────────────────────────────
    if rank <= 15:
        templates = [
            f"An exceptional {title} bringing {yoe:.1f} years of experience from {company}. They possess highly relevant expertise in {skills_str}.",
            f"A top-tier {title} with {yoe:.1f} years of experience. Their background at {company} and proficiency in {skills_str} makes them a perfect fit.",
            f"Highly recommended. This {title} offers {yoe:.1f} years of deep experience at {company}, backed by strong fundamentals in {skills_str}."
        ]
        base = templates[variant % len(templates)]
        if open_to_work and variant % 2 == 0:
            base += " Additionally, they are actively open to new opportunities."
        return base
        
    # ─── Mid Tier (Rank 16 - 50) ──────────────────────────────────────────────
    elif rank <= 50:
        templates = [
            f"A solid {title} with {yoe:.1f} years of experience at {company}. They possess relevant skills like {skills_str}",
            f"Demonstrates strong capability as a {title} with {yoe:.1f} years of experience, particularly in {skills_str}",
            f"A well-rounded {title} offering {yoe:.1f} years of experience from {company}, highlighting {skills_str}"
        ]
        base = templates[variant % len(templates)]
        
        if has_bad_notice:
            base += f", though their {notice}-day notice period is a minor hurdle."
        elif has_bad_response:
            base += f", but historical recruiter response rates are somewhat low."
        elif not has_good_yoe:
            base += f", though they fall slightly below the target experience range."
        else:
            base += "."
        return base
        
    # ─── Lower Tier (Rank 51 - 100) ───────────────────────────────────────────
    else:
        # Construct a "Why they ranked low" narrative
        drawbacks = []
        if has_bad_notice:
            drawbacks.append(f"a long {notice}-day notice period")
        if has_bad_response:
            drawbacks.append("historically low responsiveness")
        if not has_good_yoe:
            drawbacks.append("falling short of the ideal experience range")
            
        drawback_str = _format_list(drawbacks)
        
        templates = [
            f"While this {title} possesses {yoe:.1f} years of experience and {skills_str}",
            f"Despite having {skills_str} and {yoe:.1f} years as a {title}",
            f"Although they bring {yoe:.1f} years of experience from {company}"
        ]
        opener = templates[variant % len(templates)]
        
        if drawback_str:
            return f"{opener}, they were deprioritized due to {drawback_str}."
        else:
            return f"{opener}, their overall profile alignment was slightly weaker than top-tier candidates."
