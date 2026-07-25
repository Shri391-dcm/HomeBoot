"""Chroma-style vector store for BGE embeddings."""

from __future__ import annotations

import chromadb
import json
import math
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from retrieval.embeddings import create_embeddings


class VectorStore:
    """In-memory vector store that mirrors a simple Chroma workflow."""

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension
        self._store: List[Dict[str, Any]] = []

    def add(
        self,
        id: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        text: str = "",
    ) -> None:
        if len(vector) != self.dimension:
            raise ValueError(f"Expected vector dimension {self.dimension}, got {len(vector)}")
        self._store.append(
            {
                "id": id,
                "vector": vector,
                "metadata": metadata or {},
                "text": text,
            }
        )

    def delete(self, id: str) -> None:
        self._store = [item for item in self._store if item["id"] != id]

    def query(
        self,
        vector: List[float],
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        candidates = self._apply_filter(metadata_filter)
        scored = [
            {
                "id": item["id"],
                "score": self._cosine_similarity(vector, item["vector"]),
                "metadata": item["metadata"],
                "text": item["text"],
            }
            for item in candidates
        ]
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_k]

    def search(
        self,
        vector: List[float],
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        return self.query(vector, top_k=top_k, metadata_filter=metadata_filter)

    def _apply_filter(self, metadata_filter: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not metadata_filter:
            return self._store
        return [
            item
            for item in self._store
            if all(item["metadata"].get(key) == value for key, value in metadata_filter.items())
        ]

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        dot = 0.0
        norm_a = 0.0
        norm_b = 0.0
        for x, y in zip(a, b):
            dot += x * y
            norm_a += x * x
            norm_b += y * y
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))

    @classmethod
    def from_json(
        cls,
        path: Path,
        embedder: Callable[[List[str]], List[List[float]]],
        chunk_key: str = "chunk_id",
        text_key: str = "text",
        metadata_keys: Optional[List[str]] = None,
    ) -> "VectorStore":
        metadata_keys = metadata_keys or ["source_url", "title", "heading_path", "page_type"]
        with path.open("r", encoding="utf-8") as fh:
            chunks = json.load(fh)

        texts = [chunk[text_key] for chunk in chunks]
        vectors = embedder(texts)
        store = cls(dimension=len(vectors[0]) if vectors else cls().dimension)

        for chunk, vector in zip(chunks, vectors):
            metadata = {key: chunk.get(key) for key in metadata_keys if key in chunk}
            store.add(
                id=chunk[chunk_key],
                vector=vector,
                metadata=metadata,
                text=chunk[text_key],
            )
        return store


def load_mock_chunks(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


if __name__ == "__main__":
    # Create a local ChromaDB database
    client = chromadb.PersistentClient(path="data/vector_db")

    # Create a collection
    collection = client.get_or_create_collection(name="homeboot_chunks")

    # Temporary mock data
    texts = [
        "If the washing machine is not draining, check the drain hose for kinks or clogs.",
        "If the washing machine will not start, make sure the door is completely closed.",
        "If the washing machine is not filling with water, check that the water supply valves are open.",
    ]

    # Create BGE embeddings
    embeddings = create_embeddings(texts).tolist()

    # Store them in ChromaDB
    collection.upsert(
        ids=["washer_001", "washer_002", "washer_003"],
        documents=texts,
        embeddings=embeddings,
    )

    print("Successfully stored chunks in ChromaDB!")
    print("Number of chunks:", collection.count())
