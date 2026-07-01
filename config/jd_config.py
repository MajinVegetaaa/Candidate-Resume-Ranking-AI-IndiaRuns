"""
JD Configuration — Structured intent parsed from job_description.docx

This is the "brain" of the ranker. Every scoring decision flows from this config.
The JD is for a Senior AI/ML Ranking Systems Engineer at Redrob (product company, India).
"""

JD_CONFIG = {
    # =========================================================================
    # ROLE IDENTITY
    # =========================================================================
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
        "ml architect", "backend engineer"
    ],

    "red_flag_titles": [
        "marketing manager", "hr manager", "content writer",
        "graphic designer", "accountant", "sales executive",
        "customer support", "civil engineer", "mechanical engineer",
        "operations manager", "project manager", "office manager",
        "admin", "receptionist", "finance manager", "hr executive"
    ],

    # =========================================================================
    # MUST-HAVE SKILLS
    # =========================================================================
    "must_have_skills": [
        "embeddings", "embedding", "sentence-transformers", "sentence transformers",
        "openai embeddings", "bge", "e5", "text embeddings",
        "dense retrieval", "embedding drift",
        "vector search", "vector database", "faiss", "pinecone", "weaviate",
        "qdrant", "milvus", "opensearch", "elasticsearch", "hybrid search",
        "haystack",
        "python", "ranking", "ranking systems", "retrieval",
        "search", "search ranking", "information retrieval",
        "recommendation", "recommendation systems", "recommender systems",
        "matching", "candidate matching",
        "ndcg", "mrr", "map", "a/b testing", "a/b test", "evaluation",
        "offline benchmarks", "online evaluation",
        "machine learning", "deep learning", "nlp",
        "natural language processing", "pytorch", "tensorflow",
        "transformers", "hugging face", "huggingface",
        "scikit-learn", "sklearn"
    ],

    # =========================================================================
    # NICE-TO-HAVE SKILLS
    # =========================================================================
    "nice_to_have_skills": [
        "llm fine-tuning", "fine-tuning", "lora", "qlora", "peft",
        "large language models", "generative ai", "finetuning",
        "learning-to-rank", "learning to rank", "l2r",
        "xgboost", "lightgbm", "feature engineering",
        "hr-tech", "recruiting tech", "marketplace",
        "talent intelligence",
        "distributed systems", "large-scale inference",
        "model serving", "inference optimization",
        "open-source", "open source contributions",
        "rag", "retrieval augmented generation",
        "langchain", "llamaindex",
        "docker", "kubernetes", "aws", "gcp",
        "mlops", "ml pipeline", "airflow", "spark",
        "mlflow", "weights & biases", "wandb",
        "bentoml", "ray",
        "bm25", "re-ranking", "reranking", "cross-encoder", "bi-encoder",
        "two-tower", "collab filtering", "collaborative filtering",
        "click-through", "training pipeline", "feature pipeline",
        "pgvector"
    ],

    # =========================================================================
    # EXPERIENCE RANGE
    # =========================================================================
    "ideal_yoe_min": 5,
    "ideal_yoe_max": 9,
    "acceptable_yoe_min": 4,
    "acceptable_yoe_max": 15,

    # =========================================================================
    # ANTI-PATTERNS
    # =========================================================================
    "consulting_firms": [
        "tcs", "tata consultancy", "tata consultancy services",
        "infosys", "wipro", "accenture",
        "cognizant", "cts", "capgemini",
        "hcl", "hcl technologies", "tech mahindra",
        "genpact", "mindtree", "mphasis", "hexaware",
        "ltimindtree", "persistent systems", "firstsource",
        "niit technologies"
    ],

    "title_chaser_threshold_months": 18,
    
    "computer_vision_keywords": [
        "yolo", "opencv", "computer vision", "gan", "gans", "cnn", "cnns",
        "image classification", "object detection", "image segmentation", 
        "diffusion models", "stable diffusion", "midjourney", "dall-e",
        "resnet", "vgg", "image processing", "facial recognition"
    ],

    "jd_text_for_embedding": """
    Ideal archetype: Senior Machine Learning Engineer or Search Ranking Engineer from a product-first tech company. 
    They have 5+ years of experience building, evaluating, and shipping production-scale retrieval and ranking systems. 
    Core expertise in Python, embedding-based dense retrieval, vector databases, and Learning-to-Rank. 
    Deep understanding of search relevance metrics (NDCG, MRR, A/B testing). 
    They are builders who own the end-to-end ML pipeline, not just fine-tuning LLMs or building generic CV/GenAI wrappers.
    """,

    # =========================================================================
    # CAREER DESCRIPTION KEYWORDS
    # =========================================================================
    "system_building_keywords": [
        "built", "shipped", "deployed", "designed", "architected",
        "implemented", "developed", "launched", "scaled", "optimized",
        "ranking", "search", "recommendation", "retrieval", "embeddings",
        "production", "inference", "pipeline", "real-time", "latency",
        "a/b test", "evaluation", "metrics", "ndcg", "precision",
        "vector", "index", "reranking", "re-ranking",
        "matching", "scoring", "relevance",
        "ml model", "model serving", "model deployment",
        "feature engineering", "training pipeline", "data pipeline",
        "click model", "engagement metrics", "recruiter"
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
        "hr tech", "recruiting", "talent intelligence"
    ],

    # =========================================================================
    # LOCATION / LOGISTICS
    # =========================================================================
    "preferred_locations": ["noida", "pune"],
    "acceptable_locations": [
        "hyderabad", "mumbai", "delhi", "ncr", "gurgaon", "gurugram",
        "bangalore", "bengaluru", "chennai", "kolkata",
        "greater noida", "new delhi"
    ],
    "country": "india",
    "preferred_notice_days_max": 30,
    "work_mode": "hybrid"
}

# Convenience Exports
ALL_JD_SKILLS = JD_CONFIG["must_have_skills"] + JD_CONFIG["nice_to_have_skills"]
PREFERRED_LOCATIONS: set = set(JD_CONFIG["preferred_locations"])
ACCEPTABLE_LOCATIONS: set = set(JD_CONFIG["acceptable_locations"])