"""
career_fit.py — Career Fit Scoring (Phase 1)

Weighted-additive scorer with 4 sub-scores:

    career_fit = 0.40×work_evidence + 0.25×trajectory + 0.20×company_quality + 0.15×stability

Sub-scores:
    work_evidence    — Ranking/retrieval/ML keywords in job descriptions
    trajectory       — ML/Search role progression + current title type
    company_quality  — Product vs consulting mix + scale + current context
    stability        — Tenure stability + YoE sweet spot

No gate checks here — gates live exclusively in honeypot_detector.py.
"""

from collections import Counter
from typing import Any, Dict, List


# ══════════════════════════════════════════════════════════════════════════
# CLASSIFICATION SETS
# ══════════════════════════════════════════════════════════════════════════

PRODUCT_COMPANIES = {
    "swiggy", "zomato", "cred", "razorpay", "flipkart", "ola", "meesho",
    "phonepe", "paytm", "byju", "unacademy", "groww", "zerodha", "nykaa",
    "dunzo", "urban company", "slice", "moengage", "cleartax", "lenskart",
    "freshworks", "zoho", "ola electric", "rapido", "sharechat",
    "google", "meta", "amazon", "microsoft", "apple", "netflix", "uber",
    "airbnb", "linkedin", "twitter", "stripe", "shopify", "salesforce",
    "atlassian", "databricks", "snowflake", "openai", "anthropic",
    "mad street den",
}

CONSULTING_FIRMS = {
    "tcs", "tata consultancy services", "wipro", "infosys", "cognizant",
    "tech mahindra", "mindtree", "hcl", "hcl technologies", "accenture",
    "capgemini", "mphasis", "hexaware", "ltimindtree", "persistent systems",
}

NON_TECH_INDUSTRIES = {
    "manufacturing", "paper products", "retail", "conglomerate",
    "agriculture", "textiles", "hospitality", "real estate",
    "pharmaceuticals", "fmcg", "consumer goods", "construction",
}

IT_SERVICES_INDUSTRIES = {
    "it services", "information technology services", "consulting",
    "technology consulting", "it consulting", "staffing", "bpo",
}

ML_SEARCH_TITLES = {
    "recommendation systems engineer", "applied ml engineer",
    "nlp engineer", "search engineer", "machine learning engineer",
    "ml engineer", "research scientist", "applied scientist",
    "ranking engineer", "search relevance engineer",
    "information retrieval engineer", "senior ml engineer",
    "staff ml engineer", "principal ml engineer",
}

SWE_TITLES = {
    "software engineer", "backend engineer", "full stack engineer",
    "senior software engineer", "staff engineer", "principal engineer",
    "java developer", ".net developer", "full stack developer",
    "senior backend engineer", "software developer",
}

DATA_CLOUD_TITLES = {
    "data engineer", "cloud engineer", "devops engineer", "qa engineer",
    "senior data engineer", "data architect", "analytics engineer",
    "platform engineer", "infrastructure engineer", "sre",
}

NON_TECH_TITLES = {
    "marketing manager", "operations manager", "accountant",
    "hr manager", "graphic designer", "civil engineer",
    "mechanical engineer", "customer support", "content writer",
    "sales executive", "hr executive", "finance manager",
    "office manager", "admin", "receptionist",
}

# ── Description keyword sets ─────────────────────────────────────────

DESC_RETRIEVAL = {
    "retrieval", "embedding-based retrieval", "l2r", "learning to rank",
    "ndcg", "mrr", "ranking model", "search ranking",
    "recommendation system", "recommender", "collab filtering",
    "two-tower", "bm25", "faiss", "pinecone", "weaviate", "qdrant",
    "reranking", "re-ranking", "cross-encoder", "bi-encoder",
    "feature pipeline", "training pipeline", "click-through",
    "xgboost", "lightgbm", "a/b test",
}

DESC_ML = {
    "shipped model", "production ml", "model deployment", "inference",
    "model serving", "experiment", "feature engineering", "model training",
    "embedding", "sentence transformer", "pytorch", "tensorflow",
    "fine-tuning", "training loop", "model monitoring", "mlflow",
}

