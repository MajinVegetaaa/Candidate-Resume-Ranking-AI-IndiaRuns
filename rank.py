#!/usr/bin/env python3
"""
Redrob Hackathon — Intelligent Candidate Discovery & Ranking
=============================================================

Main orchestrator: streams 100K candidates, scores across 5 dimensions,
detects honeypots, semantically reranks the top 200, and outputs the
final top 100 with fact-grounded reasoning.

Usage:
    python rank.py --candidates ./candidates.jsonl --out ./output/submission.csv

Constraints:
    - ≤ 5 minutes wall-clock on CPU
    - ≤ 16 GB RAM
    - No GPU, no network during ranking
"""

import argparse
import csv
import json
import sys
import time
from tqdm import tqdm

# ── Config ───────────────────────────────────────────────────────────────
from config.jd_config import JD_CONFIG

# ── Scorers (5 dimensions) ──────────────────────────────────────────────
from scorers.career_fit import score_career_fit
from scorers.skill_authenticity import score_skill_authenticity
from scorers.behavioral import score_behavioral
from scorers.education import score_education
from scorers.logistics import score_logistics

# ── Pipeline stages ─────────────────────────────────────────────────────
from pipeline.honeypot_detector import detect_honeypot
from pipeline.semantic_reranker import load_model, semantic_rerank
from pipeline.reasoning_generator import generate_reasoning


# ─── Scoring Weights ─────────────────────────────────────────────────────
WEIGHTS = {
    "career_fit":       0.35,
    "skill_auth":       0.25,
    "behavioral":       0.20,
    "education":        0.10,
    "logistics":        0.10,
}

# How many candidates to pass through semantic reranking
SEMANTIC_RERANK_TOP_N = 500

# Final output size
OUTPUT_TOP_K = 100


def score_candidate(candidate: dict, jd: dict) -> tuple:
    """
    Score a single candidate across all 5 dimensions.

    Returns:
        (composite_score: float, is_honeypot: bool, sub_scores: dict)
    """
    sub_scores = {
        "career_fit":  score_career_fit(candidate, jd),
        "skill_auth":  score_skill_authenticity(candidate, jd),
        "behavioral":  score_behavioral(candidate),
        "education":   score_education(candidate),
        "logistics":   score_logistics(candidate, jd),
    }

    composite = sum(WEIGHTS[k] * sub_scores[k] for k in WEIGHTS)
    is_honeypot = detect_honeypot(candidate)

    if is_honeypot:
        composite = 0.0  # eliminate honeypots from ranking

    return composite, is_honeypot, sub_scores

def _generate_candidate_fingerprint(candidate: dict) -> int:
    """
    Generates a robust, false-positive-proof fingerprint based on the 
    exact sequence of their career and education history.
    """
    career = candidate.get('career_history', []) or []
    edu = candidate.get('education', []) or []

    # 1. Career Fingerprint: Company + Title + Duration (Top 3 roles)
    career_sig = "|".join([
        f"{str(role.get('company')).lower()}_{str(role.get('title')).lower()}_{role.get('duration_months', 0)}"
        for role in career[:3]
    ])

    # 2. Education Fingerprint: Institution + Degree + End Year
    edu_sig = "|".join([
        f"{str(e.get('institution')).lower()}_{str(e.get('degree')).lower()}_{e.get('end_year', '')}"
        for e in edu[:2]
    ])

    # Combine them into a single unique hash
    return hash(f"{career_sig}###{edu_sig}")

def stream_and_score(candidates_path: str, jd: dict) -> list:
    """
    Stream candidates.jsonl line by line and score each candidate.

    Returns:
        list of (candidate_id, composite_score, candidate_dict)
        sorted descending by composite_score
    """
    results = []
    honeypot_count = 0
    total_count = 0
    
    # 👇 FIX: You must initialize these variables before the loop starts!
    duplicate_count = 0
    seen_signatures = set()

    print(f"\n{'='*60}")
    print(f"  PHASE 1: Rule-Based Scoring")
    print(f"  Streaming from: {candidates_path}")
    print(f"{'='*60}\n")

    with open(candidates_path, "r", encoding="utf-8") as f:
        for line in tqdm(f, desc="Scoring candidates", unit=" candidates"):
            line = line.strip()
            if not line:
                continue

            candidate = json.loads(line)
            
            # 🛡️ Unbeatable Duplicate Detection
            cand_fingerprint = _generate_candidate_fingerprint(candidate)
            if cand_fingerprint in seen_signatures:
                duplicate_count += 1
                continue  # Skip them instantly
                
            seen_signatures.add(cand_fingerprint)

            total_count += 1
            cid = candidate["candidate_id"]

            score, is_honeypot, _ = score_candidate(candidate, jd)

            if is_honeypot:
                honeypot_count += 1

            results.append((cid, score, candidate))

    # Sort descending by score, then ascending by candidate_id for tie-breaking
    results.sort(key=lambda x: (-x[1], x[0]))

    print(f"\n  Total candidates processed: {total_count:,}")
    print(f"  Duplicates blocked: {duplicate_count}") # <-- Added this to see the result!
    print(f"  Honeypots detected: {honeypot_count}")
    print(f"  Top score: {results[0][1]:.4f} ({results[0][0]})")
    if len(results) >= 100:
        print(f"  Score at rank 100: {results[99][1]:.4f}")
    if len(results) >= 200:
        print(f"  Score at rank 200: {results[199][1]:.4f}")

    return results
    
