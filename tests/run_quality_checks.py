#!/usr/bin/env python3
"""
Quality Checks — Validate the ranker output beyond format correctness.

Runs 5 checks:
  1. Honeypot leak check (< 10 in top 100)
  2. Keyword stuffer check (0 in top 100)
  3. Red-flag title check (0 in top 100)
  4. Score distribution analysis
  5. Top 10 spot-check

Usage:
    python tests/run_quality_checks.py ./output/submission.csv /path/to/candidates.jsonl
"""

import csv
import json
import math
import sys
import os

# Add project root to path so we can import pipeline modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.honeypot_detector import detect_honeypot


RED_FLAG_TITLES = [
    "marketing manager", "hr manager", "content writer",
    "graphic designer", "accountant", "sales executive",
    "customer support", "civil engineer", "mechanical engineer",
    "operations manager", "project manager",
]


def load_candidates(candidates_path: str) -> dict:
    """Load all candidates into a dict keyed by candidate_id."""
    print(f"Loading candidates from {candidates_path}...")
    candidates = {}
    with open(candidates_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                c = json.loads(line)
                candidates[c["candidate_id"]] = c
    print(f"  Loaded {len(candidates):,} candidates\n")
    return candidates


def load_submission(submission_path: str) -> list:
    """Load submission CSV rows."""
    with open(submission_path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def check_honeypots(rows: list, candidates: dict) -> bool:
    """TEST 1: Check if any honeypots leaked into the top 100."""
    print("=" * 60)
    print("  TEST 1: Honeypot Check")
    print("=" * 60)

    count = 0
    for row in rows:
        cid = row["candidate_id"]
        if detect_honeypot(candidates[cid]):
            count += 1
            p = candidates[cid].get("profile", {})
            print(f'  ⚠ Honeypot at rank {row["rank"]}: {cid} ({p.get("current_title", "?")})')

    passed = count < 10
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\n  Honeypots in top 100: {count}/100 (limit: <10) {status}\n")
    return passed


def check_keyword_stuffers(rows: list, candidates: dict) -> bool:
    """TEST 2: Check if keyword stuffers made it into top 100."""
    print("=" * 60)
    print("  TEST 2: Anti-Gaming (Keyword Stuffers)")
    print("=" * 60)

    count = 0
    for row in rows:
        c = candidates[row["candidate_id"]]
        skills = c.get("skills") or []
        stuffed = sum(
            1 for s in skills
            if (s.get("proficiency", "") == "beginner"
                and s.get("endorsements", 0) == 0
                and (s.get("duration_months", 0) or 0) == 0)
        )
        if stuffed >= 5:
            count += 1
            p = c.get("profile", {})
            print(f'  ⚠ Rank {row["rank"]}: {p.get("current_title", "")} — {stuffed} stuffed skills')

    passed = count == 0
    status = "✅ PASS" if passed else "⚠ WARNING"
    print(f"\n  Keyword stuffers in top 100: {count} {status}\n")
    return passed


def check_red_flag_titles(rows: list, candidates: dict) -> bool:
    """TEST 3: Check if red-flag titles appear in top 100."""
    print("=" * 60)
    print("  TEST 3: Red-Flag Titles")
    print("=" * 60)

    count = 0
    for row in rows:
        c = candidates[row["candidate_id"]]
        title = (c.get("profile", {}).get("current_title", "") or "").lower()
        for flag in RED_FLAG_TITLES:
            if flag in title:
                count += 1
                print(f'  ⚠ Rank {row["rank"]}: "{c["profile"]["current_title"]}"')
                break

    passed = count == 0
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\n  Red-flag titles in top 100: {count} {status}\n")
    return passed


def check_score_distribution(rows: list) -> bool:
    """TEST 4: Analyze score distribution."""
    print("=" * 60)
    print("  TEST 4: Score Distribution")
    print("=" * 60)

    scores = [float(r["score"]) for r in rows]

    print(f"  #1:     {scores[0]:.4f}")
    print(f"  #10:    {scores[9]:.4f}")
    print(f"  #25:    {scores[24]:.4f}")
    print(f"  #50:    {scores[49]:.4f}")
    print(f"  #100:   {scores[99]:.4f}")
    print(f"  Range:  {scores[0] - scores[99]:.4f}")
    print(f"  Avg:    {sum(scores) / len(scores):.4f}")

    monotonic = all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))
    print(f'  Non-increasing: {"✅" if monotonic else "❌"}')

    return monotonic


def spot_check_top_10(rows: list, candidates: dict):
    """TEST 5: Display top 10 for manual review."""
    print(f"\n{'=' * 60}")
    print("  TEST 5: Top 10 Spot-Check")
    print("=" * 60)
    print(f"  {'Rank':>4}  {'Score':>6}  {'Title':<36} {'Company':<14} {'YoE':>5}  {'Location':<16} Skills")
    print(f"  {'─' * 4}  {'─' * 6}  {'─' * 36} {'─' * 14} {'─' * 5}  {'─' * 16} {'─' * 30}")

    for row in rows[:10]:
        c = candidates[row["candidate_id"]]
        p = c.get("profile", {})
        skills = [s["name"] for s in (c.get("skills") or [])[:3]]
        print(
            f"  #{row['rank']:>3}  {row['score']:>6}  "
            f"{p.get('current_title', '?')[:36]:<36} "
            f"{p.get('current_company', '?')[:14]:<14} "
            f"{p.get('years_of_experience', 0):>4.1f}y  "
            f"{p.get('location', '')[:16]:<16} "
            f"{', '.join(skills)}"
        )


def main():
    if len(sys.argv) < 3:
        print("Usage: python tests/run_quality_checks.py <submission.csv> <candidates.jsonl>")
        sys.exit(1)

    submission_path = sys.argv[1]
    candidates_path = sys.argv[2]

    candidates = load_candidates(candidates_path)
    rows = load_submission(submission_path)

    print(f"  Submission: {len(rows)} candidates\n")

    results = []
    results.append(("Honeypot Check", check_honeypots(rows, candidates)))
    results.append(("Keyword Stuffers", check_keyword_stuffers(rows, candidates)))
    results.append(("Red-Flag Titles", check_red_flag_titles(rows, candidates)))
    results.append(("Score Distribution", check_score_distribution(rows)))
    spot_check_top_10(rows, candidates)

    # Summary
    print(f"\n{'=' * 60}")
    print("  SUMMARY")
    print("=" * 60)
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}  {name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("  🏆 All quality checks passed!")
    else:
        print("  ⚠  Some checks failed — review above for details.")
    print()

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
