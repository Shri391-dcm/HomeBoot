"""FastAPI main application - Integrated with real RAG retrieval pipeline."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import logging

from backend.src.generation import generate_answer, extract_citations
from backend.src.refusal import should_refuse
from backend.src.safety import detect_safety_issue

# Import fresh retrieval pipeline
from retrieval.retrieve import retrieve_documents

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="HomeBoot Backend API",
    description="RAG Chatbot for appliance support with real retrieval",
    version="2.0.0",
)

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Initialization: Retrieval pipeline initialized in retrieval/retrieve.py
# ============================================================================
# Fresh retrieval is performed for every user query via retrieve_documents()


# ============================================================================
# Pydantic Models
# ============================================================================

class PassageInput(BaseModel):
    """A single retrieved passage."""
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
    top_k: Optional[int] = 10
    conversation_history: Optional[List[Dict[str, str]]] = None  # List of {"role": "user"|"assistant", "content": "..."}


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


class RetrieveResponse(BaseModel):
    """Response from /retrieve endpoint."""
    query: str
    passages: List[PassageInput]
    total_found: int


class ClarifyResponse(BaseModel):
    """Response from /clarify endpoint."""
    needs_clarification: bool
    message: str
    suggestions: Optional[List[str]] = None


# ============================================================================
# Helper Functions
# ============================================================================

MAX_DIAGNOSTIC_QUESTIONS = 5


def _infer_appliance_category(text: str) -> Optional[str]:
    """Return the appliance category named in a query or conversation."""
    text = text.lower()
    # Check in order of specificity (longer keywords first)
    # IMPORTANT: Check "dishwasher" before "washer" because "washer" is in "dishwasher"
    if any(keyword in text for keyword in ["dishwasher"]):
        return "dishwasher"
    if any(keyword in text for keyword in ["refrigerator", "refrigirator", "fridge", "fidge", "freezer"]):
        return "refrigerator"
    if any(keyword in text for keyword in ["washer", "washing machine"]):
        return "washer"
    return None


def _infer_brand(text: str) -> Optional[str]:
    """Return the supported appliance brand named in a query or conversation."""
    normalized_text = "".join(
        character if character.isalnum() else " " for character in text.lower()
    )
    if "whirlpool" in normalized_text:
        return "whirlpool"
    if any(
        keyword in f" {normalized_text} "
        for keyword in ["ge appliances", "general electric", "ge"]
    ):
        return "ge"
    return None


def _starts_new_appliance_issue(query: str) -> bool:
    """Identify a standalone appliance problem rather than a short follow-up."""
    problem_keywords = [
        "not working",
        "not cooling",
        "not draining",
        "not starting",
        "leaking",
        "broken",
        "problem",
        "issue",
    ]
    query_lower = query.lower()
    return (
        _infer_appliance_category(query) is not None
        and any(keyword in query_lower for keyword in problem_keywords)
    )


def _starts_new_appliance_topic(query: str) -> bool:
    """Identify a full appliance question that must not inherit old context."""
    topic_keywords = [
        "how", "what", "when", "where", "why", "can", "should",
        "move", "install", "clean", "repair", "replace", "prepare",
        "safe", "safely", "maintenance",
    ]
    query_lower = query.lower()
    return (
        _infer_appliance_category(query) is not None
        and len(query.split()) >= 3
        and (
            any(keyword in query_lower for keyword in topic_keywords)
            or _starts_new_appliance_issue(query)
        )
    )


def _changes_appliance_category(query: str, history: Optional[List[Dict[str, str]]]) -> bool:
    """Return whether a new query names a different appliance than its history."""
    query_category = _infer_appliance_category(query)
    history_category = _infer_appliance_category(
        " ".join(message.get("content", "") for message in history or [])
    )
    return query_category is not None and history_category is not None and query_category != history_category


def _needs_brand_clarification(query: str, history: Optional[List[Dict[str, str]]] = None) -> bool:
    """Require a brand before starting a new appliance diagnosis."""
    conversation_text = " ".join(
        message.get("content", "") for message in history or []
    )
    combined_text = f"{query} {conversation_text}"
    return _infer_appliance_category(combined_text) is not None and _infer_brand(combined_text) is None


def _needs_product_specifications(query: str, history: Optional[List[Dict[str, str]]] = None) -> bool:
    """Require product details before a new appliance troubleshooting session."""
    return _starts_new_appliance_topic(query) and not history

def _build_trace(query: str, passages: List[PassageInput]) -> RetrievalTrace:
    """Build retrieval trace from passages."""
    if not passages:
        return RetrievalTrace(
            query=query,
            passage_count=0,
            top_5_scores_before=[],
            top_5_scores_after=[],
            max_score_before=0.0,
            max_score_after=0.0,
        )
    
    pre_scores = sorted(
        [p.pre_rerank_score for p in passages],
        reverse=True
    )[:5]
    
    post_scores = sorted(
        [p.post_rerank_score for p in passages],
        reverse=True
    )[:5]
    
    return RetrievalTrace(
        query=query,
        passage_count=len(passages),
        top_5_scores_before=pre_scores,
        top_5_scores_after=post_scores,
        max_score_before=max([p.pre_rerank_score for p in passages]) if passages else 0.0,
        max_score_after=max([p.post_rerank_score for p in passages]) if passages else 0.0,
    )


def _format_conversation_history(history: Optional[List[Dict[str, str]]]) -> str:
    """Format recent messages so short replies retain their diagnostic meaning."""
    if not history:
        return ""

    recent_messages = history[-6:]
    formatted_messages = []
    for message in recent_messages:
        role = message.get("role", "user").capitalize()
        content = message.get("content", "").strip()
        if content:
            formatted_messages.append(f"{role}: {content}")

    return "\n".join(formatted_messages)


def _is_diagnostic_follow_up(history: Optional[List[Dict[str, str]]]) -> bool:
    """Distinguish an active diagnosis from product-specification intake."""
    return any(message.get("role") == "assistant" for message in history or [])


def _diagnostic_question_count(history: Optional[List[Dict[str, str]]]) -> int:
    """Count prior assistant diagnostic turns in the active conversation."""
    if not history:
        return 0
    return sum(1 for message in history if message.get("role") == "assistant")


def _retrieve_passages(query: str, top_k: int = 10, conversation_history: Optional[List[Dict[str, str]]] = None) -> List[PassageInput]:
    """Call fresh retrieval pipeline for every query, optionally with conversation context."""
    try:
        # Build context-aware query from conversation history
        retrieval_query = query
        if conversation_history and len(conversation_history) > 0:
            # Extract previous context from history (exclude the current query)
            context_parts = []
            for msg in conversation_history[:-1]:  # All but last (which is current query)
                if msg.get("role") == "user":
                    context_parts.append(f"User: {msg.get('content', '')}")
                elif msg.get("role") == "assistant":
                    # Extract first 100 chars of assistant response for context
                    content = msg.get('content', '')
                    if len(content) > 100:
                        content = content[:100] + "..."
                    context_parts.append(f"Assistant: {content}")
            
            if context_parts:
                # Build enhanced query with history context
                context_str = " | ".join(context_parts[-3:])  # Use last 3 messages for context
                retrieval_query = f"{query}. Context: {context_str}"
                logger.info(f"Enhanced query with history: {retrieval_query[:150]}...")
        
        # Fresh retrieval: new query embedding + fresh hybrid search + fresh reranking
        reranked_results = retrieve_documents(
            retrieval_query,
            candidate_k=max(top_k, 100),
            final_k=max(top_k, 100),
        )
        
        if not reranked_results:
            logger.warning(f"No results for query: {query}")
            return []
        
        # ===== SEMANTIC FILTERING =====
        # If query doesn't mention specific components, boost general appliance troubleshooting
        query_lower = query.lower()
        component_keywords = ["ice", "freezer", "dispenser", "water", "filter", "icemaker", "ice maker"]
        query_mentions_component = any(kw in query_lower for kw in component_keywords)
        
        if not query_mentions_component and reranked_results:
            top_text = reranked_results[0].get("text", "").lower()
            component_mentions = ["icemaker", "ice maker", "ice cube", "water dispenser", "water filter"]
            
            if any(comp in top_text for comp in component_mentions):
                # Deprioritize component-specific content
                general_results = [r for r in reranked_results if not any(
                    comp in r.get("text", "").lower() for comp in component_mentions
                )]
                component_results = [r for r in reranked_results if any(
                    comp in r.get("text", "").lower() for comp in component_mentions
                )]
                
                if general_results:
                    reranked_results = general_results + component_results

        conversation_text = " ".join(
            message.get("content", "") for message in conversation_history or []
        )
        appliance_category = _infer_appliance_category(f"{query} {conversation_text}")
        appliance_brand = _infer_brand(f"{query} {conversation_text}")

        if appliance_category:
            category_results = [
                result for result in reranked_results
                if result.get("category", "").lower() == appliance_category
            ]
            if category_results:
                reranked_results = category_results

        if appliance_brand:
            brand_results = [
                result for result in reranked_results
                if appliance_brand in result.get("brand", "").lower()
            ]
            if brand_results:
                reranked_results = brand_results
        
        # Convert to PassageInput objects
        passages = []
        for rank, result in enumerate(reranked_results[:top_k], 1):
            passages.append(PassageInput(
                rank=rank,
                chunk_id=result.get("id", ""),
                text=result.get("text", ""),
                source_url=result.get("url", ""),
                heading_path="",
                page_type="",
                effective_date="",
                pre_rerank_score=0.0,
                post_rerank_score=result.get("rerank_score", 0.0),
            ))
        
        logger.info(f"Retrieved {len(passages)} passages for query: {query}")
        return passages  # Use original query for logging
        
    except Exception as e:
        logger.error(f"Error retrieving passages: {e}")
        return []


# ============================================================================
# Endpoints
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Application startup - retrieval system pre-initialized in retrieval/retrieve.py."""
    logger.info("✅ HomeBoot Backend API started - fresh retrieval ready for every query")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "HomeBoot Backend API",
        "version": "2.0.0",
        "retrieval_available": True,
    }


