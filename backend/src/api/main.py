"""FastAPI main application - Query handler and response builder."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import logging

from src.generation import generate_answer, extract_citations
from src.refusal import should_refuse
from src.safety import detect_safety_issue

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="HomeBoot Backend API",
    description="RAG Chatbot for appliance support",
    version="1.0.0",
)

# Add CORS middleware for frontend integration later
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Pydantic Models
# ============================================================================


class PassageInput(BaseModel):
    """A single retrieved passage from Sanjana's retrieval."""

    rank: int
    chunk_id: str
    text: str
    source_url: str
    heading_path: Optional[str] = ""
    page_type: Optional[str] = ""
    effective_date: Optional[str] = ""
    pre_rerank_score: float
    post_rerank_score: float


class QueryRequest(BaseModel):
    """Request body for /query endpoint."""

    query: str
    retrieved_passages: List[PassageInput]


class Citation(BaseModel):
    """Citation for a claim in the answer."""

    claim: str
    quote: str
    source_url: str
    heading_path: Optional[str] = ""


class RetrievalTrace(BaseModel):
    """Trace of retrieval and reranking scores."""

    query: str
    passage_count: int
    top_5_scores_before: List[float]
    top_5_scores_after: List[float]
    max_score_before: float
    max_score_after: float


class QueryResponse(BaseModel):
    """Response body for /query endpoint."""

    query: str
    answer: str
    citations: List[Citation]
    refusal: bool
    refusal_reason: Optional[str] = None
    safety_flag: bool
    safety_category: Optional[str] = None
    safety_message: Optional[str] = None
    retrieval_trace: RetrievalTrace


# ============================================================================
# Endpoints
# ============================================================================


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "HomeBoot Backend API",
        "version": "1.0.0",
    }


@app.post("/query", response_model=QueryResponse)
async def handle_query(request: QueryRequest) -> QueryResponse:
    """
    Main query endpoint.
    
    Flow:
    1. Check for safety-critical question → referral if yes
    2. Check confidence from retrieval scores → refusal if too low
    3. Generate answer using Mistral
    4. Extract citations from answer
    5. Return complete response
    """
    try:
        logger.info(f"Received query: {request.query}")

        # Step 1: Safety check
        is_safety_issue, safety_category, safety_message = detect_safety_issue(
            request.query
        )
        if is_safety_issue:
            logger.warning(f"Safety issue detected: {safety_category}")
            return QueryResponse(
                query=request.query,
                answer=safety_message,
                citations=[],
                refusal=False,
                safety_flag=True,
                safety_category=safety_category,
                safety_message=safety_message,
                retrieval_trace=_build_trace(request),
            )

        # Step 2: Confidence check (refusal)
        scores = [p.post_rerank_score for p in request.retrieved_passages]
        should_refuse_answer, refusal_reason = should_refuse(scores)

        if should_refuse_answer:
            logger.info(f"Refusing answer: {refusal_reason}")
            return QueryResponse(
                query=request.query,
                answer="I don't have that information.",
                citations=[],
                refusal=True,
                refusal_reason=refusal_reason,
                safety_flag=False,
                retrieval_trace=_build_trace(request),
            )

        # Step 3: Generate answer
        context = _build_context(request.retrieved_passages)
        answer = generate_answer(request.query, context)

        logger.info(f"Generated answer: {answer[:100]}...")

        # Step 4: Extract citations
        passages_dict = [
            {
                "text": p.text,
                "source_url": p.source_url,
                "heading_path": p.heading_path,
            }
            for p in request.retrieved_passages
        ]
        citations_raw = extract_citations(answer, passages_dict, request.query)

        # Convert to Pydantic models
        citations = [Citation(**c) for c in citations_raw]

        logger.info(f"Extracted {len(citations)} citations")

        # Step 5: Return response
        return QueryResponse(
            query=request.query,
            answer=answer,
            citations=citations,
            refusal=False,
            safety_flag=False,
            retrieval_trace=_build_trace(request),
        )

    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


# ============================================================================
# Helper Functions
# ============================================================================


def _build_context(passages: List[PassageInput]) -> str:
    """Join passages into a single context string."""
    context_parts = []
    for passage in passages:
        header = f"[Source: {passage.source_url}]\n[{passage.heading_path}]"
        context_parts.append(f"{header}\n{passage.text}")

    return "\n\n".join(context_parts)


def _build_trace(request: QueryRequest) -> RetrievalTrace:
    """Build retrieval trace from request."""
    scores_before = [p.pre_rerank_score for p in request.retrieved_passages]
    scores_after = [p.post_rerank_score for p in request.retrieved_passages]

    return RetrievalTrace(
        query=request.query,
        passage_count=len(request.retrieved_passages),
        top_5_scores_before=scores_before,
        top_5_scores_after=scores_after,
        max_score_before=max(scores_before) if scores_before else 0.0,
        max_score_after=max(scores_after) if scores_after else 0.0,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
