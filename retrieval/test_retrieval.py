```python
"""Unit tests for the retrieval package."""

import json
from pathlib import Path

from retrieval import BM25Search, MockEmbeddings, MockReranker, VectorStore


def load_mock_chunks(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def test_bm25_and_vector_retrieval(tmp_path):
    chunks = [
        {
            "id": "c1",
            "text": "Admissions deadlines for the fall semester.",
            "metadata": {
                "source_url": "https://example.edu/admissions"
            },
        },
        {
            "id": "c2",
            "text": "Tuition rates and financial aid eligibility.",
            "metadata": {
                "source_url": "https://example.edu/aid"
            },
        },
        {
            "id": "c3",
            "text": "Campus housing options and move-in dates.",
            "metadata": {
                "source_url": "https://example.edu/housing"
            },
        },
    ]

    # Test BM25 retrieval
    bm25 = BM25Search(chunks)

    results = bm25.search(
        "financial aid deadlines",
        top_k=2,
    )

    assert len(results) == 2
    assert results[0]["id"] == "c2"

    # Test vector retrieval
    store = VectorStore()

    embeddings = MockEmbeddings().embed_texts(
        [chunk["text"] for chunk in chunks]
    )

    for chunk, vector in zip(chunks, embeddings):
        store.add(
            chunk["id"],
            vector,
            metadata=chunk["metadata"],
            text=chunk["text"],
        )

    query_vec = MockEmbeddings().embed_texts(
        ["financial aid deadline"]
    )[0]

    vector_results = store.query(
        query_vec,
        top_k=2,
    )

    assert len(vector_results) == 2
    assert vector_results[0]["id"] in {"c1", "c2"}


def test_mock_reranker_boosts_overlap():
    candidates = [
        {
            "id": "c1",
            "score": 0.1,
            "text": "Admissions deadlines for the fall semester.",
        },
        {
            "id": "c2",
            "score": 0.05,
            "text": "Tuition rates and financial aid eligibility.",
        },
    ]

    reranker = MockReranker()

    ranked = reranker.rerank(
        candidates,
        "financial aid deadline",
    )

    assert ranked[0]["id"] == "c2"


def test_load_mock_chunks_file(tmp_path):
    path = tmp_path / "mock_chunks.json"

    data = [
        {
            "id": "c1",
            "text": "Test chunk",
            "metadata": {
                "source_url": "https://example.com"
            },
        }
    ]

    path.write_text(
        json.dumps(data),
        encoding="utf-8",
    )

    loaded = load_mock_chunks(path)

    assert loaded == data
```
