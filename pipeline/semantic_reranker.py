"""
semantic_reranker.py - Rerank top-N candidates using semantic similarity.

Uses SentenceTransformer ('all-MiniLM-L6-v2') to embed a rich text
representation of each candidate and the job description, then combines
the cosine-similarity score with the rule-based score (60/40 blend).
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def load_model():
    """Load the SentenceTransformer model. Call once at startup."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer('all-MiniLM-L6-v2')


def _build_candidate_text(candidate: dict) -> str:
    """Build a rich text representation of a candidate for embedding.

    Format:
        {headline}. {summary}. Career: {title} at {company}: {desc[:200]}
        for up to 4 roles. Skills: {up to 15 skill names}.
    """
    parts = []

    profile = candidate.get('profile', {})
    headline = profile.get('headline', '') or ''
    summary = profile.get('summary', '') or ''
    if headline:
        parts.append(headline)
    if summary:
        parts.append(summary)

    # Career history (up to 4 most recent roles)
    career = candidate.get('career_history', []) or []
    role_texts = []
    for role in career[:4]:
        title = role.get('title', '') or ''
        company = role.get('company', '') or ''
        description = (role.get('description', '') or '')[:200]
        role_texts.append(f"{title} at {company}: {description}")
    if role_texts:
        parts.append("Career: " + "; ".join(role_texts))

    # Skills (up to 15)
    skills = candidate.get('skills', []) or []
    skill_names = [s.get('name', '') for s in skills[:15] if s.get('name')]
    if skill_names:
        parts.append("Skills: " + ", ".join(skill_names))

    return ". ".join(parts)


def semantic_rerank(
    model,
    jd_text: str,
    candidates_with_scores: list,
    top_n: int = 200,
) -> list:
    """Rerank top-N candidates using semantic similarity.

    Args:
        model: SentenceTransformer model (from ``load_model``).
        jd_text: Full job-description text for embedding.
        candidates_with_scores: list of
            ``(candidate_id, rule_score, candidate_dict)`` tuples,
            **already sorted descending** by *rule_score*.
        top_n: Number of top candidates to semantically rerank
            (default 200).

    Returns:
        Full list of ``(candidate_id, combined_score, candidate_dict)``
        tuples sorted descending by *combined_score*.  Candidates beyond
        *top_n* retain their original rule_score.
    """
    # Split into rerank pool and remainder.
    rerank_pool = candidates_with_scores[:top_n]
    remainder = candidates_with_scores[top_n:]

    if not rerank_pool:
        return candidates_with_scores

    # Build texts for the pool.
    candidate_texts = [_build_candidate_text(c[2]) for c in rerank_pool]

    # Encode everything in one pass.
    jd_embedding = model.encode([jd_text], batch_size=32)
    candidate_embeddings = model.encode(candidate_texts, batch_size=32)

    # Cosine similarity → 1-D array of scores.
    similarities = cosine_similarity(jd_embedding, candidate_embeddings)[0]

    # Use raw cosine similarity (already ~0-1 for L2-normalized embeddings).
    # Clamp to [0, 1] to handle any edge cases.
    normalized = np.clip(similarities, 0.0, 1.0)

    # Blend: 60 % rule + 40 % semantic.
    reranked = []
    for idx, (cid, rule_score, cand) in enumerate(rerank_pool):
        combined = 0.60 * rule_score + 0.40 * normalized[idx]
        reranked.append((cid, combined, cand))

    # Sort the reranked pool descending by combined score.
    reranked.sort(key=lambda x: x[1], reverse=True)

    # Append remainder with original scores.
    for cid, rule_score, cand in remainder:
        reranked.append((cid, rule_score, cand))

    return reranked
