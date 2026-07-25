"""Hybrid retrieval combining dense and sparse signals."""

from __future__ import annotations

from typing import Any, Dict, List


class HybridSearch:

    def __init__(
        self,
        dense_search: Any,
        bm25_search: Any,
        dense_weight: float = 0.6,
        sparse_weight: float = 0.4,
    ):
        self.dense_search = dense_search
        self.bm25_search = bm25_search
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight


    def normalize(self, scores: Dict[str, float]) -> Dict[str, float]:

        if not scores:
            return {}

        max_score = max(scores.values())

        if max_score == 0:
            return {key: 0 for key in scores}

        return {
            key: value / max_score
            for key, value in scores.items()
        }


    def search(
        self,
        query: str,
        query_vector: List[float],
        top_k: int = 20,
    ) -> List[Dict[str, Any]]:


        dense_results = self.dense_search.search(
            query_vector,
            top_k=top_k
        )

        sparse_results = self.bm25_search.search(
            query,
            top_k=top_k
        )


        dense_scores = {
            item["id"]: item.get("score", 0.0)
            for item in dense_results
        }

        bm25_scores = {
            item["id"]: item.get("score", 0.0)
            for item in sparse_results
        }


        dense_scores = self.normalize(dense_scores)
        bm25_scores = self.normalize(bm25_scores)


        fused = {}


        # Dense results
        for item in dense_results:

            fused[item["id"]] = {
                "id": item["id"],
                "score": (
                    dense_scores[item["id"]]
                    * self.dense_weight
                ),
                "dense_score": dense_scores[item["id"]],
                "bm25_score": 0.0,
                "text": item["text"],
                "metadata": item.get("metadata", {}),
                "title": item.get("title"),
                "category": item.get("category"),
                "brand": item.get("brand"),
                "url": item.get("url"),
            }


        # BM25 results
        for item in sparse_results:

            if item["id"] in fused:

                fused[item["id"]]["score"] += (
                    bm25_scores[item["id"]]
                    * self.sparse_weight
                )

                fused[item["id"]]["bm25_score"] = (
                    bm25_scores[item["id"]]
                )

            else:

                fused[item["id"]] = {
                    "id": item["id"],
                    "score": (
                        bm25_scores[item["id"]]
                        * self.sparse_weight
                    ),
                    "dense_score": 0.0,
                    "bm25_score": bm25_scores[item["id"]],
                    "text": item["text"],
                    "metadata": item.get("metadata", {}),
                    "title": item.get("title"),
                    "category": item.get("category"),
                    "brand": item.get("brand"),
                    "url": item.get("url"),
                }


        ranked = sorted(
            fused.values(),
            key=lambda x: x["score"],
            reverse=True
        )


        return ranked[:top_k]