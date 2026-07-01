import sys
import csv
import json
import math

def dcg(relevances):
    return sum((2**rel - 1) / math.log2(idx + 2) for idx, rel in enumerate(relevances))

def calculate_ndcg(relevances, k):
    actual = relevances[:k]
    ideal = sorted(relevances, reverse=True)[:k]
    actual_dcg = dcg(actual)
    ideal_dcg = dcg(ideal)
    return actual_dcg / ideal_dcg if ideal_dcg > 0 else 0.0

def calculate_map(relevances):
    # For MAP, we treat relevance >= 2 as relevant (1) and < 2 as not relevant (0)
    binary_rels = [1 if r >= 2 else 0 for r in relevances]
    if sum(binary_rels) == 0:
        return 0.0
    
    precisions = []
    hits = 0
    for i, is_rel in enumerate(binary_rels):
        if is_rel:
            hits += 1
            precisions.append(hits / (i + 1))
            
    return sum(precisions) / sum(binary_rels)

def calculate_p_at_k(relevances, k, threshold=3):
    # Fraction of top-k that are tier `threshold` or higher
    top_k = relevances[:k]
    hits = sum(1 for r in top_k if r >= threshold)
    return hits / k

def heuristic_grade(c):
    skills = [s.get("name", "").lower().strip() for s in c.get("skills", [])]
    summary = c.get("profile", {}).get("summary", "").lower()
    
    # Keyword sets
    retrieval = {"faiss", "qdrant", "pinecone", "weaviate", "milvus", "elasticsearch", "opensearch", "vector search"}
    embeddings = {"sentence transformers", "sentence-transformers", "bge", "embeddings", "embedding"}
    ranking = {"recommendation systems", "learning to rank", "xgboost", "lightgbm", "ranking", "ndcg", "mrr"}
    
    r_count = len(set(skills) & retrieval)
    e_count = len(set(skills) & embeddings)
    rk_count = len(set(skills) & ranking)
    
    yoe = c.get("profile", {}).get("years_of_experience", 0)
    
    # Grading logic
    core_sum = r_count + e_count + rk_count
    
    if core_sum >= 4 and yoe >= 5.0:
        return 3
    elif core_sum >= 2 and yoe >= 4.0:
        return 2
    elif core_sum >= 1:
        return 1
    else:
        return 0

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 evaluator.py <submission.csv> <candidates.jsonl>")
        sys.exit(1)
        
    sub_path = sys.argv[1]
    cand_path = sys.argv[2]
    
    # Load top 50 CIDs
    top_50_cids = []
    with open(sub_path, "r") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 50:
                break
            top_50_cids.append(row["candidate_id"])
            
    # Stream JSONL to find those 50
    candidates = {}
    with open(cand_path, "r") as f:
        for line in f:
            if not line.strip(): continue
            c = json.loads(line)
            if c["candidate_id"] in top_50_cids:
                candidates[c["candidate_id"]] = c
                if len(candidates) == 50:
                    break
                    
    # Grade them in order
    relevances = []
    for cid in top_50_cids:
        c = candidates.get(cid, {})
        relevances.append(heuristic_grade(c))
        
    ndcg_10 = calculate_ndcg(relevances, 10)
    ndcg_50 = calculate_ndcg(relevances, 50)
    map_score = calculate_map(relevances)
    p_10 = calculate_p_at_k(relevances, 10, threshold=3)
    
    print("\n--- FINAL EVALUATION METRICS ---")
    print(f"NDCG@10:  {ndcg_10:.4f}  (Quality of top-10 picks)")
    print(f"NDCG@50:  {ndcg_50:.4f}  (Quality of top-50 picks)")
    print(f"MAP:      {map_score:.4f}  (Mean Avg Precision, relevance >= 2)")
    print(f"P@10:     {p_10:.4f}  (Fraction of top-10 that are tier 3+)")
    print("--------------------------------\n")
    print(f"Top 10 Relevances: {relevances[:10]}")

if __name__ == "__main__":
    main()
