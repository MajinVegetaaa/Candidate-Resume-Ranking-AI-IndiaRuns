"""
skill_authenticity.py — Skill Fit Scoring (Phase 1)

Weighted-additive scorer with 3 sub-scores:

    skill_fit = 0.45×relevance + 0.30×depth + 0.25×summary

Sub-scores:
    relevance — Which JD-relevant skill categories are present
    depth     — Proficiency level + tenure combined
    summary   — Profile summary technical quality + cert bonus

No gate checks here — gates live exclusively in honeypot_detector.py.
"""

from typing import List


# ══════════════════════════════════════════════════════════════════════════
# SKILL CATEGORY SETS
# ══════════════════════════════════════════════════════════════════════════

RETRIEVAL_VECTOR = {
    "faiss", "qdrant", "pinecone", "weaviate", "milvus",
    "elasticsearch", "opensearch", "haystack",
    "information retrieval", "vector database",
    "vector search", "hybrid search", "dense retrieval",
}

EMBEDDINGS_TRANSFORMERS = {
    "sentence transformers", "sentence-transformers",
    "bge", "e5", "hugging face transformers",
    "huggingface transformers", "embeddings", "embedding",
    "text embeddings",
}

RANKING_RECSYS = {
    "recommendation systems", "recommender systems",
    "learning to rank", "learning-to-rank", "xgboost",
    "lightgbm", "feature engineering", "ranking",
    "reranking", "re-ranking", "ndcg",
}

ML_CORE = {
    "python", "scikit-learn", "sklearn", "tensorflow",
    "pytorch", "mlflow", "weights & biases", "wandb",
    "machine learning", "deep learning", "neural networks",
}

LLM_FINETUNE = {
    "fine-tuning llms", "finetuning", "lora", "qlora",
    "peft", "langchain", "rag",
    "retrieval augmented generation", "mlops",
    "large language models", "generative ai",
}

DATA_ENGINEERING = {
    "spark", "airflow", "kafka", "dbt", "databricks",
    "etl", "data pipelines", "snowflake", "bigquery",
    "apache beam", "hadoop", "flink", "pyspark",
}

# Union of all JD-relevant skill names (for depth scoring)
JD_RELEVANT = (
    RETRIEVAL_VECTOR | EMBEDDINGS_TRANSFORMERS
    | RANKING_RECSYS | ML_CORE | LLM_FINETUNE
)

# ── Summary keyword sets ─────────────────────────────────────────────

SUMMARY_DOMAIN = {
    "retrieval", "embedding", "embeddings", "ndcg", "a/b test",
    "ranking system", "recommendation system", "vector search",
    "information retrieval", "learning to rank", "rerank",
    "sentence transformer", "faiss", "pinecone", "elasticsearch",
    "feature pipeline", "production ml", "ranking model", "search ranking",
}

SUMMARY_ML = {
    "machine learning", "deep learning", "neural network",
    "artificial intelligence", "data science", "model training",
    "nlp", "natural language processing", "large language model",
}

SUMMARY_BOILERPLATE = {
    "driving business outcomes", "helping teams scale",
    "built and led teams", "owned kpis",
    "driving outcomes through", "results-driven professional",
    "passionate about delivering value", "proven track record of",
    "cross-functional stakeholder", "managed relationships",
}

# ── Certification keyword sets ────────────────────────────────────────

ML_CERT_KEYWORDS = {
    "machine learning specialty", "ml specialty",
    "professional machine learning engineer",
    "deeplearning.ai", "fast.ai", "tensorflow developer",
    "hugging face", "pytorch certification", "aws ml",
}

CLOUD_CERT_KEYWORDS = {
    "aws certified cloud practitioner", "azure fundamentals",
    "gcp associate", "aws solutions architect",
    "google cloud professional data engineer", "cloud practitioner",
}


# ══════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════

def _n(s: str) -> str:
    return s.lower().strip() if s else ""


# ══════════════════════════════════════════════════════════════════════════
# SUB-SCORE 1: RELEVANCE (weight 0.45)
# ══════════════════════════════════════════════════════════════════════════

def _score_relevance(skills: List[dict]) -> float:
    """Which JD-relevant skill categories are present."""
    if not skills:
        return 0.05

    names = {_n(s.get("name", "")) for s in skills}
    r_count  = len(names & RETRIEVAL_VECTOR)
    e_count  = len(names & EMBEDDINGS_TRANSFORMERS)
    rk_count = len(names & RANKING_RECSYS)
    ml_count = len(names & ML_CORE)
    
    # We want depth/substantive proof. 1.00 requires at least 4 distinct core search/ranking skills.
    core_search_skills = r_count + e_count + rk_count

    if core_search_skills >= 4:       return 1.00
    if core_search_skills == 3:       return 0.85
    if core_search_skills == 2:       return 0.70
    if core_search_skills == 1 and ml_count >= 2: return 0.55
    if core_search_skills == 1:       return 0.40
    if ml_count >= 2:                 return 0.25
    return 0.05


