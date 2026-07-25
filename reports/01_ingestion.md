# 01 — Ingestion Report

## Corpus

**Domain:** Home appliance troubleshooting and support  
**Brands:** Whirlpool, GE Appliances  
**Categories:** Washer, Refrigerator, Dishwasher  

## Stage 1: Scrape

### Configuration

| Parameter | Value |
| --- | --- |
| User-Agent | `MSAI633-ApplianceSupportBot/1.0 (contact: mkolluru48935@ucumberlands.edu)` |
| Rate limit | 1.0 sec/request per domain |
| Timeout | 30 seconds |
| Max pages per category | 60 |
| robots.txt | Parsed and honored in code (fail-closed on error) |

### Sources

| Brand | Category | Seed URL | Pages |
| --- | --- | --- | --- |
| Whirlpool | Washer | producthelp.whirlpool.com/Laundry/Washers | 55 |
| Whirlpool | Refrigerator | producthelp.whirlpool.com/Refrigeration | 54 |
| Whirlpool | Dishwasher | producthelp.whirlpool.com/Dishwashers | 56 |
| GE | Washer | geappliances.com/ge/service-and-support/washers-dryers.htm + 4 PDFs | 60 |
| GE | Refrigerator | geappliances.com/ge/service-and-support/refrigerators-freezers.htm + 1 PDF | 52 |
| GE | Dishwasher | geappliances.com + products.geappliances.com | 18 |

### Results

| Metric | Value |
| --- | --- |
| Total pages scraped | 300 |
| HTML pages | 295 |
| PDF documents | 5 |
| Pages with data tables | 4 (5 tables total) |
| Failed URLs | 38 |

### Manifest Fields

Each record in `data/raw/manifest.jsonl` contains:
- `url` — source URL
- `brand`, `category` — classification
- `local_path` — path to raw file on disk
- `is_pdf` — boolean
- `content_hash` — SHA-256 of raw bytes (integrity/dedup)
- `scraped_at` — ISO 8601 UTC timestamp
- `status` — "ok" or "failed"

## Stage 2: Extraction

### Method

- **HTML:** Trafilatura (markdown output with tables) → BeautifulSoup fallback for thin results
- **PDF with tables:** pdfplumber (preserves row/column structure)
- **PDF without tables:** PyMuPDF (fast plain-text extraction)
- **Boilerplate removal:** Regex patterns strip "Was this helpful?", copyright lines, cookie banners
- **Deduplication:** SHA-256 content hash — identical extracted text from different URLs is stored once

### Results

| Metric | Value |
| --- | --- |
| Unique documents extracted | 193 |
| Duplicates removed | 107 |
| Extraction failures | 0 |
| Pages with tables preserved | 6 |
| PDFs extracted | 5 |

### Page Type Classification

| Type | Count |
| --- | --- |
| support_article | 350 |
| troubleshooting | 14 |
| pdf_manual | 10 |
| faq | 8 |
| table_page | 4 |

### Metadata per Document

| Field | Description |
| --- | --- |
| `doc_id` | Deterministic hash of URL |
| `source_url` | Original page URL |
| `title` | Page title |
| `heading_path` | Top heading hierarchy |
| `page_type` | Classification for metadata filtering |
| `has_table` | Boolean — markdown table present |
| `content_hash` | SHA-256 of extracted text |
| `crawl_timestamp` | When the page was scraped |
| `effective_date` | null (not discoverable on these sites) |

## Stage 3: Normalization

### Transformations Applied

1. **Punctuation normalization** — smart quotes → straight quotes, em/en dashes → hyphens, ellipsis → "..."
2. **PDF line-break repair** — mid-sentence breaks rejoined when next line starts lowercase
3. **Whitespace normalization** — collapse tabs/spaces, trim leading whitespace, max 1 blank line
4. **Paragraph deduplication** — exact-repeat paragraphs (from mobile/desktop markup duplication) removed

### Output

193 normalized markdown files in `data/normalized/{brand}/{category}/`.
These are the permanent saved files — all downstream chunking reads from here without re-crawling.

## Reproduction

```bash
# Full pipeline:
python scrape.py      # Stage 1: ~5 min (rate-limited)
python extract.py     # Stage 2: ~2 min
python clean.py       # Stage 3: <1 sec
python chunk.py       # Stage 4: <1 sec
```

## Exclusions

- No login-walled pages (all URLs are publicly accessible)
- No staff, patient, player, or customer directory pages
- No PII/PHI — appliance support content only
- Pages blocked by robots.txt are skipped (fail-closed policy)