def write_submission(top_100: list, output_path: str, jd: dict):
    """
    Write the final submission CSV with reasoning strings.
    Ensures scores are non-increasing and ties are broken by candidate_id ascending.
    """
    print(f"\n{'='*60}")
    print(f"  PHASE 3: Writing Submission")
    print(f"  Output: {output_path}")
    print(f"{'='*60}\n")

    # Sort: score descending, then candidate_id ascending for ties
    top_100.sort(key=lambda x: (-x[1], x[0]))

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])

        prev_score = float("inf")
        write_count = min(len(top_100), OUTPUT_TOP_K)

        # Build rows with clamped scores, rounded to 4 decimals (matching CSV output)
        rows = []
        for rank_idx, (cid, score, candidate) in enumerate(top_100[:write_count]):
            score = min(score, prev_score)
            score = round(score, 4)  # round to match CSV format
            prev_score = score
            rows.append((cid, score, candidate))

        # Fix tie-break ordering: equal scores must have candidate_id ascending
        # Group by rounded score, sort within each group by candidate_id
        fixed_rows = []
        i = 0
        while i < len(rows):
            j = i
            while j < len(rows) and rows[j][1] == rows[i][1]:
                j += 1
            # rows[i:j] all have the same score — sort by candidate_id ascending
            group = sorted(rows[i:j], key=lambda x: x[0])
            fixed_rows.extend(group)
            i = j

        for rank, (cid, score, candidate) in enumerate(fixed_rows, start=1):
            reason = generate_reasoning(candidate, rank, jd)
            writer.writerow([cid, rank, f"{score:.4f}", reason])

    print(f"  ✅ Wrote {write_count} candidates to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Redrob Hackathon — Intelligent Candidate Ranker"
    )
    parser.add_argument(
        "--candidates",
        type=str,
        default="./candidates.jsonl",
        help="Path to candidates.jsonl file"
    )
    parser.add_argument(
        "--out",
        type=str,
        default="./output/Tunday_Kebabs.csv",
        help="Output CSV path"
    )
    parser.add_argument(
        "--no-semantic",
        action="store_true",
        help="Skip semantic reranking (faster, for debugging)"
    )
    args = parser.parse_args()

    start_time = time.time()

    print("\n" + "=" * 60)
    print("  Redrob Hackathon — Intelligent Candidate Ranker")
    print("=" * 60)

    # ─── Phase 1: Stream & Score ─────────────────────────────────────────
    all_scored = stream_and_score(args.candidates, JD_CONFIG)

    phase1_time = time.time() - start_time
    print(f"\n  ⏱  Phase 1 completed in {phase1_time:.1f}s")

    # ─── Phase 2: Semantic Reranking ─────────────────────────────────────
    if not args.no_semantic:
        print(f"\n{'='*60}")
        print(f"  PHASE 2: Semantic Reranking (top {SEMANTIC_RERANK_TOP_N})")
        print(f"{'='*60}\n")

        print("  Loading SentenceTransformer model...")
        model = load_model()

        reranked = semantic_rerank(
            model=model,
            jd_text=JD_CONFIG["jd_text_for_embedding"],
            candidates_with_scores=all_scored,
            top_n=SEMANTIC_RERANK_TOP_N,
        )

        phase2_time = time.time() - start_time - phase1_time
        print(f"\n  ⏱  Phase 2 completed in {phase2_time:.1f}s")
    else:
        print("\n  ⚠  Semantic reranking skipped (--no-semantic)")
        reranked = all_scored

    # ─── Phase 3: Write Submission ───────────────────────────────────────
    write_submission(reranked[:OUTPUT_TOP_K], args.out, JD_CONFIG)

    total_time = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"  ✅ DONE — Total time: {total_time:.1f}s")
    print(f"{'='*60}\n")

    # Safety check: warn if over 4 minutes
    if total_time > 240:
        print("  ⚠  WARNING: Approaching 5-minute limit!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