# ══════════════════════════════════════════════════════════════════════════
# SUB-SCORE 2: DEPTH (weight 0.30) — merges proficiency + tenure
# ══════════════════════════════════════════════════════════════════════════

def _score_depth(skills: List[dict]) -> float:
    """Combined proficiency level + tenure on JD-relevant skills."""
    # Only measure depth against CORE Search/Ranking skills, not generic ML
    core_relevant = [s for s in skills if _n(s.get("name", "")) in (RETRIEVAL_VECTOR | EMBEDDINGS_TRANSFORMERS | RANKING_RECSYS)]
    if not core_relevant:
        return 0.10
        
    # Proficiency component (60%)
    expert   = sum(1 for s in core_relevant if s.get("proficiency") == "expert")
    advanced = sum(1 for s in core_relevant if s.get("proficiency") == "advanced")
    inter    = sum(1 for s in core_relevant if s.get("proficiency") == "intermediate")

    if expert >= 2:                   prof = 1.00
    elif expert == 1 or advanced >= 3: prof = 0.80
    elif advanced >= 1:               prof = 0.55
    elif inter >= 1:                  prof = 0.35
    else:                             prof = 0.15

    # Tenure component (40%)
    durations = [s.get("duration_months", 0) for s in core_relevant if s.get("duration_months", 0) > 0]
    if not durations:
        ten = 0.15
    else:
        avg = sum(durations) / len(durations)
        if avg > 36:   ten = 1.00
        elif avg >= 18: ten = 0.75
        elif avg >= 6:  ten = 0.45
        else:           ten = 0.15

    return round(0.60 * prof + 0.40 * ten, 4)


# ══════════════════════════════════════════════════════════════════════════
# SUB-SCORE 3: SUMMARY (weight 0.25) — summary quality + cert bonus
# ══════════════════════════════════════════════════════════════════════════

def _score_summary(summary: str, certifications: List[dict]) -> float:
    """Profile summary technical quality + certification bonus."""
    # Summary component (base)
    if not summary:
        base = 0.05
    else:
        text = _n(summary)
        domain_hits     = sum(1 for kw in SUMMARY_DOMAIN if kw in text)
        ml_hits         = sum(1 for kw in SUMMARY_ML if kw in text)
        boilerplate_hits = sum(1 for kw in SUMMARY_BOILERPLATE if kw in text)

        if boilerplate_hits >= 1 and domain_hits == 0 and ml_hits == 0:
            base = 0.05
        elif domain_hits >= 3: base = 1.00
        elif domain_hits >= 1: base = 0.75
        elif ml_hits >= 2:     base = 0.55
        elif ml_hits >= 1:     base = 0.35
        else:                  base = 0.10

    # Cert bonus (additive, +0.10 for ML cert, +0.05 for cloud cert)
    cert_bonus = 0.0
    if certifications:
        for cert in certifications:
            combined = _n(cert.get("name", "") + " " + cert.get("issuer", ""))
            if any(kw in combined for kw in ML_CERT_KEYWORDS):
                cert_bonus = 0.10
                break
        if cert_bonus == 0.0:
            for cert in certifications:
                if any(kw in _n(cert.get("name", "")) for kw in CLOUD_CERT_KEYWORDS):
                    cert_bonus = 0.05
                    break

    return round(min(1.0, base + cert_bonus), 4)


# ══════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════

def score_skill_authenticity(candidate: dict, jd: dict) -> float:
    """Compute skill_fit using weighted additive formula.

    skill_fit = 0.45×relevance + 0.30×depth + 0.25×summary

    No gate checks — gates live exclusively in honeypot_detector.py.

    Parameters
    ----------
    candidate : dict
        Candidate profile.
    jd : dict
        Job-description config (JD_CONFIG).

    Returns
    -------
    float
        Score in [0.0, 1.0].
    """
    skills  = candidate.get("skills", [])
    summary = candidate.get("profile", {}).get("summary", "")
    certs   = candidate.get("certifications", [])

    rel   = _score_relevance(skills)
    dep   = _score_depth(skills)
    summ  = _score_summary(summary, certs)

    score = 0.45 * rel + 0.30 * dep + 0.25 * summ
    
# ─── Graduated Computer Vision Bleed-Over Penalty ────────────────────
    cv_kws = jd.get("computer_vision_keywords", [])
    names = {_n(s.get("name", "")) for s in skills}
    
    cv_count = sum(1 for n in names if any(kw in n for kw in cv_kws))
    retrieval_count = (len(names & RETRIEVAL_VECTOR) + 
                       len(names & EMBEDDINGS_TRANSFORMERS) + 
                       len(names & RANKING_RECSYS))

    if cv_count > 0 and retrieval_count <= 1:
        score *= 0.20
    elif cv_count > 0 and retrieval_count == 2:
        score *= 0.55
    elif cv_count > 0 and retrieval_count >= 3:
        score *= 1.0  

    return round(min(1.0, max(0.0, score)), 4)
