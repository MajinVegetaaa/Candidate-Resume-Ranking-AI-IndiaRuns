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

# ── Scoring weights (same as rank.py) ────────────────────────────────
WEIGHTS = {
    "career_fit":  0.35,
    "skill_auth":  0.25,
    "behavioral":  0.20,
    "education":   0.10,
    "logistics":   0.10,
}

OUTPUT_TOP_K = 100


def score_candidate(candidate: dict) -> tuple:
    """Score a single candidate across all 5 dimensions."""
    sub_scores = {
        "career_fit":  score_career_fit(candidate, JD_CONFIG),
        "skill_auth":  score_skill_authenticity(candidate, JD_CONFIG),
        "behavioral":  score_behavioral(candidate),
        "education":   score_education(candidate),
        "logistics":   score_logistics(candidate, JD_CONFIG),
    }
    composite = sum(WEIGHTS[k] * sub_scores[k] for k in WEIGHTS)
    is_honeypot = detect_honeypot(candidate)
    if is_honeypot:
        composite = 0.0
    return composite, is_honeypot, sub_scores


def run_ranking(candidates: list[dict]) -> list[dict]:
    """Run the full rule-based ranking pipeline on a candidate list."""
    results = []
    honeypot_count = 0

    for candidate in candidates:
        cid = candidate["candidate_id"]
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
Upload a candidate JSONL file (≤100 candidates) to see the ranking in action.
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

        if st.button("🚀 Run Ranker", type="primary"):
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
                    "Career": f"{s['career_fit']:.3f}",
                    "Skills": f"{s['skill_auth']:.3f}",
                    "Behav": f"{s['behavioral']:.3f}",
                    "Edu": f"{s['education']:.3f}",
                    "Logist": f"{s['logistics']:.3f}",
                    "Honeypot": "⚠️" if entry["is_honeypot"] else "",
                })

            st.dataframe(table_data, use_container_width=True, hide_index=True)

            # Download CSV
            st.divider()
            csv_output = results_to_csv(results, top_k)
            st.download_button(
                "📥 Download Submission CSV",
                csv_output,
                file_name="submission.csv",
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
