# 🏆 Redrob Hackathon — Intelligent Candidate Ranker

An AI-powered candidate ranking system that processes **100,000 profiles in ~30 seconds** to find the best-fit candidates for a Senior AI/ML Ranking Systems Engineer role.

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the ranker
python rank.py --candidates /path/to/candidates.jsonl --out ./output/Tunday_Kebabs.csv

# 3. Validate
python validate_submission.py ./output/Tunday_Kebabs.csv

# 4. Run quality checks
python tests/run_quality_checks.py ./output/Tunday_Kebabs.csv /path/to/candidates.jsonl
```

> **Note on Pre-computation:** The very first time `rank.py` runs, the `sentence-transformers` library will download the `all-MiniLM-L6-v2` model weights (~80MB). This is a one-time pre-computation step. Subsequent runs will use the cached local weights and will not require network access, ensuring compliance with the Stage 3 compute constraints.

## 📁 Project Structure

```
redrob-ranker/
│
├── rank.py                            # Main entry point (CLI)
├── requirements.txt                   # Python dependencies
├── submission_metadata.yaml           # Hackathon submission metadata
├── streamlit_app.py                   # Sandbox demo app
├── .gitignore                         # Git exclusions
├── README.md                          # This file
│
├── config/                            # ── Configuration ──
│   ├── __init__.py                    #   Exports JD_CONFIG, ALL_JD_SKILLS
│   └── jd_config.py                   #   Structured JD: titles, skills, weights, anti-patterns
│
├── scorers/                           # ── 5 Scoring Dimensions ──
│   ├── __init__.py                    #   Exports all scorer functions
│   ├── career_fit.py                  #   (0.35) Title match, role descriptions, tenure, industry
│   ├── skill_authenticity.py          #   (0.25) Proficiency, endorsements, duration, assessments
│   ├── behavioral.py                  #   (0.20) Recency, response rate, GitHub, verification
│   ├── education.py                   #   (0.10) Institution tier, field relevance, degree level
│   └── logistics.py                   #   (0.10) Location, notice period, work mode
│
├── pipeline/                          # ── Pipeline Stages ──
│   ├── __init__.py                    #   Exports detect_honeypot, semantic_rerank, etc.
│   ├── honeypot_detector.py           #   5-check fabricated profile filter (flags ≥ 2 = honeypot)
│   ├── semantic_reranker.py           #   all-MiniLM-L6-v2 cosine similarity reranking
│   └── reasoning_generator.py         #   Fact-grounded, varied reasoning string builder
│
├── tests/                             # ── Quality Assurance ──
│   ├── run_quality_checks.py          #   Honeypot, anti-gaming, red-flag, distribution checks
│   └── test_candidates.jsonl          #   50-candidate sample for quick testing
│
└── output/                            # ── Results ──
    └── submission.csv                 #   Final ranked top-100 candidates
```

## ⚙️ How It Works

### Two-Pass Architecture

```
Phase 1: Rule-Based Scoring (~16s)     Phase 2: Semantic Reranking (~14s)
┌──────────────────────────────────┐   ┌──────────────────────────────────┐
│  Stream 100K candidates          │   │  Top 200 → MiniLM-L6-v2         │
│  Score across 5 dimensions       │──►│  Cosine similarity vs JD         │
│  Detect & eliminate honeypots    │   │  Blend: 60% rule + 40% sem       │
│  Sort → Top 200                  │   │  Output Top 100 + reasoning      │
└──────────────────────────────────┘   └──────────────────────────────────┘
```

### Scoring Dimensions

| Dimension | Weight | What It Measures |
|-----------|--------|------------------|
| **Career Fit** | 0.35 | Title alignment (with seniority multipliers), role descriptions (per-role keyword scoring), product vs consulting ratio, tenure stability, YoE bell curve |
| **Skill Authenticity** | 0.25 | Proficiency × endorsements × duration × assessments (catches keyword stuffers via 0.3× penalty) |
| **Behavioral** | 0.20 | Last active date, response rate, GitHub activity, profile completeness, interview completion |
| **Education** | 0.10 | Institution tier, CS/AI/ML field match, degree level |
| **Logistics** | 0.10 | Noida/Pune preference, notice period, hybrid work mode |

### Anti-Gaming Features

- **Keyword stuffer detection**: ≥5 beginner-level skills with 0 endorsements and 0 duration → 0.3× penalty
- **Seniority-aware title matching**: Junior/Intern titles get 0.6× multiplier; staff/principal get 1.1×
- **Context-aware "Backend Engineer"**: Only full score if career descriptions contain ML/AI keywords
- **Consulting-only penalty**: 0.3× if entire career is at consulting firms (TCS, Infosys, etc.)

### Honeypot Detection

Catches fabricated profiles via 5 independent checks:
1. Overlapping employment dates (>30 days)
2. Skill duration exceeding total career length
3. Impossible technology timelines (e.g., 5 years of ChatGPT)
4. Education-career timeline contradictions
5. Total career months exceeding reported YoE

### Reasoning Generation

Each reasoning string is unique and fact-grounded:
- Rank-tiered openers (varied across 3 sentence patterns per tier)
- Specific career highlights with role title, company, duration
- Named skills with proficiency levels and durations
- Exact behavioral signal values (response rate %, GitHub score)
- Honest gap acknowledgment for lower-ranked candidates

## 🏅 Performance

| Metric | Result | Limit |
|--------|--------|-------|
| **Total time** | ~30s | 300s |
| **RAM usage** | ~2 GB | 16 GB |
| **GPU** | Not needed | Not allowed |
| **Network** | Not needed | Not allowed |

## 🧪 Testing

```bash
# Quick test on 50-candidate sample (no semantic reranking)
python rank.py --candidates tests/test_candidates.jsonl --out ./output/test_out.csv --no-semantic

# Full quality checks
python tests/run_quality_checks.py ./output/submission.csv /path/to/candidates.jsonl
```

## 🖥️ Sandbox Demo

```bash
# Run the Streamlit sandbox app
streamlit run streamlit_app.py

# Upload tests/test_candidates.jsonl for a quick demo
```

## 📋 CLI Options

| Flag | Description |
|------|-------------|
| `--candidates PATH` | Path to candidates.jsonl (default: `./candidates.jsonl`) |
| `--out PATH` | Output CSV path (default: `./output/submission.csv`) |
| `--no-semantic` | Skip Phase 2 semantic reranking (for faster debugging) |
