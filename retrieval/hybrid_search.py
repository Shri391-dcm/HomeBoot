"""Hybrid retrieval combining dense and sparse signals."""

from __future__ import annotations

from typing import Any


class HybridSearch:
    """Combine dense retrieval and BM25 using weighted score fusion."""

    def __init__(
        self,
        dense_search: Any,
        bm25_search: Any,
        dense_weight: float = 0.6,
        sparse_weight: float = 0.4,
    ) -> None:
        self.dense_search = dense_search
        self.bm25_search = bm25_search
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight

    @staticmethod
    def normalize(
        scores: dict[str, float],
    ) -> dict[str, float]:
        """Normalize scores so the largest score becomes 1.0."""

        if not scores:
            return {}

        max_score = max(scores.values())

        if max_score <= 0:
            return {
                key: 0.0
                for key in scores
            }

        return {
            key: value / max_score
            for key, value in scores.items()
        }

    def search(
        self,
        query: str,
        query_vector: list[float],
        top_k: int = 20,
    ) -> list[dict[str, Any]]:
        """Return the top hybrid retrieval candidates."""

        if not query.strip():
            raise ValueError(
                "Query cannot be empty."
            )

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        # Dense semantic retrieval
        dense_results = self.dense_search.search(
            query_vector,
            top_k=top_k,
        )

        # BM25 keyword retrieval
        sparse_results = self.bm25_search.search(
            query,
            top_k=top_k,
        )

        # Raw score maps
        dense_scores = {
            item["id"]: float(
                item.get("score", 0.0)
            )
            for item in dense_results
        }

        bm25_scores = {
            item["id"]: float(
                item.get("score", 0.0)
            )
            for item in sparse_results
        }

        # Normalize both score types before combining.
        normalized_dense_scores = self.normalize(
            dense_scores
        )

        normalized_bm25_scores = self.normalize(
            bm25_scores
        )

        fused: dict[str, dict[str, Any]] = {}

        # ------------------------------------------
        # Add dense results
        # ------------------------------------------

        for item in dense_results:
            item_id = item["id"]

            dense_score = normalized_dense_scores.get(
                item_id,
                0.0,
            )

            fused[item_id] = {
                "id": item_id,
                "score": (
                    dense_score
                    * self.dense_weight
                ),
                "dense_score": dense_score,
                "bm25_score": 0.0,
                "text": item.get("text", ""),
                "metadata": item.get(
                    "metadata",
                    {},
                ),
                "title": item.get(
                    "title",
                    "",
                ),
                "category": item.get(
                    "category",
                    "",
                ),
                "brand": item.get(
                    "brand",
                    "",
                ),
                "url": item.get(
                    "url",
                    "",
                ),
                "page_type": item.get(
                    "page_type",
                    item.get(
                        "metadata",
                        {},
                    ).get(
                        "page_type",
                        "",
                    ),
                ),
            }

        # ------------------------------------------
        # Add BM25 results
        # ------------------------------------------

        for item in sparse_results:
            item_id = item["id"]

            bm25_score = normalized_bm25_scores.get(
                item_id,
                0.0,
            )

            weighted_bm25_score = (
                bm25_score
                * self.sparse_weight
            )

            if item_id in fused:
                fused[item_id]["score"] += (
                    weighted_bm25_score
                )

                fused[item_id]["bm25_score"] = (
                    bm25_score
                )

            else:
                fused[item_id] = {
                    "id": item_id,
                    "score": weighted_bm25_score,
                    "dense_score": 0.0,
                    "bm25_score": bm25_score,
                    "text": item.get(
                        "text",
                        "",
                    ),
                    "metadata": item.get(
                        "metadata",
                        {},
                    ),
                    "title": item.get(
                        "title",
                        "",
                    ),
                    "category": item.get(
                        "category",
                        "",
                    ),
                    "brand": item.get(
                        "brand",
                        "",
                    ),
                    "url": item.get(
                        "url",
                        "",
                    ),
                    "page_type": item.get(
                        "page_type",
                        item.get(
                            "metadata",
                            {},
                        ).get(
                            "page_type",
                            "",
                        ),
                    ),
                }

        # ------------------------------------------
        # Rank the fused results
        # ------------------------------------------

        ranked = sorted(
            fused.values(),
            key=lambda item: item["score"],
            reverse=True,
        )

        ranked = ranked[:top_k]

        # Keep the hybrid score and rank clearly named.
        for rank, item in enumerate(
            ranked,
            start=1,
        ):
            item["hybrid_score"] = float(
                item.get("score", 0.0)
            )

            item["rank_before_rerank"] = rank

        return ranked 