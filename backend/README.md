# HomeBoot Backend API

Backend service for the HomeBoot RAG Chatbot project.

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Install & Start Ollama

```bash
# macOS
brew install ollama

# Start Ollama server (keep running in background)
ollama serve &

# Pull Qwen2.5 model
ollama pull qwen2.5:7b-instruct
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env if needed (defaults should work)
```

### 4. Run Backend API

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at `http://localhost:8000`

---

## API Endpoints

### Health Check
```bash
GET http://localhost:8000/health
```

### Query Endpoint
```bash
POST http://localhost:8000/query
Content-Type: application/json

{
  "query": "my washing machine won't drain",
  "retrieved_passages": [
    {
      "rank": 1,
      "chunk_id": "chunk_123",
      "text": "If water won't drain from your washer...",
      "source_url": "https://www.whirlpool.com/...",
      "heading_path": "Troubleshooting > Drainage",
      "page_type": "support_page",
      "effective_date": "2024-07-01",
      "pre_rerank_score": 0.87,
      "post_rerank_score": 0.95
    }
  ]
}
```

Response:
```json
{
  "query": "my washing machine won't drain",
  "answer": "Your washing machine won't drain because the drain pump filter is likely clogged...",
  "citations": [
    {
      "claim": "drain pump filter is likely clogged",
      "quote": "Drain filter clogs are common",
      "source_url": "https://www.whirlpool.com/...",
      "heading_path": "Troubleshooting > Drainage"
    }
  ],
  "refusal": false,
  "refusal_reason": null,
  "safety_flag": false,
  "safety_category": null,
  "safety_message": null,
  "retrieval_trace": {
    "query": "my washing machine won't drain",
    "passage_count": 5,
    "top_5_scores_before": [0.87, 0.82, 0.78, 0.75, 0.71],
    "top_5_scores_after": [0.95, 0.88, 0.84, 0.81, 0.77],
    "max_score_before": 0.87,
    "max_score_after": 0.95
  }
}
```

---

## Module Overview

### `src/constants.py`
- Safety keywords and referral messages
- Confidence thresholds
- Ollama configuration
- Grounding prompt template

### `src/generation.py`
- `generate_answer()` — Call Mistral via Ollama
- `extract_citations()` — Match claims to source passages
- `extract_quote_from_passage()` — Pull relevant quotes
- `validate_citation()` — Verify quote exists in source

### `src/refusal.py`
- `should_refuse()` — Check if top score below threshold
- `should_refuse_by_score_distribution()` — Stricter multi-passage check

### `src/safety.py`
- `detect_safety_issue()` — Flag electrical, gas, recall, warranty questions
- `get_safety_referral_message()` — Get appropriate referral message

### `src/mock_data.py`
- Mock retrieval responses for testing without Sanjana's real output
- `MOCK_RETRIEVAL_RESPONSE_DRAINAGE` — Drainage troubleshooting
- `MOCK_RETRIEVAL_RESPONSE_REPAIR` — Door latch repair
- `MOCK_RETRIEVAL_RESPONSE_LOW_CONFIDENCE` — Low-confidence scenario

### `src/api/main.py`
- FastAPI application with `/health` and `/query` endpoints
- Pydantic models for request/response validation
- Query orchestration logic

---

## Testing with Mock Data

```bash
# Start API
uvicorn src.api.main:app --reload &

# Test drainage query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d @test_drainage.json

# Test repair query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d @test_repair.json
```

Create `test_drainage.json`:
```json
{
  "query": "my washing machine won't drain",
  "retrieved_passages": [
    {
      "rank": 1,
      "chunk_id": "whirlpool_washer_drain_1",
      "text": "If water won't drain from your washer, first check the drain pump filter for clogs. Drain filter clogs are one of the most common causes of drainage issues.",
      "source_url": "https://www.whirlpool.com/en-us/support/washers/drainage",
      "heading_path": "Troubleshooting > Drainage Issues",
      "page_type": "support_page",
      "effective_date": "2024-07-01",
      "pre_rerank_score": 0.87,
      "post_rerank_score": 0.95
    },
    {
      "rank": 2,
      "chunk_id": "whirlpool_washer_hoses_1",
      "text": "Check the inlet hoses for kinks or damage that might restrict water flow. Kinked hoses can prevent proper drainage and water fill.",
      "source_url": "https://www.whirlpool.com/en-us/support/washers/hoses",
      "heading_path": "Maintenance > Inlet Hoses",
      "page_type": "support_page",
      "effective_date": "2024-06-15",
      "pre_rerank_score": 0.82,
      "post_rerank_score": 0.88
    },
    {
      "rank": 3,
      "chunk_id": "ge_washer_drain_1",
      "text": "For GE washers, drainage problems often stem from a blocked drain hose. Remove the drain hose from the back of the machine and check for blockages.",
      "source_url": "https://www.ge.com/appliances/support/washers/drainage",
      "heading_path": "Troubleshooting > Drain Hose",
      "page_type": "support_page",
      "effective_date": "2024-07-05",
      "pre_rerank_score": 0.78,
      "post_rerank_score": 0.84
    },
    {
      "rank": 4,
      "chunk_id": "whirlpool_error_codes_1",
      "text": "Error code F21 indicates a drainage failure. This usually means the drain pump is not working or the filter is blocked.",
      "source_url": "https://www.whirlpool.com/en-us/support/washers/error-codes",
      "heading_path": "Error Codes > F21",
      "page_type": "support_page",
      "effective_date": "2024-07-01",
      "pre_rerank_score": 0.75,
      "post_rerank_score": 0.81
    },
    {
      "rank": 5,
      "chunk_id": "ge_washer_pump_1",
      "text": "If your GE washer still won't drain after checking the filter and hose, the drain pump may be faulty and require replacement.",
      "source_url": "https://www.ge.com/appliances/support/washers/drain-pump",
      "heading_path": "Troubleshooting > Drain Pump",
      "page_type": "support_page",
      "effective_date": "2024-06-20",
      "pre_rerank_score": 0.71,
      "post_rerank_score": 0.77
    }
  ]
}
```

---

## Integration with Sanjana (Saturday)

When Sanjana's retrieval is ready, replace the mock data in requests with real output from their `/retrieve` endpoint.

Expected format remains the same — just populate `retrieved_passages` with real scores.

---

## Project Status

- **Friday**: Backend skeleton + mock data ✓
- **Saturday**: Integrate with Sanjana's real retrieval
- **Sunday**: Run final evaluation + generate report
