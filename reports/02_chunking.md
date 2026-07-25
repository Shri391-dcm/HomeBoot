# 02 — Chunking Report

## Overview

We implemented two chunking strategies as required, both reading from the
normalized markdown files produced by `clean.py`. Re-chunking never
re-crawls or re-extracts — it only re-reads `data/normalized/`.

## Strategies

### 1. Fixed-Size Chunking

- **Target size:** 400 tokens (~300 words)
- **Overlap:** 60 tokens (~45 words)
- **Method:** Sliding window over whitespace-split words. Each chunk
  overlaps with the previous one so that sentences split at a boundary
  still appear in at least one chunk in full.
- **Heading path:** Not carried (set to `null`) — this strategy is
  position-based, not structure-based.

### 2. Structure-Aware Chunking

- **Split points:** Markdown headings (`#`, `##`, `###`, etc.)
- **Method:** The `build_heading_index()` function walks the normalized
  markdown and assigns every line to its current heading path (e.g.
  `"Leaking - Dishwasher > Water on the Floor"`). Each heading section
  becomes one chunk.
- **Heading path:** Carried as metadata on every chunk — enables
  retrieval to show users exactly where an answer came from in the
  original document hierarchy.

## Chunk Counts

| Strategy | Chunk Count |
|---|---|
| Fixed | 314 |
| Structure-aware | 967 |
| **Total** | **1,281** |

## Token-Length Distributions

| Strategy | Mean | Median | Std Dev | Min | Max |
|---|---|---|---|---|---|
| Fixed | 278 | 329 | 128 | 35 | 400 |
| Structure-aware | 83 | 52 | 118 | 3 | 1,152 |

### Percentiles

| Strategy | p10 | p25 | p50 | p75 | p90 |
|---|---|---|---|---|---|
| Fixed | 95 | 136 | 329 | 400 | 400 |
| Structure-aware | 4 | 8 | 52 | 96 | 205 |

## Observations

1. **Fixed chunks cluster at the 400-token cap.** The median (329) is
   slightly below 400 because the final chunk of each document is often
   shorter. The p75 and p90 both hit exactly 400, confirming the window
   logic works correctly.

2. **Structure-aware chunks have high variance.** Some heading sections
   are just a one-line label (min = 3 tokens), while others contain an
   entire troubleshooting guide (max = 1,152 tokens). The median of 52
   tokens reflects that many Whirlpool support pages use deep heading
   hierarchies with short sections.

3. **Structure-aware produces 3× more chunks** because each heading
   boundary creates a new chunk regardless of length. This gives finer
   retrieval granularity but may hurt embedding quality on very short
   chunks.

4. **Trade-off:** Fixed chunks guarantee a minimum context window for
   the embedding model. Structure-aware chunks guarantee semantic
   coherence (no mid-paragraph splits) and carry heading metadata for
   better citations.

## Deterministic Chunk IDs

Every chunk ID is a SHA-256 hash of `(url, heading_path_or_"fixed", index)`.
This means:
- Re-running `chunk.py` produces identical IDs for unchanged content
- The vector database can upsert by ID without creating duplicates
- Re-chunking with `--rechunk fixed` deletes only fixed-strategy chunks
  and replaces them, leaving structure-aware chunks untouched

## Reproduction

```bash
# Run the full pipeline from normalized text to chunks:
python chunk.py

# Re-chunk only one strategy (no re-crawling):
python chunk.py --rechunk fixed
python chunk.py --rechunk structure_aware
```

## Token Estimation

We use `words / 0.75` as an approximate token count (configurable in
`config.py` as `WORDS_PER_TOKEN = 0.75`). This is a standard English
approximation. A real tokenizer (e.g. `tiktoken` for OpenAI models)
can be swapped in later without changing any upstream code.
