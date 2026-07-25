# Appliance Support Assistant — Data Engineering Pipeline

Covers the Data Engineer's part of the project: scrape, extract, clean, chunk.
Each stage is its own script, reads from a manifest so it's safe to re-run,
and never repeats work that already succeeded.

## Setup

```bash
pip install -r requirements.txt
```

## Run order

```bash
python scrape.py     # pulls raw HTML/PDF from Whirlpool + GE into data/raw/
python extract.py    # raw HTML/PDF -> clean markdown into data/extracted/
python clean.py      # normalizes whitespace/punctuation into data/normalized/
python chunk.py      # builds fixed + structure-aware chunks into data/chunks/chunks.jsonl
```

Re-chunk without re-scraping or re-extracting anything:

```bash
python chunk.py --rechunk fixed             # only rebuilds the fixed-size chunks
python chunk.py --rechunk structure_aware   # only rebuilds the heading-based chunks
```

## Why it's laid out this way

- **data/raw/** — untouched HTML/PDF exactly as scraped. If extraction or
  cleaning logic changes later, nothing needs to be re-crawled.
- **data/extracted/** — one markdown file per page, boilerplate stripped,
  headings and tables preserved.
- **data/normalized/** — the canonical text every downstream stage reads
  from. This is the file that matters for re-chunking: chunk.py never
  touches raw or extracted, only this.
- **data/chunks/chunks.jsonl** — the final output, one JSON object per
  chunk, each with a deterministic `chunk_id`, its text, its strategy
  (`fixed` or `structure_aware`), and metadata (`url`, `brand`, `category`,
  `heading_path`, `has_table`).
- **manifest.jsonl files** at each stage record what succeeded, so
  re-running any script skips work that's already done and only picks up
  new or previously failed pages.

## Practices this follows

- robots.txt is checked before any request; if it can't be read, that
  domain is skipped rather than assumed to be crawlable.
- Requests are rate-limited to 1/second per domain.
- Every fetch uses a descriptive `User-Agent` naming the project.
- Every stage is idempotent: safe to stop and re-run without duplicating
  or re-doing work.
- Chunk IDs are deterministic (hash of URL + heading path + index), so
  re-chunking can delete old IDs and insert new ones without orphaning
  anything in the vector store downstream.
