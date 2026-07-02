# 🏆 Candidate Resume Ranking AI - IndiaRuns Hackathon (Redrob)
### Team: Tunday Kebabs

An intelligent, AI-powered candidate ranking system that processes **100,000 profiles in ~263 seconds**.

(No GPU, No Network, < 5 minutes)

---

## 🚀 Quick Start

Follow these steps to run the ranker on your local machine.

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the ranker
# Note: The first run will download model weights (~300MB total). Subsequent runs are instant and offline.
python rank.py --candidates /path/to/candidates.jsonl --out ./output/submission.csv

# 3. Validate your final submission
python validate_submission.py ./output/submission.csv
```

---

## ⚙️ How It Works (4-Phase Architecture)

To process 100,000 candidates quickly while maintaining deep semantic accuracy, we use a cascaded approach:

1. **Phase 1: Rule-Based Scoring (~36s)**
   - Streams all 100K candidates.
   - Applies lightweight rules for career fit, skills, logistics, and behavioral signals.
   - Filters out duplicates and **honeypots** (caught over 74,000 bad profiles).
   - Output: Top 1,000 candidates.

2. **Phase 2: Fast Semantic Search (~205s)**
   - Uses a **Bi-Encoder** (`all-mpnet-base-v2`) to compare the Job Description against the Top 1,000 candidates.
   - Blends the semantic score with the Phase 1 rule score.
   - Output: Top 300 candidates.

3. **Phase 3: Deep Contextual Reranking (~23s)**
   - Uses a heavy **Cross-Encoder** (`ms-marco-MiniLM-L-6-v2`) on the Top 300 for intense, deep-context evaluation.
   - Blends this final semantic score with previous scores.
   - Output: Final highly-accurate ranking.

4. **Phase 4: Output & Reasoning**
   - Cuts off at exactly 100 candidates.
   - Generates a unique, fact-grounded reasoning string using a custom **5-Tier Natural Language Generation (NLG)** engine.
   - Writes the final `submission.csv`.

---

## 📁 Project Structure

```text
redrob-ranker/
├── rank.py                            # Main entry point (CLI)
├── requirements.txt                   # Python dependencies
├── README.md                          # This file
│
├── config/                            # ── Configuration (No Hardcoding!) ──
│   ├── ranking_config.yaml            # Pipeline settings, weights, model selection, CPU config
│   ├── jd_config.py                   # Structured JD: titles, skills, keywords, anti-patterns
│   └── __init__.py
│
├── scorers/                           # ── Rule-Based Dimensions (Phase 1) ──
│   ├── career_fit.py                  # (0.35) Title match, industry, tenure
│   ├── skill_authenticity.py          # (0.25) Proficiency, duration, endorsements
│   ├── behavioral.py                  # (0.20) GitHub, response rate, open-to-work
│   ├── education.py                   # (0.10) Institution tier, degree relevance
│   └── logistics.py                   # (0.10) Location, notice period
│
├── pipeline/                          # ── AI & Data Pipeline ──
│   ├── semantic_reranker.py           # Phase 2 & 3: Bi-Encoder and Cross-Encoder logic
│   ├── honeypot_detector.py           # 5-check fabricated profile filter
│   └── reasoning_generator.py         # Dynamic, fact-grounded reasoning string builder
│
└── output/                            # ── Results ──
    └── submission.csv                 # Final ranked top-100 candidates
```

---

## 🛠️ Configuration & Tuning

`config/` directory:

- **`ranking_config.yaml`**: Adjust scoring weights, change the HuggingFace models, modify the blending ratios between rules and semantics, or change the Top-N pool sizes. 
  - *Hardware Compliance:* The `device` is explicitly forced to `"cpu"` here to guarantee compliance with the hackathon's Stage 3 sandbox environment.
- **`jd_config.py`**: Add new must-have skills, update preferred cities, or change the Job Description embedding text entirely if targeting a new role.

---

## 🛡️ Anti-Gaming & Honeypots

The dataset contains traps that this ranker automatically avoids:

- **Honeypot Filter**: Detects impossible profiles (e.g., overlapping full-time jobs, skills claiming 5+ years of experience for technology invented 2 years ago).
- **Keyword Stuffer Penalty**: Candidates with 10+ "expert" skills but 0 endorsements and 0 duration are heavily penalized.
- **Consulting Penalty**: A slight adjustment for candidates whose entire career is in consulting, favoring those with product company experience as requested by the JD.

---

## 🏅 Performance Metrics

| Metric | Result | Hackathon Limit |
|--------|--------|-----------------|
| **Total Runtime** | ~263 seconds | 300 seconds (5 min) |
| **RAM Usage** | ~2 GB | 16 GB |
| **GPU/Hardware** | Forced `CPU-only` | No GPU allowed |
| **Network** | Zero (Offline after init) | No network allowed |
