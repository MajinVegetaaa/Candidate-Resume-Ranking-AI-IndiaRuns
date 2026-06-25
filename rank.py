#!/usr/bin/env python3
"""
Redrob Hackathon — Intelligent Candidate Discovery & Ranking
=============================================================

Main orchestrator: streams 100K candidates, scores across 5 dimensions,
detects honeypots, semantically reranks the top 200, and outputs the
final top 100 with fact-grounded reasoning.
"""

import argparse
import csv
import json
import sys
import time
import hashlib  # Added for deterministic fingerprinting
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
# FIXED: Imported the correct multi-phase pipeline functions
from pipeline.semantic_reranker import load_bi_encoder, load_cross_encoder, bi_encoder_rerank, cross_encoder_rerank
from pipeline.reasoning_generator import generate_reasoning


# ─── Scoring Weights ─────────────────────────────────────────────────────
WEIGHTS = {
    "career_fit":       0.35,
    "skill_auth":       0.25,
    "behavioral":       0.20,
    "education":        0.10,
    "logistics":        0.10,
}

BI_ENCODER_TOP_N = 1500     # Phase 2 Pool
CROSS_ENCODER_TOP_N = 200   # Phase 3 Pool
OUTPUT_TOP_K = 100          # Final Output


def score_candidate(candidate: dict, jd: dict) -> tuple:
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
        composite = 0.0

    return composite, is_honeypot, sub_scores

def _generate_candidate_fingerprint(candidate: dict) -> str:
    """
    FIXED: Generates a deterministic MD5 hash string instead of Python's 
    unstable process-based hash() function.
    """
    career = candidate.get('career_history', []) or []
    edu = candidate.get('education', []) or []

    career_sig = "|".join([
        f"{str(role.get('company')).lower()}_{str(role.get('title')).lower()}_{role.get('duration_months', 0)}"
        for role in career[:3]
    ])

    edu_sig = "|".join([
        f"{str(e.get('institution')).lower()}_{str(e.get('degree')).lower()}_{e.get('end_year', '')}"
        for e in edu[:2]
    ])

    combined_str = f"{career_sig}###{edu_sig}"
    return hashlib.md5(combined_str.encode('utf-8')).hexdigest()

def stream_and_score(candidates_path: str, jd: dict) -> list:
    results = []
    honeypot_count = 0
    total_count = 0
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
            
            cand_fingerprint = _generate_candidate_fingerprint(candidate)
            if cand_fingerprint in seen_signatures:
                duplicate_count += 1
                continue
                
            seen_signatures.add(cand_fingerprint)
            total_count += 1
            cid = candidate["candidate_id"]

            score, is_honeypot, _ = score_candidate(candidate, jd)

            if is_honeypot:
                honeypot_count += 1

            results.append((cid, score, candidate))

    results.sort(key=lambda x: (-x[1], x[0]))

    print(f"\n  Total candidates processed: {total_count:,}")
    print(f"  Duplicates blocked: {duplicate_count}")
    print(f"  Honeypots detected: {honeypot_count}")
    print(f"  Top score: {results[0][1]:.4f} ({results[0][0]})")
    
    return results
    
def write_submission(all_ranked_candidates: list, output_path: str, jd: dict):
    """
    FIXED: Processes entire dataset pool first to resolve true boundary tie-breaks 
    BEFORE cutting off at the final top 100 rows.
    """
    print(f"\n{'='*60}")
    print(f"  PHASE 4: Writing Submission")
    print(f"  Output: {output_path}")
    print(f"{'='*60}\n")

    # Sort everything up front: score descending, candidate_id ascending
    all_ranked_candidates.sort(key=lambda x: (-x[1], x[0]))

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])

        prev_score = float("inf")
        rows = []
        
        # Smooth and round all scores safely across the entire pool
        for cid, score, candidate in all_ranked_candidates:
            score = min(score, prev_score)
            score = round(score, 4)
            prev_score = score
            rows.append((cid, score, candidate))

        # Group and break ties safely across data groups
        fixed_rows = []
        i = 0
        while i < len(rows):
            j = i
            while j < len(rows) and rows[j][1] == rows[i][1]:
                j += 1
            group = sorted(rows[i:j], key=lambda x: x[0])
            fixed_rows.extend(group)
            i = j

        # Now cleanly cut off exactly at the target 100 row output limit
        write_count = min(len(fixed_rows), OUTPUT_TOP_K)
        for rank, (cid, score, candidate) in enumerate(fixed_rows[:write_count], start=1):
            reason = generate_reasoning(candidate, rank, jd)
            writer.writerow([cid, rank, f"{score:.4f}", reason])

    print(f"  ✅ Wrote {write_count} candidates to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Redrob Hackathon — Intelligent Candidate Ranker")
    parser.add_argument("--candidates", type=str, default="./candidates.jsonl")
    parser.add_argument("--out", type=str, default="./output/Tunday_Kebabs.csv")
    parser.add_argument("--no-semantic", action="store_true")
    args = parser.parse_args()

    start_time = time.time()

    print("\n" + "=" * 60)
    print("  Redrob Hackathon — Intelligent Candidate Ranker")
    print("=" * 60)

    # ─── Phase 1: Stream & Score ─────────────────────────────────────────
    all_scored = stream_and_score(args.candidates, JD_CONFIG)
    phase1_time = time.time() - start_time
    print(f"\n  ⏱  Phase 1 completed in {phase1_time:.1f}s")

    # ─── Phase 2: Bi-Encoder Reranking ───────────────────────────────────
    if not args.no_semantic:
        print(f"\n{'='*60}")
        print(f"  PHASE 2: Bi-Encoder Reranking (top {BI_ENCODER_TOP_N})")
        print(f"{'='*60}\n")

        print("  Loading Bi-Encoder model (all-mpnet-base-v2)...")
        bi_model = load_bi_encoder()

        phase2_scored = bi_encoder_rerank(
            model=bi_model,
            jd_text=JD_CONFIG["jd_text_for_embedding"],
            candidates_with_scores=all_scored,
            top_n=BI_ENCODER_TOP_N,
        )
        phase2_time = time.time() - start_time - phase1_time
        print(f"\n  ⏱  Phase 2 completed in {phase2_time:.1f}s")

    # ─── Phase 3: Cross-Encoder Reranking ────────────────────────────────
        print(f"\n{'='*60}")
        print(f"  PHASE 3: Cross-Encoder Deep Reranking (top {CROSS_ENCODER_TOP_N})")
        print(f"{'='*60}\n")

        print("  Loading Cross-Encoder model (ms-marco-MiniLM-L-6-v2)...")
        ce_model = load_cross_encoder()

        final_scored = cross_encoder_rerank(
            model=ce_model,
            jd_text=JD_CONFIG["jd_text_for_embedding"],
            candidates_with_scores=phase2_scored,
            top_n=CROSS_ENCODER_TOP_N,
        )
        phase3_time = time.time() - start_time - phase1_time - phase2_time
        print(f"\n  ⏱  Phase 3 completed in {phase3_time:.1f}s")
    else:
        print("\n  ⚠  Semantic reranking skipped (--no-semantic)")
        final_scored = all_scored

    # ─── Phase 4: Write Submission ───────────────────────────────────────
    # FIXED: Passed entire un-sliced list to protect boundary constraints
    write_submission(final_scored, args.out, JD_CONFIG)

if __name__ == "__main__":
    sys.exit(main())