"""
Small helpers shared by scrape.py, extract.py, clean.py, and chunk.py.
Kept in one place so every stage hashes URLs and logs the same way.
"""

import hashlib
import json
import logging
from pathlib import Path


def url_hash(url: str) -> str:
    """Short, stable filename-safe hash for a URL. Same URL -> same hash,
    every time, which is what makes re-running any stage idempotent."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def content_hash(data: bytes) -> str:
    """SHA-256 hash of raw content bytes, used to verify integrity and
    detect duplicates regardless of URL."""
    return hashlib.sha256(data).hexdigest()


def chunk_id(url: str, heading_path: str, index: int) -> str:
    """Deterministic chunk ID: same document + same heading + same position
    always produces the same ID. This is what makes re-chunking safe --
    old IDs can be deleted by exact match before new ones are inserted."""
    raw = f"{url}|{heading_path}|{index}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def get_logger(name: str, log_dir: Path) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:  # avoid duplicate handlers on re-import
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    file_handler = logging.FileHandler(log_dir / f"{name}.log")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    return logger


def read_jsonl(path: Path):
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def append_jsonl(path: Path, record: dict):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def already_processed(manifest_path: Path, key: str, key_field: str = "url") -> bool:
    """Check a manifest before doing work, so re-running a stage never
    repeats a scrape/extract/clean step that already succeeded."""
    for record in read_jsonl(manifest_path):
        if record.get(key_field) == key and record.get("status") == "ok":
            return True
    return False
