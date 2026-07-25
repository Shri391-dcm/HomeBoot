"""Reusable retrieval pipeline for chatbot questions."""

from __future__ import annotations

import json
from typing import Any

import chromadb

from retrieval.bm25_search import BM25Search
from retrieval.embeddings import create_embedding
from retrieval.hybrid_search import HybridSearch
from retrieval.reranker import CrossEncoderReranker


CHUNKS_PATH = "data/chunks/chunks.jsonl"
CHROMA_PATH = "data/vector_db"
COLLECTION_NAME = "homeboot_chunks"


# Load chunks once for BM25.
with open(CHUNKS_PATH, "r", encoding="utf-8") as file:
    chunks = [
        json.loads(line)
        for line in file
        if line.strip()
    ]


# Connect to the existing ChromaDB index.
client = chromadb.PersistentClient(path=CHROMA_PATH)

collection = client.get_collection(
    name=COLLECTION_NAME
)


class DenseSearch:
    """Search document embeddings stored in ChromaDB."""

    def search(
        self,
        query_vector: list[float],
        top_k: int = 20,
    ) -> list[dict[str, Any]]:
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
        )

        output = []

        for index in range(len(results["ids"][0])):
            metadata = (
                results["metadatas"][0][index]
                or {}
            )

            output.append(
                {
                    "id": results["ids"][0][index],
                    "score": (
                        1
                        - results["distances"][0][index]
                    ),
                    "text": results["documents"][0][index],
                    "metadata": metadata,
                    "title": metadata.get("title", ""),
                    "category": metadata.get("category", ""),
                    "brand": metadata.get("brand", ""),
                    "url": metadata.get("url", ""),
                }
            )

        return output


# Load these models once when the application starts.
dense_search = DenseSearch()
bm25_search = BM25Search(chunks)

hybrid_search = HybridSearch(
    dense_search=dense_search,
    bm25_search=bm25_search,
)

reranker = CrossEncoderReranker()


def retrieve_documents(
    query: str,
    candidate_k: int = 20,
    final_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Run fresh retrieval for one user question.

    Document embeddings remain stored in ChromaDB.
    Only the user's query embedding is newly created.
    """

    query = query.strip()

    if not query:
        raise ValueError("The query cannot be empty.")

    # Fresh query embedding for every question.
    query_vector = create_embedding(query).tolist()

    # Fresh dense + BM25 hybrid search.
    candidate_pool = hybrid_search.search(
        query=query,
        query_vector=query_vector,
        top_k=candidate_k,
    )

    # Fresh reranking for this question.
    reranked_results = reranker.rerank(
        candidates=candidate_pool,
        query=query,
    )

    return reranked_results[:final_k]