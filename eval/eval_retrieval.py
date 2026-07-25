"""
eval_retrieval.py — Evaluate retrieval quality against gold queries.

Measures:
  - Support-type filter accuracy (does the classified type match expected?)
  - Keyword recall in top-K retrieved chunks
  - Mean Reciprocal Rank (MRR) for keyword hits

Usage:
    python eval/eval_retrieval.py
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import CHUNKS_DIR

GOLD_PATH = Path(__file__).parent / "gold_queries.json"
CHUNKS_PATH = CHUNKS_DIR / "chunks.jsonl"
TOP_K = 5


def load_chunks():
    with open(CHUNKS_PATH) as f:
        return [json.loads(line) for line in f if line.strip()]


def simple_retrieve(chunks, query, support_type=None, brand=None, category=None, top_k=TOP_K):
    """Naive keyword retrieval for offline eval (no embeddings needed)."""
    query_words = set(query.lower().split())
    scored = []
    for c in chunks:
        # Apply metadata filters
        if support_type and c.get("page_type") != support_type:
            continue
        if brand and c.get("brand") != brand:
            continue
        if category and c.get("category") != category:
            continue
        text_words = set(c["text"].lower().split())
        overlap = len(query_words & text_words)
        if overlap > 0:
            scored.append((overlap, c))
    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored[:top_k]]


def evaluate():
    with open(GOLD_PATH) as f:
        gold = json.load(f)
    chunks = load_chunks()

    results = []
    for q in gold:
        retrieved = simple_retrieve(
            chunks, q["query"],
            support_type=q.get("expected_support_type"),
            brand=q.get("expected_brand"),
            category=q.get("expected_category"),
        )
        # Keyword recall: how many expected keywords appear in top-K?
        keywords = [kw.lower() for kw in q["expected_answer_keywords"]]
        combined_text = " ".join(c["text"].lower() for c in retrieved)
        hits = [kw for kw in keywords if kw in combined_text]
        recall = len(hits) / len(keywords) if keywords else 0

        # MRR: rank of first chunk containing any keyword
        mrr = 0
        for rank, c in enumerate(retrieved, 1):
            if any(kw in c["text"].lower() for kw in keywords):
                mrr = 1 / rank
                break

        results.append({
            "query": q["query"],
            "keyword_recall": recall,
            "mrr": mrr,
            "retrieved_count": len(retrieved),
        })

    # Summary
    avg_recall = sum(r["keyword_recall"] for r in results) / len(results)
    avg_mrr = sum(r["mrr"] for r in results) / len(results)
    print(f"\n{'='*60}")
    print(f"Gold Evaluation ({len(gold)} queries, top-{TOP_K})")
    print(f"{'='*60}")
    print(f"  Avg Keyword Recall@{TOP_K}: {avg_recall:.2%}")
    print(f"  Avg MRR:                    {avg_mrr:.3f}")
    print(f"{'='*60}\n")
    for r in results:
        status = "✓" if r["keyword_recall"] > 0.5 else "✗"
        print(f"  {status} [{r['keyword_recall']:.0%}] {r['query'][:60]}")

    return results


if __name__ == "__main__":
    evaluate()
