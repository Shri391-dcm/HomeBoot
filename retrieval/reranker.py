"""Cross-encoder reranking for retrieved document candidates."""

from __future__ import annotations

from typing import Any

from sentence_transformers import CrossEncoder


DEFAULT_RERANKER_MODEL = "BAAI/bge-reranker-base"


class Reranker:
    """Base interface for reranking retrieved documents."""

    def rerank(
        self,
        candidates: list[dict[str, Any]],
        query: str,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError(
            "Subclasses must implement rerank()."
        )


class CrossEncoderReranker(Reranker):
    """Rerank retrieval candidates using a local cross-encoder."""

    def __init__(
        self,
        model_name: str = DEFAULT_RERANKER_MODEL,
    ) -> None:
        self.model_name = model_name

        self.model = CrossEncoder(
            model_name
        )

    def rerank(
        self,
        candidates: list[dict[str, Any]],
        query: str,
    ) -> list[dict[str, Any]]:
        """Rerank hybrid candidates for one user query."""

        if not candidates:
            return []

        query = query.strip()

        if not query:
            raise ValueError(
                "Query cannot be empty."
            )

        pairs = [
            (
                query,
                candidate.get("text", ""),
            )
            for candidate in candidates
        ]

        scores = self.model.predict(
            pairs
        )

        reranked = []

        for candidate, score in zip(
            candidates,
            scores,
        ):
            item = dict(candidate)

            # Preserve the score created by hybrid search.
            item["hybrid_score"] = float(
                candidate.get(
                    "hybrid_score",
                    candidate.get("score", 0.0),
                )
            )

            # Score created by the cross-encoder.
            item["rerank_score"] = float(
                score
            )

            # Final score used to order chatbot results.
            item["final_score"] = float(
                score
            )

            reranked.append(item)

        reranked.sort(
            key=lambda item: item["final_score"],
            reverse=True,
        )

        for rank, item in enumerate(
            reranked,
            start=1,
        ):
            item["rank_after_rerank"] = rank

        return reranked