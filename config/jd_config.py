"""
JD Configuration — Structured intent parsed from job_description.docx

This is the "brain" of the ranker. Every scoring decision flows from this config.
The JD is for a Senior AI/ML Ranking Systems Engineer at Redrob (product company, India).

NOTE: The raw JD text for semantic embedding (Phases 2 & 3) is now loaded
directly from job_description.docx at runtime — see rank.py load_jd_text().
"""

JD_CONFIG = {
    # =========================================================================
    # ROLE IDENTITY
    # =========================================================================
    # Titles that indicate genuine fit for this role
    "target_titles": [
        "ai engineer", "ml engineer", "machine learning engineer",
        "senior ml engineer", "senior machine learning engineer",
        "senior ai engineer", "lead ai engineer", "lead ml engineer",
        "staff ml engineer", "principal ml engineer",
        "data scientist", "senior data scientist",
        "nlp engineer", "senior nlp engineer",
        "search engineer", "ranking engineer", "recommendation engineer",
        "recommendation systems engineer", "search relevance engineer",
        "information retrieval engineer",
        "applied scientist", "senior applied scientist",
        "research engineer", "research scientist",
        "ml architect",
        "backend engineer",  # if career context matches
    ],

    # Titles that are clear mismatches — JD explicitly calls these out
    "red_flag_titles": [
        "marketing manager", "hr manager", "content writer",
        "graphic designer", "accountant", "sales executive",
        "customer support", "civil engineer", "mechanical engineer",
        "operations manager", "project manager", "office manager",
        "admin", "receptionist", "finance manager", "hr executive",
    ],

    # =========================================================================
    # MUST-HAVE SKILLS (from "Things you absolutely need")
    # =========================================================================
    "must_have_skills": [
        # Embeddings & retrieval — "Production experience with embeddings-based
        # retrieval systems (sentence-transformers, OpenAI embeddings, BGE, E5)"
        "embeddings", "embedding", "sentence-transformers", "sentence transformers",
        "openai embeddings", "bge", "e5", "text embeddings",
        "dense retrieval", "embedding drift",

        # Vector databases / hybrid search — "Production experience with vector
        # databases or hybrid search infrastructure"
        "vector search", "vector database", "faiss", "pinecone", "weaviate",
        "qdrant", "milvus", "opensearch", "elasticsearch", "hybrid search",
        "haystack",

        # Core ranking/retrieval — "own the intelligence layer: ranking, retrieval,
        # and matching systems"
        "python", "ranking", "ranking systems", "retrieval",
        "search", "search ranking", "information retrieval",
        "recommendation", "recommendation systems", "recommender systems",
        "matching", "candidate matching",

        # Evaluation — "Hands-on experience designing evaluation frameworks for
        # ranking systems (NDCG, MRR, MAP, offline-to-online correlation)"
        "ndcg", "mrr", "map", "a/b testing", "a/b test", "evaluation",
        "offline benchmarks", "online evaluation",

        # General ML/DL — "Strong Python and code quality"
        "machine learning", "deep learning", "nlp",
        "natural language processing", "pytorch", "tensorflow",
        "transformers", "hugging face", "huggingface",
        "scikit-learn", "sklearn",
    ],

    # =========================================================================
    # NICE-TO-HAVE SKILLS (from "Things we'd like you to have")
    # =========================================================================
    "nice_to_have_skills": [
        # LLM fine-tuning
        "llm fine-tuning", "fine-tuning", "lora", "qlora", "peft",
        "large language models", "generative ai", "finetuning",

        # Learning-to-rank
        "learning-to-rank", "learning to rank", "l2r",
        "xgboost", "lightgbm", "feature engineering",

        # HR-tech / marketplace
        "hr-tech", "recruiting tech", "marketplace",
        "talent intelligence",

        # Distributed systems / infrastructure
        "distributed systems", "large-scale inference",
        "model serving", "inference optimization",

        # Open-source
        "open-source", "open source contributions",

        # RAG / LLM integration
        "rag", "retrieval augmented generation",
        "langchain", "llamaindex",

        # Infrastructure / MLOps
        "docker", "kubernetes", "aws", "gcp",
        "mlops", "ml pipeline", "airflow", "spark",
        "mlflow", "weights & biases", "wandb",
        "bentoml", "ray",

        # Retrieval specific
        "bm25", "re-ranking", "reranking", "cross-encoder", "bi-encoder",
        "two-tower", "collab filtering", "collaborative filtering",
        "click-through", "training pipeline", "feature pipeline",
        "pgvector",
    ],

    # =========================================================================
    # EXPERIENCE RANGE (JD: "5-9 years is a range, not a requirement")
    # =========================================================================
    "ideal_yoe_min": 5,
    "ideal_yoe_max": 9,
    "acceptable_yoe_min": 4,
    "acceptable_yoe_max": 15,

    # =========================================================================
    # ANTI-PATTERNS (from "Things we explicitly do NOT want")
    # =========================================================================
    # "People who have only worked at consulting firms (TCS, Infosys, Wipro,
    #  Accenture, Cognizant, Capgemini, etc.) in their entire career."
    "consulting_firms": [
        "tcs", "tata consultancy", "tata consultancy services",
        "infosys", "wipro", "accenture",
        "cognizant", "cts", "capgemini",
        "hcl", "hcl technologies", "tech mahindra",
        "genpact", "mindtree", "mphasis", "hexaware",
        "ltimindtree", "persistent systems", "firstsource",
        "niit technologies",
    ],

    # "Title-chasers" — avg tenure < 18 months across roles
    "title_chaser_threshold_months": 18,
    
    # Computer Vision Keywords — Explicit negative signal to penalize CV bleeding into Search roles
    "computer_vision_keywords": [
        "yolo", "opencv", "computer vision", "gan", "gans", "cnn", "cnns",
        "image classification", "object detection", "image segmentation", 
        "diffusion models", "stable diffusion", "midjourney", "dall-e",
        "resnet", "vgg", "image processing", "facial recognition"
    ],

    # =========================================================================
    # CAREER DESCRIPTION KEYWORDS
    # =========================================================================
    # Words in role descriptions that indicate genuine system-building experience
    # (catches hidden gems whose skill lists don't contain buzzwords)
    "system_building_keywords": [
        # Action verbs indicating building
        "built", "shipped", "deployed", "designed", "architected",
        "implemented", "developed", "launched", "scaled", "optimized",
        # Domain-specific terms
        "ranking", "search", "recommendation", "retrieval", "embeddings",
        "production", "inference", "pipeline", "real-time", "latency",
        "a/b test", "evaluation", "metrics", "ndcg", "precision",
        "vector", "index", "reranking", "re-ranking",
        "matching", "scoring", "relevance",
        "ml model", "model serving", "model deployment",
        "feature engineering", "training pipeline", "data pipeline",
        "click model", "engagement metrics", "recruiter",
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
        "hr tech", "recruiting", "talent intelligence",
    ],

    # =========================================================================
    # LOCATION
    # =========================================================================
    "preferred_locations": ["noida", "pune"],
    "acceptable_locations": [
        "hyderabad", "mumbai", "delhi", "ncr", "gurgaon", "gurugram",
        "bangalore", "bengaluru", "chennai", "kolkata",
        "greater noida", "new delhi",
    ],
    "country": "india",

    # =========================================================================
    # LOGISTICS
    # =========================================================================
    "preferred_notice_days_max": 30,
    "work_mode": "hybrid",
}


# Convenience: all JD skills combined for matching
ALL_JD_SKILLS = JD_CONFIG["must_have_skills"] + JD_CONFIG["nice_to_have_skills"]

# Convenience: location sets — import these everywhere, do NOT hardcode elsewhere
PREFERRED_LOCATIONS: set = set(JD_CONFIG["preferred_locations"])
ACCEPTABLE_LOCATIONS: set = set(JD_CONFIG["acceptable_locations"])
