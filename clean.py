"""
Stage 3: Clean.

Takes the extracted markdown from extract.py and normalizes it into the
final "normalized" document -- the one file per page that everything
downstream (chunking, re-chunking) reads from. This is the file we save
permanently: if we ever want to try a new chunking strategy, we re-read
these normalized files instead of re-scraping or re-extracting anything.

Run: python clean.py
"""

import re
import unicodedata
from pathlib import Path

from config import EXTRACTED_DIR, NORMALIZED_DIR, LOG_DIR
from utils import get_logger, read_jsonl, append_jsonl, already_processed

logger = get_logger("clean", LOG_DIR)
EXTRACT_MANIFEST = EXTRACTED_DIR / "manifest.jsonl"
NORMALIZED_MANIFEST = NORMALIZED_DIR / "manifest.jsonl"


def _dedupe_paragraphs(text: str) -> str:
    """Trafilatura occasionally emits the same paragraph twice on pages
    with duplicated markup (e.g. a mobile/desktop content toggle). Drop
    exact repeat blocks after their first occurrence; headings and table
    rows are never deduped since short repeated headers are legitimate."""
    blocks = text.split("\n\n")
    seen = set()
    kept = []
    for block in blocks:
        stripped = block.strip()
        is_structural = stripped.startswith("#") or stripped.startswith("|") or len(stripped) < 3
        if not is_structural and stripped in seen:
            continue
        if not is_structural:
            seen.add(stripped)
        kept.append(block)
    return "\n\n".join(kept)


def _normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)          # collapse repeated spaces/tabs
    text = re.sub(r"\n[ \t]+", "\n", text)        # trim leading space on lines
    text = re.sub(r"\n{3,}", "\n\n", text)         # collapse 3+ blank lines to 1
    return text.strip()


def _normalize_punctuation(text: str) -> str:
    # Standardize smart quotes and dashes so downstream matching/citation
    # extraction doesn't have to handle five different dash characters.
    replacements = {
        "\u2018": "'", "\u2019": "'",   # curly single quotes
        "\u201c": '"', "\u201d": '"',   # curly double quotes
        "\u2013": "-", "\u2014": "-",   # en dash, em dash
        "\u2026": "...",                 # ellipsis
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return unicodedata.normalize("NFKC", text)


def _fix_pdf_linebreaks(text: str) -> str:
    """PDF extraction often breaks a sentence mid-line even though it's
    not actually the end of a sentence. If a line doesn't end in
    punctuation and the next line starts lowercase, join them."""
    lines = text.split("\n")
    fixed = []
    for line in lines:
        if (fixed and fixed[-1] and not fixed[-1].rstrip().endswith((".", ":", "!", "?", "|"))
                and line[:1].islower()):
            fixed[-1] = fixed[-1].rstrip() + " " + line.strip()
        else:
            fixed.append(line)
    return "\n".join(fixed)


def build_heading_index(markdown_text: str) -> list[dict]:
    """Walks the markdown and records, for every line, which heading path
    it falls under (e.g. 'Washer Error Code F21 > How to Fix It'). This
    heading path travels with the text into chunk.py as metadata, and is
    exactly what structure-aware chunking splits on."""
    heading_stack = []
    indexed_lines = []
    for line in markdown_text.split("\n"):
        match = re.match(r"^(#{1,6})\s+(.*)", line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            heading_stack = heading_stack[: level - 1] + [title]
        indexed_lines.append({
            "text": line,
            "heading_path": " > ".join(heading_stack) if heading_stack else "Untitled",
        })
    return indexed_lines


def process_record(record: dict):
    url = record.get("url") or record.get("source_url")
    if record.get("status") != "ok" or already_processed(NORMALIZED_MANIFEST, url):
        return

    extracted_path = Path(record["extracted_path"])
    raw_text = extracted_path.read_text(encoding="utf-8")

    text = _normalize_punctuation(raw_text)
    text = _fix_pdf_linebreaks(text)
    text = _normalize_whitespace(text)
    text = _dedupe_paragraphs(text)

    out_dir = NORMALIZED_DIR / record["brand"] / record["category"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / extracted_path.name
    out_path.write_text(text, encoding="utf-8")

    append_jsonl(NORMALIZED_MANIFEST, {
        "url": url, "brand": record["brand"], "category": record["category"],
        "normalized_path": str(out_path), "title": record.get("title", ""),
        "has_table": record.get("has_table", False),
        "page_type": record.get("page_type", "general_support"),
        "status": "ok",
    })
    logger.info(f"Normalized {url} -> {out_path}")


def main():
    records = read_jsonl(EXTRACT_MANIFEST)
    logger.info(f"Cleaning {len(records)} extracted files")
    for record in records:
        process_record(record)


if __name__ == "__main__":
    main()
