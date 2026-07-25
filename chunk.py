"""
Stage 4: Chunk.

Reads the normalized markdown files from clean.py and splits each one
into retrievable chunks, using two strategies required by the project:

  1. Fixed chunking      -- ~400 tokens per chunk, 60-token overlap.
  2. Structure-aware      -- split at heading boundaries, heading path
                             carried forward as metadata on every chunk.

Every chunk gets a deterministic ID (hash of URL + heading path + index),
so re-running this file with a different chunk size or strategy is safe:
old chunk IDs for that strategy are deleted before the new ones are
written, and nothing here ever touches the raw scrape or the normalized
text -- re-chunking never requires re-crawling.

Run:
    python chunk.py                       # build both strategies
    python chunk.py --rechunk fixed       # rebuild only the fixed strategy
"""

import argparse
import json
from pathlib import Path

from config import NORMALIZED_DIR, CHUNKS_DIR, LOG_DIR, FIXED_CHUNK_TOKENS, FIXED_CHUNK_OVERLAP, WORDS_PER_TOKEN
from clean import build_heading_index
from utils import chunk_id, get_logger, read_jsonl

logger = get_logger("chunk", LOG_DIR)
NORMALIZED_MANIFEST = NORMALIZED_DIR / "manifest.jsonl"
CHUNKS_PATH = CHUNKS_DIR / "chunks.jsonl"

WORDS_PER_CHUNK = int(FIXED_CHUNK_TOKENS * WORDS_PER_TOKEN)
OVERLAP_WORDS = int(FIXED_CHUNK_OVERLAP * WORDS_PER_TOKEN)


def fixed_chunks(text: str, url: str, meta: dict) -> list[dict]:
    words = text.split()
    chunks = []
    start = 0
    index = 0
    while start < len(words):
        end = min(start + WORDS_PER_CHUNK, len(words))
        chunk_text = " ".join(words[start:end])
        chunks.append({
            "chunk_id": chunk_id(url, "fixed", index),
            "text": chunk_text,
            "strategy": "fixed",
            "heading_path": None,
            **meta,
        })
        index += 1
        if end == len(words):
            break
        start = end - OVERLAP_WORDS  # step forward but re-include the overlap window
    return chunks


def structure_aware_chunks(text: str, url: str, meta: dict) -> list[dict]:
    indexed_lines = build_heading_index(text)
    sections = {}
    order = []
    for item in indexed_lines:
        path = item["heading_path"]
        if path not in sections:
            sections[path] = []
            order.append(path)
        if item["text"].strip():
            sections[path].append(item["text"])

    chunks = []
    for index, path in enumerate(order):
        section_text = "\n".join(sections[path]).strip()
        if not section_text:
            continue
        chunks.append({
            "chunk_id": chunk_id(url, path, index),
            "text": section_text,
            "strategy": "structure_aware",
            "heading_path": path,
            **meta,
        })
    return chunks


def _load_existing_chunks() -> list[dict]:
    if not CHUNKS_PATH.exists():
        return []
    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _write_chunks(chunks: list[dict]):
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")


def build(strategy_filter: str | None = None):
    """Builds chunks for every normalized document. If strategy_filter is
    set (e.g. 'fixed'), only that strategy is rebuilt -- existing chunks
    for the other strategy are kept untouched, and existing chunks for the
    targeted strategy are dropped before the new ones are written, so no
    orphaned chunk IDs are left behind in chunks.jsonl."""
    records = [r for r in read_jsonl(NORMALIZED_MANIFEST) if r.get("status") == "ok"]
    logger.info(f"Chunking {len(records)} normalized documents (strategy filter: {strategy_filter or 'all'})")

    existing = _load_existing_chunks()
    kept = [c for c in existing if strategy_filter and c["strategy"] != strategy_filter] if strategy_filter else []

    new_chunks = []
    for record in records:
        text = Path(record["normalized_path"]).read_text(encoding="utf-8")
        url = record["url"]
        meta = {
            "url": url, "brand": record["brand"], "category": record["category"],
            "title": record.get("title", ""), "has_table": record.get("has_table", False),
        }
        if strategy_filter in (None, "fixed"):
            new_chunks.extend(fixed_chunks(text, url, meta))
        if strategy_filter in (None, "structure_aware"):
            new_chunks.extend(structure_aware_chunks(text, url, meta))

    all_chunks = kept + new_chunks
    _write_chunks(all_chunks)

    # Orphan check: every chunk ID in the file should trace back to a URL
    # that's still in the normalized manifest. If a page was ever removed
    # upstream, its chunks would show up here and should be dropped.
    valid_urls = {r["url"] for r in records}
    orphans = [c for c in all_chunks if c["url"] not in valid_urls]
    if orphans:
        logger.warning(f"{len(orphans)} orphaned chunks found, removing")
        all_chunks = [c for c in all_chunks if c["url"] in valid_urls]
        _write_chunks(all_chunks)

    logger.info(f"Wrote {len(all_chunks)} total chunks -> {CHUNKS_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rechunk", choices=["fixed", "structure_aware"], default=None,
                         help="Rebuild only this strategy, e.g. after changing chunk size")
    args = parser.parse_args()
    build(strategy_filter=args.rechunk)
