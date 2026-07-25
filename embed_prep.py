"""
embed_prep.py — Prepares chunks for embedding by prepending metadata context.

This is called before sending chunks to the embedding model. It does NOT
modify chunks.jsonl; it produces an augmented version for the vector DB.

Usage:
    from embed_prep import prepare_for_embedding
    enriched = prepare_for_embedding(chunks)
"""

import json
from pathlib import Path
from config import CHUNKS_DIR


def prepend_metadata(chunk: dict) -> str:
    """Prepend structured metadata to chunk text for richer embeddings."""
    parts = []
    if chunk.get("brand"):
        parts.append(f"Brand: {chunk['brand'].title()}")
    if chunk.get("category"):
        parts.append(f"Appliance: {chunk['category'].title()}")
    if chunk.get("page_type"):
        parts.append(f"Support Type: {chunk['page_type'].replace('_', ' ').title()}")
    if chunk.get("heading_path"):
        parts.append(f"Section: {chunk['heading_path']}")

    prefix = " | ".join(parts)
    return f"{prefix}\n\n{chunk['text']}" if prefix else chunk["text"]


def prepare_for_embedding(chunks: list[dict]) -> list[dict]:
    """Returns chunks with an 'embed_text' field for the embedding model."""
    return [{**c, "embed_text": prepend_metadata(c)} for c in chunks]


if __name__ == "__main__":
    chunks_path = CHUNKS_DIR / "chunks.jsonl"
    with open(chunks_path) as f:
        chunks = [json.loads(line) for line in f if line.strip()]

    enriched = prepare_for_embedding(chunks)
    out_path = CHUNKS_DIR / "chunks_embed_ready.jsonl"
    with open(out_path, "w") as f:
        for c in enriched:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"Wrote {len(enriched)} embedding-ready chunks -> {out_path}")
