"""
Stage 2: Extraction.

Reads the raw HTML/PDF files saved by scrape.py and turns each one into a
single markdown file with the real content and heading structure, and
nothing else -- no nav bars, no cookie banners, no footers.

HTML: Trafilatura first (handles most support pages cleanly). Falls back
to a targeted BeautifulSoup pass if Trafilatura returns too little text,
which happens on a handful of oddly-structured pages.

PDF: PyMuPDF for plain-text manuals. pdfplumber for anything that looks
like it contains a table (error-code charts, spec sheets), since it
extracts rows/columns instead of a jumbled string of numbers.

Run: python extract.py
"""

import re
from pathlib import Path

import fitz  # PyMuPDF
import pdfplumber
import trafilatura
from bs4 import BeautifulSoup

from config import RAW_DIR, EXTRACTED_DIR, LOG_DIR
from utils import get_logger, read_jsonl, append_jsonl, already_processed, content_hash, url_hash

logger = get_logger("extract", LOG_DIR)
RAW_MANIFEST = RAW_DIR / "manifest.jsonl"
EXTRACT_MANIFEST = EXTRACTED_DIR / "manifest.jsonl"

# Track content hashes seen this run for deduplication
_seen_hashes: set = set()


def _extract_html(local_path: str, url: str) -> tuple[str, str]:
    """Returns (title, markdown_body)."""
    raw_html = Path(local_path).read_text(encoding="utf-8", errors="ignore")

    markdown_body = trafilatura.extract(
        raw_html, output_format="markdown", include_tables=True, url=url
    )
    if markdown_body and len(markdown_body.split()) > 40:
        title = trafilatura.extract_metadata(raw_html).title if trafilatura.extract_metadata(raw_html) else url
        return title or url, markdown_body

    # Fallback: Trafilatura came back empty/thin, target the main content
    # tag directly instead of giving up on the page.
    logger.info(f"Trafilatura output too thin for {url}, falling back to BeautifulSoup")
    soup = BeautifulSoup(raw_html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else url

    main = soup.find("main") or soup.find("article") or soup.body
    lines = []
    if main:
        for tag in main.find_all(["h1", "h2", "h3", "p", "li", "table"]):
            if tag.name in ("h1", "h2", "h3"):
                level = "#" * int(tag.name[1])
                text = tag.get_text(strip=True)
                if text:
                    lines.append(f"{level} {text}")
            elif tag.name == "table":
                lines.append(_table_to_markdown(tag))
            else:
                text = tag.get_text(strip=True)
                if text:
                    lines.append(text)
    return title, "\n\n".join(lines)


def _table_to_markdown(table_tag) -> str:
    rows = []
    for tr in table_tag.find_all("tr"):
        cells = [c.get_text(strip=True) for c in tr.find_all(["td", "th"])]
        if cells:
            rows.append(cells)
    if not rows:
        return ""
    header, body = rows[0], rows[1:]
    md = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for row in body:
        md.append("| " + " | ".join(row) + " |")
    return "\n".join(md)


def _pdf_has_table(local_path: str) -> bool:
    with pdfplumber.open(local_path) as pdf:
        for page in pdf.pages[:5]:  # a quick look at the first few pages is enough
            if page.extract_tables():
                return True
    return False


def _extract_pdf(local_path: str) -> tuple[str, str]:
    title = Path(local_path).stem
    if _pdf_has_table(local_path):
        logger.info(f"Table detected in {local_path}, using pdfplumber")
        lines = [f"# {title}"]
        with pdfplumber.open(local_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                lines.append(f"## Page {page_num}")
                for table in page.extract_tables():
                    header, body = table[0], table[1:]
                    lines.append("| " + " | ".join(c or "" for c in header) + " |")
                    lines.append("|" + "---|" * len(header))
                    for row in body:
                        lines.append("| " + " | ".join(c or "" for c in row) + " |")
                text = page.extract_text()
                if text:
                    lines.append(text)
        return title, "\n\n".join(lines)
    else:
        logger.info(f"No table detected in {local_path}, using PyMuPDF")
        doc = fitz.open(local_path)
        lines = [f"# {title}"] + [page.get_text() for page in doc]
        return title, "\n\n".join(lines)


def _clean_boilerplate(text: str) -> str:
    """Strip the handful of repeated boilerplate lines that slip through
    extraction on almost every support page."""
    boilerplate_patterns = [
        r"(?i)^was this (article|page) helpful.*$",
        r"(?i)^©\s*\d{4}.*all rights reserved.*$",
        r"(?i)^cookie (settings|policy).*$",
        r"(?i)^skip to (main )?content.*$",
    ]
    lines = text.splitlines()
    kept = []
    for line in lines:
        if any(re.match(p, line.strip()) for p in boilerplate_patterns):
            continue
        kept.append(line)
    cleaned = "\n".join(kept)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)  # collapse extra blank lines
    return cleaned.strip()


def _extract_heading_path(body: str) -> str:
    """Extract the heading hierarchy from markdown body."""
    headings = []
    for line in body.splitlines():
        if line.startswith("#"):
            headings.append(line.lstrip("#").strip())
            if len(headings) >= 3:
                break
    return " > ".join(headings) if headings else ""


def _detect_support_type(record: dict, body: str) -> str:
    """Classify page into a specific support type for retrieval filtering.
    Uses URL path, title, and body content signals."""
    url_lower = record.get("url", "").lower()
    body_lower = body.lower()
    title_lower = (record.get("title") or "").lower()
    combined = f"{url_lower} {title_lower} {body_lower[:1000]}"

    # Order matters: more specific matches first
    if any(k in combined for k in ["error_code", "error code", "flashing_light", "blinking",
                                     "f1", "f2", "f3", "f5", "f7", "e1", "e2"]):
        return "error_code"
    if any(k in combined for k in ["install", "hook up", "hookup", "set up", "setup",
                                     "level the", "connect the"]):
        return "installation"
    if any(k in combined for k in ["troubleshoot", "not working", "won't", "does not",
                                     "will not", "problem", "issue", "diagnos"]):
        return "troubleshooting"
    if any(k in combined for k in ["clean", "maintenance", "care", "descale", "filter",
                                     "affresh", "deodor"]):
        return "maintenance"
    if any(k in combined for k in ["warranty", "service plan", "extended service",
                                     "coverage", "protection"]):
        return "warranty"
    if any(k in combined for k in ["part", "replace", "order", "accessori"]):
        return "parts"
    if any(k in combined for k in ["safety", "hazard", "caution", "warning label", "recall"]):
        return "safety"
    if any(k in combined for k in ["spec", "dimension", "capacity", "weight", "energy",
                                     "ampere", "voltage", "btu"]):
        return "specifications"
    if any(k in combined for k in ["manual", "owner", "literature", "guide", "pdf"]):
        return "manual"
    if record.get("is_pdf"):
        return "manual"
    if any(k in combined for k in ["how to", "usage", "cycle", "setting", "option",
                                     "feature", "operation", "load", "dispenser"]):
        return "usage"
    if "faq" in combined:
        return "faq"
    return "general_support"


def process_record(record: dict):
    url = record["url"]
    if already_processed(EXTRACT_MANIFEST, url):
        return

    local_path = record["local_path"]
    try:
        if record["is_pdf"]:
            title, body = _extract_pdf(local_path)
        else:
            title, body = _extract_html(local_path, url)
        body = _clean_boilerplate(body)

        # Deduplicate by content hash
        body_hash = content_hash(body.encode("utf-8"))
        if body_hash in _seen_hashes:
            logger.info(f"Duplicate content, skipping: {url}")
            append_jsonl(EXTRACT_MANIFEST, {"url": url, "status": "duplicate", "content_hash": body_hash})
            return
        _seen_hashes.add(body_hash)

        doc_id = url_hash(url)
        out_dir = EXTRACTED_DIR / record["brand"] / record["category"]
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / (Path(local_path).stem + ".md")
        out_path.write_text(body, encoding="utf-8")

        append_jsonl(EXTRACT_MANIFEST, {
            "doc_id": doc_id,
            "source_url": url,
            "brand": record["brand"],
            "category": record["category"],
            "extracted_path": str(out_path),
            "title": title,
            "heading_path": _extract_heading_path(body),
            "page_type": _detect_support_type(record, body),
            "has_table": "|---" in body,
            "content_hash": body_hash,
            "crawl_timestamp": record.get("scraped_at", ""),
            "effective_date": None,
            "status": "ok",
        })
        logger.info(f"Extracted {url} -> {out_path}")
    except Exception as e:
        logger.error(f"Extraction failed for {url}: {e}")
        append_jsonl(EXTRACT_MANIFEST, {"url": url, "status": "failed", "error": str(e)})


def main():
    records = [r for r in read_jsonl(RAW_MANIFEST) if r.get("status") == "ok"]
    logger.info(f"Extracting {len(records)} raw files")
    for record in records:
        process_record(record)


if __name__ == "__main__":
    main()
