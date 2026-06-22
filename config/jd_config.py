"""
JD Configuration — Structured intent parsed from job_description.docx

This is the "brain" of the ranker. Every scoring decision flows from this config.
The JD is for a Senior AI/ML Ranking Systems Engineer at Redrob (product company, India).
"""

JD_CONFIG = {
    # =========================================================================
    # ROLE IDENTITY
    # =========================================================================
    # Titles that indicate genuine fit for this role
    "target_titles": [
        "ai engineer", "ml engineer", "machine learning engineer",
        "senior ml engineer", "senior machine learning engineer",
        "senior ai engineer", "staff ml engineer", "lead ml engineer",
        "data scientist", "senior data scientist", "nlp engineer",
        "search engineer", "ranking engineer", "recommendation engineer",
        "applied scientist", "research engineer", "ml architect",
        "principal engineer", "backend engineer",  # if career context matches
    ],

    # Titles that are clear mismatches — JD explicitly calls these out
    "red_flag_titles": [
        "marketing manager", "hr manager", "content writer",
        "graphic designer", "accountant", "sales executive",
        "customer support", "civil engineer", "mechanical engineer",
        "operations manager", "project manager",
    ],

    # =========================================================================
    # MUST-HAVE SKILLS (from "Things you absolutely need")
    # =========================================================================
    "must_have_skills": [
        # Embeddings & retrieval
        "embeddings", "sentence-transformers", "sentence transformers",
        "openai embeddings", "bge", "e5",
        # Vector databases / hybrid search
        "vector search", "vector database", "faiss", "pinecone", "weaviate",
        "qdrant", "milvus", "opensearch", "elasticsearch", "hybrid search",
        # Core
        "python", "ranking", "ranking systems", "retrieval", "search",
        "recommendation", "recommendation systems", "information retrieval",
        # Evaluation
        "ndcg", "mrr", "map", "a/b testing", "evaluation",
        # General ML
        "machine learning", "deep learning", "nlp",
        "natural language processing", "pytorch", "tensorflow",
        "transformers", "hugging face", "huggingface",
    ],

    # =========================================================================
    # NICE-TO-HAVE SKILLS
    # =========================================================================
    "nice_to_have_skills": [
        "llm fine-tuning", "lora", "qlora", "peft",
        "learning-to-rank", "xgboost", "lightgbm",
        "hr-tech", "recruiting tech", "marketplace",
        "distributed systems", "large-scale inference",
        "open-source", "rag", "retrieval augmented generation",
        "langchain", "docker", "kubernetes", "aws", "gcp",
        "mlops", "ml pipeline", "airflow", "spark",
    ],

    # =========================================================================
    # EXPERIENCE RANGE
    # =========================================================================
    "ideal_yoe_min": 5,
    "ideal_yoe_max": 9,
    "acceptable_yoe_min": 4,
    "acceptable_yoe_max": 15,

    # =========================================================================
    # ANTI-PATTERNS (from "Things we explicitly do NOT want")
    # =========================================================================
    "consulting_firms": [
        "tcs", "tata consultancy", "infosys", "wipro", "accenture",
        "cognizant", "capgemini", "hcl", "tech mahindra",
        "cts", "genpact", # cognizant abbreviation and genpact
    ],

    # Title-chaser: avg tenure < 18 months across roles
    "title_chaser_threshold_months": 18,

    # =========================================================================
    # CAREER DESCRIPTION KEYWORDS
    # =========================================================================
    # Words in role descriptions that indicate genuine system-building experience
    # (catches hidden gems whose skill lists don't contain buzzwords)
    "system_building_keywords": [
        "built", "shipped", "deployed", "designed", "architected",
        "implemented", "developed", "launched", "scaled", "optimized",
        "ranking", "search", "recommendation", "retrieval", "embeddings",
        "production", "inference", "pipeline", "real-time", "latency",
        "a/b test", "evaluation", "metrics", "ndcg", "precision",
        "vector", "index", "reranking", "re-ranking", "candidate",
        "matching", "scoring", "relevance", "ml model", "model serving",
        "feature engineering", "training pipeline", "data pipeline",
    ],

    # =========================================================================
    # PRODUCT vs SERVICES INDUSTRY CLASSIFICATION
    # =========================================================================
    "product_industries": [
        "technology", "software", "ai", "artificial intelligence",
        "saas", "internet", "fintech", "food delivery", "consumer tech",
        "e-commerce", "ecommerce", "data analytics", "cloud computing",
        "gaming", "social media", "healthtech", "edtech",
        "machine learning", "cybersecurity", "robotics",
    ],

    # =========================================================================
    # LOCATION
    # =========================================================================
    "preferred_locations": ["noida", "pune"],
    "acceptable_locations": [
        "hyderabad", "mumbai", "delhi", "ncr", "gurgaon", "gurugram",
        "bangalore", "bengaluru", "chennai", "kolkata",
    ],
    "country": "india",

    # =========================================================================
    # LOGISTICS
    # =========================================================================
    "preferred_notice_days_max": 30,
    "work_mode": "hybrid",

    # =========================================================================
    # FULL JD TEXT (for semantic embedding)
    # =========================================================================
    "jd_text_for_embedding": (
        "Senior AI/ML Engineer for ranking and retrieval systems at a product company. "
        "Own the intelligence layer: ranking, retrieval, and matching systems that decide "
        "what recruiters see when they search for candidates. "
        "Must have production experience with embeddings-based retrieval systems "
        "(sentence-transformers, OpenAI embeddings, BGE, E5) deployed to real users. "
        "Production experience with vector databases or hybrid search infrastructure "
        "(Pinecone, Weaviate, Qdrant, Milvus, OpenSearch, Elasticsearch, FAISS). "
        "Strong Python and code quality. "
        "Hands-on experience designing evaluation frameworks for ranking systems "
        "(NDCG, MRR, MAP, offline-to-online correlation, A/B test interpretation). "
        "Ship a v2 ranking system that improves recruiter-engagement metrics. "
        "Embeddings, hybrid retrieval, LLM-based re-ranking. "
        "Set up evaluation infrastructure: offline benchmarks, online A/B testing, "
        "recruiter-feedback loops. "
        "6-8 years total experience, 4-5 in applied ML/AI roles at product companies. "
        "Shipped at least one end-to-end ranking, search, or recommendation system "
        "to real users at meaningful scale. "
        "Located in or willing to relocate to Noida or Pune, India. "
        "Nice to have: LLM fine-tuning (LoRA, QLoRA, PEFT), learning-to-rank models, "
        "HR-tech or marketplace products, distributed systems, open-source contributions."
    ),
}


# Convenience: all JD skills combined for matching
ALL_JD_SKILLS = JD_CONFIG["must_have_skills"] + JD_CONFIG["nice_to_have_skills"]