DESC_DATA_ENG = {
    "spark pipeline", "airflow", "snowflake", "bigquery",
    "dbt", "kafka", "etl", "data warehouse", "databricks", "pyspark",
}

DESC_GENERIC_TECH = {
    "improved performance", "reduced latency", "optimized",
    "microservices", "rest api", "system design", "scalable",
}

DESC_NON_TECH = {
    "managed relationships", "handled kpis", "supported business outcomes",
    "driving outcomes", "stakeholder management", "business development",
    "client engagement", "account management",
}


# ══════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════

def _n(s: str) -> str:
    return s.lower().strip() if s else ""


def _classify_company(company: str, industry: str) -> str:
    """Classify a company as product/consulting/non_tech/startup/unknown."""
    co, ind = _n(company), _n(industry)
    if co in CONSULTING_FIRMS:                                    return "consulting"
    if co in PRODUCT_COMPANIES:                                   return "product"
    if ind in NON_TECH_INDUSTRIES:                                return "non_tech"
    if ind in IT_SERVICES_INDUSTRIES:                             return "consulting"
    if any(kw in ind for kw in ("startup", "saas", "software")):  return "startup"
    return "unknown"


def _classify_title(title: str) -> str:
    """Classify a title as ml_search/swe/data_cloud/non_tech/unknown."""
    t = _n(title)
    if t in ML_SEARCH_TITLES:   return "ml_search"
    if t in SWE_TITLES:         return "swe"
    if t in DATA_CLOUD_TITLES:  return "data_cloud"
    if t in NON_TECH_TITLES:    return "non_tech"
    # Fuzzy fallback
    if any(kw in t for kw in ("ml", "machine learning", "nlp", "search", "ranking", "recommend", "research")):
        return "ml_search"
    if any(kw in t for kw in ("engineer", "developer", "software", "backend", "full stack")):
        return "swe"
    if any(kw in t for kw in ("data", "cloud", "devops", "infra", "platform", "analytics")):
        return "data_cloud"
    return "unknown"


# ══════════════════════════════════════════════════════════════════════════
# SUB-SCORE 1: WORK EVIDENCE (weight 0.40)
# ══════════════════════════════════════════════════════════════════════════

def _score_work_evidence(career: List[dict]) -> float:
    """Ranking/retrieval/ML evidence in job descriptions."""
    if not career:
        return 0.0

    descs = [d.strip() for d in (j.get("description", "") for j in career) if d.strip()]

    # Strip identical copy-pasted descriptions
    if len(descs) >= 3:
        counts = Counter(descs)
        most_common_text, count = counts.most_common(1)[0]
        if count >= 3:
            descs = [d for d in descs if d != most_common_text]
            if not descs:
                return 0.0

    retrieval = ml = data_eng = generic = 0
    for desc in descs:
        text = _n(desc)
        r = sum(1 for kw in DESC_RETRIEVAL if kw in text)
        m = sum(1 for kw in DESC_ML if kw in text)
        d = sum(1 for kw in DESC_DATA_ENG if kw in text)
        g = sum(1 for kw in DESC_GENERIC_TECH if kw in text)
        n = sum(1 for kw in DESC_NON_TECH if kw in text)

        if r >= 2:                       retrieval += 1
        elif m >= 2:                     ml += 1
        elif d >= 2:                     data_eng += 1
        elif g >= 1 and n == 0:          generic += 1

    if retrieval >= 2:                   return 1.00
    if retrieval == 1 and ml >= 1:       return 0.85
    if retrieval == 1:                   return 0.70
    if ml >= 2:                          return 0.55
    if ml == 1:                          return 0.40
    if data_eng >= 1:                    return 0.25
    if generic >= 1:                     return 0.15
    return 0.05


# ══════════════════════════════════════════════════════════════════════════
# SUB-SCORE 2: TRAJECTORY (weight 0.25)
# ══════════════════════════════════════════════════════════════════════════

