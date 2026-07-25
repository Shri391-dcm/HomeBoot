"""Sparse retrieval using BM25 ranking."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from rank_bm25 import BM25Okapi


def _tokenize(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())


class BM25Search:
    """BM25 sparse retriever over a small corpus."""

    def __init__(self, documents: List[Dict[str, Any]]) -> None:
        self.documents = documents
        self.documents = [dict(doc, text=str(doc.get("text", ""))) for doc in self.documents]
        self.corpus = [_tokenize(doc["text"]) for doc in self.documents]
        self.bm25 = BM25Okapi(self.corpus)

    def search(self, query: str, top_k: int = 5, metadata_filter: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        query_tokens = _tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        ranked = sorted(
            enumerate(scores), key=lambda item: item[1], reverse=True
        )
        results = []
        for idx, score in ranked:
            if len(results) >= top_k:
                break
            candidate = self.documents[idx]
            if metadata_filter and not all(
                candidate.get("metadata", {}).get(key) == value for key, value in metadata_filter.items()
            ):
                continue
            results.append(
                {
                    "id": candidate.get("chunk_id", candidate.get("id")),
                    "score": float(score),
                    "metadata": candidate.get("metadata", {}),
                    "text": candidate.get("text", ""),
                    "title": candidate.get("title"),
                    "category": candidate.get("category"),
                    "brand": candidate.get("brand"),
                    "url": candidate.get("url"),
                }
            )
        return results
