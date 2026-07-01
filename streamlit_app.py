"""
Redrob Ranker — Streamlit Sandbox Demo
=======================================
A lightweight demo interface for the Intelligent Candidate Discovery
& Ranking system. Accepts a small candidate sample (≤100 candidates),
runs the full ranking pipeline, and displays results.

Run with:
    streamlit run streamlit_app.py
"""

import io
import csv
import json
import time
import sys
import os
import yaml

import streamlit as st

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.jd_config import JD_CONFIG
from scorers.career_fit import score_career_fit
from scorers.skill_authenticity import score_skill_authenticity
from scorers.behavioral import score_behavioral
from scorers.education import score_education
from scorers.logistics import score_logistics
from pipeline.honeypot_detector import detect_honeypot
from pipeline.reasoning_generator import generate_reasoning

# ── Load dynamic config to ensure Sandbox matches Production ──────────
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "ranking_config.yaml")
with open(CONFIG_PATH, "r") as f:
    RANKING_CONFIG = yaml.safe_load(f)

WEIGHTS = RANKING_CONFIG["scoring_weights"]
OUTPUT_TOP_K = 100


def score_candidate(candidate: dict) -> tuple:
    """Score a single candidate mirroring the exact logic in rank.py."""
    # 🚨 SHORT-CIRCUIT: Honeypot check first to save compute
    is_honeypot = detect_honeypot(candidate)
    if is_honeypot:
        return 0.0, True, {}

    sub_scores = {
        "career_fit":  score_career_fit(candidate, JD_CONFIG),
        "skill_auth":  score_skill_authenticity(candidate, JD_CONFIG),
        "behavioral":  score_behavioral(candidate),
        "education":   score_education(candidate),
        "logistics":   score_logistics(candidate, JD_CONFIG),
    }

    # 🚨 DEFENSIVE CLEAN KILL SWITCH 🚨
    if sub_scores["logistics"] <= 0.0 or sub_scores["behavioral"] <= 0.20:
        composite = 0.0
    else:
        # Calculate Base Composite
        composite = sum(WEIGHTS[k] * sub_scores[k] for k in WEIGHTS)

        # 🚨 STRUCTURAL QUALITY FLOOR 
        career_skill_strength = (
            WEIGHTS["career_fit"] * sub_scores["career_fit"] +
            WEIGHTS["skill_auth"] * sub_scores["skill_auth"]
        ) / (WEIGHTS["career_fit"] + WEIGHTS["skill_auth"])

        if career_skill_strength < 0.30:
            composite *= 0.25  # Hard secondary penalty
            
        # 🚨 THE "RAISE THE BAR" NOTICE PERIOD MULTIPLIER 🚨
        signals = candidate.get("redrob_signals", {})
        notice_days = signals.get("notice_period_days", 0)
        
        if notice_days <= 30:
            multiplier = 1.0
        elif notice_days <= 60:
            multiplier = 0.92
        elif notice_days <= 90:
            multiplier = 0.80
        else:
            multiplier = 0.65
            
        composite = composite * multiplier

    return composite, False, sub_scores


def run_ranking(candidates: list[dict]) -> list[dict]:
    """Run the full rule-based ranking pipeline on a candidate list."""
    results = []
    honeypot_count = 0

    for candidate in candidates:
        cid = candidate.get("candidate_id", "UNKNOWN")
        score, is_hp, sub_scores = score_candidate(candidate)
        if is_hp:
            honeypot_count += 1
        results.append({
            "candidate_id": cid,
            "score": score,
            "is_honeypot": is_hp,
            "sub_scores": sub_scores,
            "candidate": candidate,
        })

    # Sort: score descending, candidate_id ascending for ties
    results.sort(key=lambda x: (-x["score"], x["candidate_id"]))

    return results