def _score_trajectory(career: List[dict], current_title: str) -> float:
    """Role title progression + current title type (merges old 2A + 1A)."""
    if not career and not current_title:
        return 0.10

    # Current title component (40% of this sub-score)
    cur_kind = _classify_title(current_title)
    cur_score = {"ml_search": 1.0, "swe": 0.65, "data_cloud": 0.55, "unknown": 0.40, "non_tech": 0.10}.get(cur_kind, 0.40)

    # Career path component (60% of this sub-score)
    if not career:
        return cur_score

    titles = [_classify_title(j.get("title", "")) for j in career]
    ml = titles.count("ml_search")
    swe = titles.count("swe")
    nt = titles.count("non_tech")
    total = len(titles)

    if ml >= 2:                  path_score = 1.00
    elif ml == 1 and swe >= 1:   path_score = 0.80
    elif ml == 1:                path_score = 0.70
    elif swe >= 1:               path_score = 0.45
    elif nt == total:            path_score = 0.10
    else:                        path_score = 0.30

    return round(0.40 * cur_score + 0.60 * path_score, 4)


# ══════════════════════════════════════════════════════════════════════════
# SUB-SCORE 3: COMPANY QUALITY (weight 0.20)
# ══════════════════════════════════════════════════════════════════════════

def _score_company_quality(career: List[dict], current_company: str,
                           current_industry: str, current_size: str) -> float:
    """Product vs consulting mix + scale + current context (merges old 2B + 2E + 1E)."""
    if not career:
        return 0.15

    # History component (60%): product/startup ratio
    types = [_classify_company(j.get("company", ""), j.get("industry", "")) for j in career]
    total = len(types)
    product = types.count("product") + types.count("startup")
    consulting = types.count("consulting")
    nontech = types.count("non_tech")

    if nontech == total:              hist = 0.05
    elif product == total:            hist = 1.00
    elif product / total >= 0.66:     hist = 0.80
    elif product / total >= 0.33:     hist = 0.55
    elif consulting == total:         hist = 0.15
    else:                             hist = 0.35

    # Current company component (40%)
    cur_type = _classify_company(current_company, current_industry)
    sz = _n(current_size)
    large_consulting = cur_type == "consulting" and ("10001" in sz or "10,001" in sz)

    if cur_type == "product":         cur = 1.00
    elif cur_type == "startup":       cur = 0.75
    elif large_consulting:            cur = 0.15
    elif cur_type == "consulting":    cur = 0.40
    elif cur_type == "non_tech":      cur = 0.20
    else:                             cur = 0.55

    return round(0.60 * hist + 0.40 * cur, 4)


# ══════════════════════════════════════════════════════════════════════════
# SUB-SCORE 4: STABILITY (weight 0.15)
# ══════════════════════════════════════════════════════════════════════════

def _score_stability(career: List[dict], yoe: float) -> float:
    """Tenure stability + YoE sweet spot (merges old 2C + 1D)."""
    # Tenure component (50%)
    if not career:
        tenure = 0.30
    elif len(career) == 1:
        m = career[0].get("duration_months", 0)
        tenure = 0.65 if m >= 36 else (0.50 if m >= 18 else 0.30)
    else:
        durs = [j.get("duration_months", 0) for j in career]
        avg = sum(durs) / len(durs)
        if 18 <= avg <= 48:     tenure = 1.00
        elif avg > 48:          tenure = 0.80
        elif avg >= 12:         tenure = 0.55
        else:                   tenure = 0.25

    # YoE component (50%)
    if 5 <= yoe <= 9:           yoe_score = 1.00
    elif 4 <= yoe < 5:          yoe_score = 0.80
    elif 9 < yoe <= 12:         yoe_score = 0.75
    elif yoe < 4:               yoe_score = 0.30
    else:                       yoe_score = 0.40  # >12 years

    return round(0.50 * tenure + 0.50 * yoe_score, 4)


# ══════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════

def score_career_fit(candidate: dict, jd: dict) -> float:
    """Compute career_fit using weighted additive formula.

    career_fit = 0.40×work_evidence + 0.25×trajectory
               + 0.20×company_quality + 0.15×stability

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
    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])

    we = _score_work_evidence(career)
    tr = _score_trajectory(career, profile.get("current_title", ""))
    cq = _score_company_quality(
        career,
        profile.get("current_company", ""),
        profile.get("industry", ""),
        profile.get("company_size", ""),
    )
    st = _score_stability(career, profile.get("years_of_experience", 0))

    score = 0.40 * we + 0.25 * tr + 0.20 * cq + 0.15 * st
    return round(min(1.0, max(0.0, score)), 4)