@app.post("/clarify", response_model=ClarifyResponse)
async def handle_clarify(request: QueryRequest) -> ClarifyResponse:
    """
    Check if query needs clarification on brand/model.
    Returns suggestion to ask user for brand/model if needed.
    """
    if _needs_product_specifications(request.query, request.conversation_history):
        return ClarifyResponse(
            needs_clarification=True,
            message="Which brand is your appliance: Whirlpool or GE Appliances? Please include the appliance type and model number if available.",
            suggestions=["Whirlpool", "GE Appliances"]
        )
    
    return ClarifyResponse(
        needs_clarification=False,
        message="Query is specific enough to answer.",
        suggestions=None
    )


@app.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_passages(request: QueryRequest) -> RetrieveResponse:
    """
    Retrieve passages from real RAG pipeline.
    Returns top-k passages with retrieval scores.
    """
    try:
        logger.info(f"Retrieve request: {request.query}")
        
        passages = _retrieve_passages(request.query, request.top_k)
        
        return RetrieveResponse(
            query=request.query,
            passages=passages,
            total_found=len(passages),
        )
        
    except Exception as e:
        logger.error(f"Retrieve error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=QueryResponse)
async def handle_query(request: QueryRequest) -> QueryResponse:
    """
    Main query endpoint with real retrieval.
    
    Flow:
    1. Retrieve passages from real pipeline
    2. Check for safety-critical question
    3. Check confidence from retrieval scores
    4. Generate answer using Ollama
    5. Extract citations from answer
    6. Return complete response
    """
    try:
        logger.info(f"Query request: {request.query}")

        # A full appliance question begins a separate topic even if an older
        # client accidentally includes messages from a previous conversation.
        conversation_history = request.conversation_history
        if _starts_new_appliance_topic(request.query) and _changes_appliance_category(
            request.query, conversation_history
        ):
            conversation_history = None

        # Require product details before retrieval when an older client bypasses /clarify.
        if _needs_product_specifications(request.query, conversation_history):
            return QueryResponse(
                query=request.query,
                answer="Which brand is your appliance: Whirlpool or GE Appliances? Please include the appliance type and model number if available.",
                citations=[],
                refusal=False,
                safety_flag=False,
                retrieval_trace=_build_trace(request.query, []),
            )

        # Enforce the same brand gate here as a fallback for older frontend clients.
        if _needs_brand_clarification(request.query, conversation_history):
            return QueryResponse(
                query=request.query,
                answer="To provide the most accurate troubleshooting, could you please tell me the brand and model of your appliance?",
                citations=[],
                refusal=False,
                safety_flag=False,
                retrieval_trace=_build_trace(request.query, []),
            )
        
        # Step 1: Retrieve real passages (with optional conversation history)
        passages = _retrieve_passages(request.query, request.top_k, conversation_history)
        
        if not passages:
            logger.warning("No passages retrieved")
            return QueryResponse(
                query=request.query,
                answer="I couldn't find relevant information to answer your question.",
                citations=[],
                refusal=True,
                refusal_reason="No relevant documents found in retrieval",
                safety_flag=False,
                retrieval_trace=_build_trace(request.query, []),
            )
        
        # Step 2: Safety check
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
                retrieval_trace=_build_trace(request.query, passages),
            )
        
        # Step 3: Confidence check (refusal)
        scores = [p.post_rerank_score for p in passages]
        should_refuse_answer, refusal_reason = should_refuse(scores)
        is_follow_up = _is_diagnostic_follow_up(conversation_history)
        
        if should_refuse_answer and not is_follow_up:
            logger.info(f"Refusing answer: {refusal_reason}")
            return QueryResponse(
                query=request.query,
                answer="I don't have reliable information to answer that question. Please contact support.",
                citations=[],
                refusal=True,
                refusal_reason=refusal_reason,
                safety_flag=False,
                retrieval_trace=_build_trace(request.query, passages),
            )
        
        # Step 4: Generate answer
        context = "\n\n".join([p.text for p in passages])
        formatted_history = _format_conversation_history(conversation_history)
        diagnostic_question_count = _diagnostic_question_count(conversation_history)
        generation_question = request.query
        if formatted_history:
            generation_question = (
                "Conversation history:\n"
            f"{formatted_history}\n\n"
                f"Latest user reply: {request.query}\n\n"
                "Respond only to the latest user reply. Do not repeat the conversation history or these instructions. "
            )
            if diagnostic_question_count >= MAX_DIAGNOSTIC_QUESTIONS:
                generation_question += (
                    "You have completed the diagnostic questions. Do not ask another question. "
                    "Give the most likely conclusion and next action supported by the context. "
                    "If the checks do not identify a safe user-fix, recommend scheduling service."
                )
            else:
                generation_question += "Ask exactly one next diagnostic question or give the next safe troubleshooting step."
        answer = generate_answer(generation_question, context)
        
        # Step 5: Extract citations (convert Pydantic models to dicts)
        passages_dicts = [p.dict() for p in passages]
        citations = extract_citations(answer, passages_dicts)
        
        logger.info(f"Generated answer with {len(citations)} citations")
        
        return QueryResponse(
            query=request.query,
            answer=answer,
            citations=citations,
            refusal=False,
            safety_flag=False,
            retrieval_trace=_build_trace(request.query, passages),
        )
        
    except Exception as e:
        logger.error(f"Query error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "HomeBoot Backend API v2.0 with Real Retrieval",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
