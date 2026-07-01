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
import yaml
import os
from datetime import date

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "ranking_config.yaml")
with open(CONFIG_PATH, "r") as f:
    RANKING_CONFIG = yaml.safe_load(f)


def load_jd_text(jd_path: str) -> str:
    """Read the raw JD text directly from the .docx file.
    Falls back to an empty string on failure."""
    try:
        from docx import Document
        doc = Document(jd_path)
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        print(f"  ✅ Loaded JD from {jd_path} ({len(text):,} chars)")
        return text
    except Exception as e:
        print(f"  ⚠  Could not read JD docx ({e}). Falling back to empty string.")
        return ""

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
WEIGHTS = RANKING_CONFIG["scoring_weights"]

BI_ENCODER_TOP_N = RANKING_CONFIG["pipeline"]["phase2_bi_encoder"]["top_n_pool"]
CROSS_ENCODER_TOP_N = RANKING_CONFIG["pipeline"]["phase3_cross_encoder"]["top_n_pool"]
OUTPUT_TOP_K = RANKING_CONFIG["pipeline"]["output"]["top_k"]

def _days_since(date_str: str) -> int:
    try:
        d = date.fromisoformat(str(date_str)[:10])
        return (date.today() - d).days
    except Exception:
        return 9999

#Behavioral dead candidates (inactive + low response rate) should be gated
def compute_availability_multiplier(candidate):
    signals = candidate.get("redrob_signals", {})
    days_inactive = _days_since(signals.get("last_active_date", ""))
    response_rate = signals.get("recruiter_response_rate", 0) or 0
    if days_inactive > 180 and response_rate < 0.2:  return 0.3
    if days_inactive > 90 and response_rate < 0.15:  return 0.4
    if not signals.get("open_to_work_flag") and days_inactive > 60: return 0.75
    return 1.0
    
def _notice_multiplier(candidate: dict) -> float:
    notice_days = candidate.get("redrob_signals", {}).get("notice_period_days", 0) or 0
    if notice_days <= 30:   return 1.0
    elif notice_days <= 60: return 0.92
    elif notice_days <= 90: return 0.80
    else:                   return 0.65

def score_candidate(candidate: dict, jd: dict) -> tuple:
    sub_scores = {
        "career_fit":  score_career_fit(candidate, jd),
        "skill_auth":  score_skill_authenticity(candidate, jd),
        "behavioral":  score_behavioral(candidate),
        "education":   score_education(candidate),
        "logistics":   score_logistics(candidate, jd),
    }
    composite = sum(WEIGHTS[k] * sub_scores[k] for k in WEIGHTS)
    # 🚨 STRUCTURAL FLOORS (YoE & Foreign Location)
    profile = candidate.get("profile", {})
    yoe = profile.get("years_of_experience", 0)
    country = str(profile.get("country", "")).strip().lower()
    
    if yoe < 4.0:
        composite *= 0.55  # JD explicitly requires 4+ years minimum

    if country not in ("", "india"):
        composite *= 0.50

    is_honeypot = detect_honeypot(candidate)
    if is_honeypot:
        composite = 0.0
    else:
        composite *= _notice_multiplier(candidate)
        composite *= compute_availability_multiplier(candidate)
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
    Writes the top 100 candidates to the CSV.
    Safely slices the top outputs from Phase 3, avoiding sorting the entire 
    100,000 pool which would allow un-reranked candidates to bubble up.
    """
    print(f"\n{'='*60}")
    print(f"  PHASE 4: Writing Submission")
    print(f"  Output: {output_path}")
    print(f"{'='*60}\n")

    # Slice ONLY the top K candidates (as ordered by the final semantic phase)
    top_candidates = all_ranked_candidates[:OUTPUT_TOP_K]

    # Resolve any rare ties strictly by candidate_id ascending
    top_candidates.sort(key=lambda x: (-round(x[1], 4), x[0]))

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        
        for rank, (cid, score, candidate) in enumerate(top_candidates, start=1):
            score_rounded = round(score, 4)
            reason = generate_reasoning(candidate, rank, jd)
            writer.writerow([cid, rank, f"{score_rounded:.4f}", reason])

    print(f"  ✅ Wrote {len(top_candidates)} candidates to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Redrob Hackathon — Intelligent Candidate Ranker")
    parser.add_argument("--candidates", type=str, default="./candidates.jsonl")
    parser.add_argument("--jd", type=str, default="../India_runs_data_and_ai_challenge/job_description.docx",
                        help="Path to the job_description.docx file")
    parser.add_argument("--out", type=str, default="./output/Tunday_Kebabs.csv")
    parser.add_argument("--no-semantic", action="store_true")
    args = parser.parse_args()

    start_time = time.time()

    print("\n" + "=" * 60)
    print("  Redrob Hackathon — Intelligent Candidate Ranker")
    print("=" * 60)

    # ─── Load Raw JD Text for Semantic Phases ────────────────────────────
    jd_text = load_jd_text(args.jd)
    # ─── Phase 1: Stream & Score ─────────────────────────────────────────
    all_scored = stream_and_score(args.candidates, JD_CONFIG)
    phase1_time = time.time() - start_time
    print(f"\n  ⏱  Phase 1 completed in {phase1_time:.1f}s")

    # ─── Phase 2: Bi-Encoder Reranking ───────────────────────────────────
    if not args.no_semantic:
        print(f"\n{'='*60}")
        print(f"  PHASE 2: Bi-Encoder Reranking (top {BI_ENCODER_TOP_N})")
        print(f"{'='*60}\n")

        bi_model_name = RANKING_CONFIG["pipeline"]["phase2_bi_encoder"]["model_name"]
        bi_device = RANKING_CONFIG["pipeline"]["phase2_bi_encoder"].get("device", "cpu")
        print(f"  Loading Bi-Encoder model ({bi_model_name}) on {bi_device}...")
        bi_model = load_bi_encoder(bi_model_name, device=bi_device)

        phase2_scored = bi_encoder_rerank(
            model=bi_model,
            jd_text=jd_text,
            candidates_with_scores=all_scored,
            top_n=BI_ENCODER_TOP_N,
        )
        phase2_time = time.time() - start_time - phase1_time
        print(f"\n  ⏱  Phase 2 completed in {phase2_time:.1f}s")

    # ─── Phase 3: Cross-Encoder Reranking ────────────────────────────────
        print(f"\n{'='*60}")
        print(f"  PHASE 3: Cross-Encoder Deep Reranking (top {CROSS_ENCODER_TOP_N})")
        print(f"{'='*60}\n")

        ce_model_name = RANKING_CONFIG["pipeline"]["phase3_cross_encoder"]["model_name"]
        ce_device = RANKING_CONFIG["pipeline"]["phase3_cross_encoder"].get("device", "cpu")
        print(f"  Loading Cross-Encoder model ({ce_model_name}) on {ce_device}...")
        ce_model = load_cross_encoder(ce_model_name, device=ce_device)

        final_scored = cross_encoder_rerank(
            model=ce_model,
            jd_text=jd_text,
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
    import sys
    sys.exit(main())
