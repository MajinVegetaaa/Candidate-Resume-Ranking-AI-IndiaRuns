"""
semantic_reranker.py - 2-Stage Neural Reranking

Stage 1: Bi-Encoder (all-mpnet-base-v2) for fast vector search.
Stage 2: Cross-Encoder (ms-marco-MiniLM-L-6-v2) for deep contextual reasoning.
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import yaml
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "ranking_config.yaml")
with open(CONFIG_PATH, "r") as f:
    RANKING_CONFIG = yaml.safe_load(f)

def load_bi_encoder(model_name: str = 'all-mpnet-base-v2', device: str = 'cpu'):
    """Load the SentenceTransformer Bi-Encoder."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_name, device=device)

def load_cross_encoder(model_name: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2', device: str = 'cpu'):
    """Load the SentenceTransformer Cross-Encoder."""
    from sentence_transformers import CrossEncoder
    return CrossEncoder(model_name, device=device)

def _build_candidate_text(candidate: dict) -> str:
    """Build a rich text representation of a candidate for embedding."""
    parts = []
    profile = candidate.get('profile', {})
    if headline := profile.get('headline', ''): parts.append(headline)
    if summary := profile.get('summary', ''): parts.append(summary)

    max_roles = RANKING_CONFIG["pipeline"]["phase2_bi_encoder"]["extraction"]["max_roles"]
    max_skills = RANKING_CONFIG["pipeline"]["phase2_bi_encoder"]["extraction"]["max_skills"]

    career = candidate.get('career_history', []) or []
    role_texts = [f"{r.get('title', '')} at {r.get('company', '')}: {(r.get('description', '') or '')[:200]}" for r in career[:max_roles]]
    if role_texts: parts.append("Career: " + "; ".join(role_texts))

    skills = [s.get('name', '') for s in (candidate.get('skills', []) or [])[:max_skills] if s.get('name')]
    if skills: parts.append("Skills: " + ", ".join(skills))

    return ". ".join(parts)

def bi_encoder_rerank(model, jd_text: str, candidates_with_scores: list, top_n: int) -> list:
    """PHASE 2: Rerank using Bi-Encoder cosine similarity."""
    rerank_pool = candidates_with_scores[:top_n]
    remainder = candidates_with_scores[top_n:]

    if not rerank_pool: return candidates_with_scores

    candidate_texts = [_build_candidate_text(c[2]) for c in rerank_pool]
    jd_embedding = model.encode([jd_text], batch_size=32)
    candidate_embeddings = model.encode(candidate_texts, batch_size=32)

    similarities = cosine_similarity(jd_embedding, candidate_embeddings)[0]
    normalized = np.clip(similarities, 0.0, 1.0)
    normalized = np.nan_to_num(normalized, nan=0.0)

    rule_weight = RANKING_CONFIG["pipeline"]["phase2_bi_encoder"]["blend_weights"]["rule_score"]
    semantic_weight = RANKING_CONFIG["pipeline"]["phase2_bi_encoder"]["blend_weights"]["semantic_score"]

    reranked = []
    for idx, (cid, rule_score, cand) in enumerate(rerank_pool):
        combined = rule_weight * rule_score + semantic_weight * normalized[idx]
        reranked.append((cid, combined, cand))

    reranked.sort(key=lambda x: x[1], reverse=True)
    return reranked + remainder

def cross_encoder_rerank(model, jd_text: str, candidates_with_scores: list, top_n: int) -> list:
    """PHASE 3: Deep contextual reranking using Cross-Encoder."""
    rerank_pool = candidates_with_scores[:top_n]
    remainder = candidates_with_scores[top_n:]

    if not rerank_pool: return candidates_with_scores

    # Cross-Encoders take PAIRS of text: [[JD, Resume1], [JD, Resume2], ...]
    pairs = [[jd_text, _build_candidate_text(c[2])] for c in rerank_pool]
    
    # Predict yields raw logits (can be negative or positive)
    ce_scores = model.predict(pairs)
    
    # Normalize logits to 0-1 using Sigmoid function so we can blend it
    norm_ce_scores = 1 / (1 + np.exp(-ce_scores))
    norm_ce_scores = np.nan_to_num(norm_ce_scores, nan=0.0)

    prev_weight = RANKING_CONFIG["pipeline"]["phase3_cross_encoder"]["blend_weights"]["prev_score"]
    semantic_weight = RANKING_CONFIG["pipeline"]["phase3_cross_encoder"]["blend_weights"]["semantic_score"]

    reranked = []
    for idx, (cid, prev_score, cand) in enumerate(rerank_pool):
        # Blend the Bi-Encoder's score with the Cross-Encoder's deep context
        final_score = prev_weight * prev_score + semantic_weight * norm_ce_scores[idx]
        reranked.append((cid, final_score, cand))

    reranked.sort(key=lambda x: x[1], reverse=True)
    return reranked + remainder