def results_to_csv(results: list[dict], top_k: int) -> str:
    """Convert ranking results to submission CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["candidate_id", "rank", "score", "reasoning"])

    for rank, entry in enumerate(results[:top_k], start=1):
        cid = entry["candidate_id"]
        score = round(entry["score"], 4)
        reason = generate_reasoning(entry["candidate"], rank, JD_CONFIG)
        writer.writerow([cid, rank, f"{score:.4f}", reason])

    return output.getvalue()


# ── Streamlit UI ─────────────────────────────────────────────────────

st.set_page_config(
    page_title="Redrob Ranker — Sandbox Demo",
    page_icon="🏆",
    layout="wide",
)

st.title("🏆 Redrob Intelligent Candidate Ranker")
st.markdown("""
**Sandbox demo** for the Intelligent Candidate Discovery & Ranking Challenge.
Upload a candidate JSONL file (≤100 candidates) to see Phase 1 Heuristics in action.
*(Semantic Bi-Encoder/Cross-Encoder reranking is bypassed in this UI for rendering speed)*
""")

st.divider()

# File upload
uploaded_file = st.file_uploader(
    "Upload candidates file (.jsonl)",
    type=["jsonl", "json"],
    help="Upload a JSONL file with candidate profiles (max 100 candidates).",
)

if uploaded_file is not None:
    # Parse candidates
    raw = uploaded_file.read().decode("utf-8")
    candidates = []
    for line in raw.strip().split("\n"):
        line = line.strip()
        if line:
            try:
                candidates.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    if not candidates:
        st.error("No valid candidate records found in the uploaded file.")
    elif len(candidates) > 100:
        st.warning(f"File contains {len(candidates)} candidates. Using first 100 for demo.")
        candidates = candidates[:100]
    else:
        st.success(f"Loaded **{len(candidates)}** candidates.")

    if candidates:
        st.divider()

        if st.button("🚀 Run Phase 1 Ranker", type="primary"):
            start = time.time()

            with st.spinner("Scoring candidates..."):
                results = run_ranking(candidates)

            elapsed = time.time() - start

            # Summary metrics
            top_k = min(len(results), OUTPUT_TOP_K)
            honeypots = sum(1 for r in results if r["is_honeypot"])

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Candidates Scored", len(results))
            col2.metric("Honeypots Detected", honeypots)
            col3.metric("Output Size", f"Top {top_k}")
            col4.metric("Time", f"{elapsed:.1f}s")

            st.divider()

            # Results table
            st.subheader("📊 Ranked Results")
            table_data = []
            for rank, entry in enumerate(results[:top_k], start=1):
                c = entry["candidate"]
                p = c.get("profile", {})
                s = entry["sub_scores"]
                table_data.append({
                    "Rank": rank,
                    "ID": entry["candidate_id"],
                    "Score": f"{entry['score']:.4f}",
                    "Title": p.get("current_title", ""),
                    "Company": p.get("current_company", ""),
                    "YoE": f"{p.get('years_of_experience', 0):.1f}",
                    "Location": p.get("location", ""),
                    "Career": f"{s.get('career_fit', 0):.3f}",
                    "Skills": f"{s.get('skill_auth', 0):.3f}",
                    "Behav": f"{s.get('behavioral', 0):.3f}",
                    "Edu": f"{s.get('education', 0):.3f}",
                    "Logist": f"{s.get('logistics', 0):.3f}",
                    "Honeypot": "⚠️" if entry["is_honeypot"] else "",
                })

            st.dataframe(table_data, use_container_width=True, hide_index=True)

            # Download CSV
            st.divider()
            csv_output = results_to_csv(results, top_k)
            st.download_button(
                "📥 Download Phase 1 CSV",
                csv_output,
                file_name="sandbox_submission.csv",
                mime="text/csv",
            )

else:
    st.info("👆 Upload a `.jsonl` file to get started. Use `tests/test_candidates.jsonl` for a quick test.")

# Footer
st.divider()
st.caption(
    "Built for the Redrob × Hack2Skill Data & AI Challenge. "
    "Rule-based scoring (5 dimensions) + honeypot detection. "
    "Semantic reranking is disabled in sandbox mode for speed."
)
