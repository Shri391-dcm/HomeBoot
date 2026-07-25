"""Cross-encoder reranking of retrieval candidates."""

from __future__ import annotations

from typing import Any, Dict, List

from sentence_transformers import CrossEncoder


MODEL_NAME = "BAAI/bge-reranker-base"


class Reranker:
    """
    Base reranker interface.
    """

    def rerank(
        self,
        candidates: List[Dict[str, Any]],
        query: str,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError


class CrossEncoderReranker(Reranker):
    """
    Uses a cross encoder model to score query-document relevance.
    """

    def __init__(
        self,
        model_name: str = MODEL_NAME,
    ):
        self.model = CrossEncoder(model_name)


    def rerank(
        self,
        candidates: List[Dict[str, Any]],
        query: str,
    ) -> List[Dict[str, Any]]:


        pairs = [
            (
                query,
                candidate.get("text", "")
            )
            for candidate in candidates
        ]


        scores = self.model.predict(pairs)


        reranked = []

        for candidate, score in zip(candidates, scores):

            item = dict(candidate)

            item["rerank_score"] = float(score)

            reranked.append(item)


        reranked.sort(
            key=lambda x: x["rerank_score"],
            reverse=True
        )


        return reranked