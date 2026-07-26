# ApplianceAI — Retrieval-Augmented Generation for Home Appliance Support

An AI-powered home appliance support assistant using Retrieval-Augmented Generation (RAG). Get accurate, cited answers to questions about Whirlpool and GE appliances directly from official documentation.

## Features

✨ **RAG-Powered Answers** — Combines dense and sparse retrieval for accurate, grounded responses  
📌 **Automatic Citations** — Every answer includes sources with direct links to documentation  
🏠 **Appliance Support** — Covers washers, dryers, dishwashers, and refrigerators  
🔍 **Hybrid Search** — BM25 + dense vector embeddings for comprehensive retrieval  
⚡ **Real-Time Generation** — FastAPI backend with streaming responses  
🛡️ **Safety Checks** — Prevents hallucinations and flags unsafe advice  

## Architecture

```
Frontend (localhost:8080)          Backend API (localhost:8000)
    ├─ index.html                        ├─ FastAPI with Uvicorn
    ├─ script.js                         ├─ /query endpoint
    └─ style.css                         ├─ /clarify endpoint
                                         └─ /retrieve endpoint
                                              ↓
                                    Retrieval Pipeline
                                         ├─ BM25 search
                                         ├─ Dense embeddings (Chroma)
                                         └─ Reranking & hybrid fusion
                                              ↓
                                    LLM Generation
                                         ├─ Answer generation
                                         ├─ Citation extraction
                                         └─ Safety classification
```

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js (optional, for development server)

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Build embeddings (one-time setup)
PYTHONPATH=/Users/manisha/project/HomeBoot:$PYTHONPATH python3 retrieval/build_embeddings.py
```

### Run the Application

**Terminal 1 — Start the backend API:**
```bash
PYTHONPATH=/Users/manisha/project/HomeBoot:$PYTHONPATH python3 -m uvicorn backend.src.api.main:app --port 8000
```

**Terminal 2 — Start the frontend server:**
```bash
cd frontend && python3 -m http.server 8080
```

Then open your browser to `http://localhost:8080`

## Project Structure

### Data Pipeline

Data flows through a multi-stage ETL pipeline with idempotent stages:

```
scrape.py  →  extract.py  →  clean.py  →  chunk.py
   ↓            ↓              ↓            ↓
data/raw/   data/extracted/ data/normalized/ data/chunks/
```

- **`scrape.py`** — Fetch HTML/PDF from Whirlpool and GE websites (respects robots.txt, 1 req/sec)
- **`extract.py`** — Strip boilerplate, preserve headings and tables; save as markdown
- **`clean.py`** — Normalize whitespace, punctuation, and formatting
- **`chunk.py`** — Split into fixed-size and structure-aware chunks with metadata

Each stage maintains a `manifest.jsonl` for idempotent re-runs.

### Backend Structure

```
backend/
├── src/
│   ├── api/
│   │   └── main.py              # FastAPI app & /query, /clarify endpoints
│   ├── generation.py            # LLM generation & citation extraction
│   ├── refusal.py               # Refusal detection
│   ├── safety.py                # Safety classification
│   └── constants.py             # Config & LLM prompts
└── data/
    └── vector_db/               # Chroma SQLite vector store
```

**Key Endpoints:**
- `POST /query` — Submit appliance question (returns answer + citations)
- `POST /clarify` — Clarify brand/model after initial question
- `POST /retrieve` — Retrieve top passages for a query

### Retrieval Pipeline

```
retrieval/
├── bm25_search.py              # Sparse retrieval
├── embeddings.py               # Dense embedding with Chroma
├── hybrid_search.py            # Combine BM25 + dense
├── reranker.py                 # Rerank results
├── retrieve.py                 # Main retrieval orchestrator
├── build_embeddings.py         # One-time embedding build
└── vector_store.py             # Vector DB wrapper
```

### Frontend

```
frontend/
├── index.html                  # Chat UI template
├── script.js                   # Client-side logic (messages, citations)
└── style.css                   # Styling
```

Features:
- Brand clarification modal
- Citation modal (displays quote + source link)
- Message history
- Responsive design

### Evaluation

```
evaluation/
├── golden_queries.json         # 40 test queries with gold answers
├── run_evaluation.py           # Evaluation harness
└── check_golden_set.py         # Validation utilities
```

## Running the Data Pipeline

### Full pipeline (from scratch):

```bash
python scrape.py     # pulls raw HTML/PDF from Whirlpool + GE into data/raw/
python extract.py    # raw HTML/PDF -> clean markdown into data/extracted/
python clean.py      # normalizes whitespace/punctuation into data/normalized/
python chunk.py      # builds fixed + structure-aware chunks into data/chunks/chunks.jsonl
```

### Re-chunk without re-scraping:

```bash
python chunk.py --rechunk fixed             # only fixed-size chunks
python chunk.py --rechunk structure_aware   # only heading-based chunks
```

## Design Principles

- **Idempotent Stages** — Safe to stop and re-run; never duplicates work
- **Manifest-Driven** — Each stage records success; only processes new/failed items
- **Deterministic IDs** — Chunk IDs based on URL + heading + index; safe re-chunking
- **Responsible Crawling** — Respects robots.txt, rate-limits to 1 req/sec, descriptive User-Agent
- **Grounded Generation** — Citations extracted from retrieved passages; minimal hallucination
- **Safety-First** — Detects refusals, flags safety issues, prompts for clarification

## Testing

Run the evaluation suite:

```bash
python evaluation/run_evaluation.py
```

This tests against 40 golden queries (dev/test split) covering:
- Single-hop factual questions
- Multi-hop reasoning
- Comparative questions
- Temporal reasoning
- Unanswerable questions
- Adversarial/ambiguous queries

## Environment Variables

Optional configuration in `.env` or shell:

```bash
CHROMA_DB_PATH=data/vector_db/       # Vector DB location
DATA_DIR=data/                       # Data directory root
CHUNK_SIZE=512                       # Fixed chunk size (tokens)
```

## Dependencies

See `requirements.txt` for full list. Key packages:
- `fastapi`, `uvicorn` — Backend API
- `chromadb` — Vector database
- `sentence-transformers` — Embeddings
- `rank-bm25` — Sparse retrieval
- `pydantic` — Data validation
- `anthropic` — LLM (Claude)
