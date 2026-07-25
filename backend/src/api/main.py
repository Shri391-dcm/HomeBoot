"""FastAPI main application - Integrated with real RAG retrieval pipeline."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import logging
import os
from pathlib import Path

from backend.src.generation import generate_answer, extract_citations
from backend.src.refusal import should_refuse
from backend.src.safety import detect_safety_issue

# Import real retrieval components
from retrieval import HybridSearch, VectorStore, BM25Search, Reranker, CrossEncoderReranker

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
# Initialization: Setup Retrieval Pipeline
# ============================================================================

# Initialize retrieval system at startup
_retrieval_system = None
_vector_store = None
_bm25_search = None
_reranker = None

def _init_retrieval():
    """Initialize real retrieval pipeline."""
    global _retrieval_system, _vector_store, _bm25_search, _reranker
    
    try:
        # Build paths - go up from backend/src/api/main.py to project root
        project_root = Path(__file__).parent.parent.parent.parent  # /Users/manisha/project/HomeBoot
        data_dir = project_root / "data"
        db_path = project_root / "data" / "vector_db"
        
        # Initialize vector store with ChromaDB
        logger.info("Initializing vector store from ChromaDB...")
        import chromadb
        chroma_client = chromadb.PersistentClient(path=str(db_path))
        chroma_collection = chroma_client.get_collection(name="homeboot_chunks")
        
        # Wrap ChromaDB as dense search
        class ChromaDBSearch:
            def __init__(self, collection):
                self.collection = collection
            
            def search(self, query_vector, top_k=20):
                """Search ChromaDB with query vector."""
                results = self.collection.query(
                    query_embeddings=[query_vector],
                    n_results=top_k,
                    include=["documents", "metadatas", "distances"]
                )
                
                if not results or not results["ids"][0]:
                    return []
                
                # Convert distances to similarity scores (0-1 range)
                # Chroma returns distances, so convert: similarity = 1 / (1 + distance)
                output = []
                for i, chunk_id in enumerate(results["ids"][0]):
                    distance = results["distances"][0][i]
                    similarity = 1.0 / (1.0 + distance)  # Convert distance to similarity
                    output.append({
                        "id": chunk_id,
                        "text": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "score": similarity
                    })
                return output
        
        _vector_store = ChromaDBSearch(chroma_collection)
        
        # Initialize BM25 (sparse search) - load chunks from JSONL
        logger.info("Initializing BM25 search...")
        chunks_file = project_root / "data" / "chunks" / "chunks.jsonl"
        chunks = []
        with open(chunks_file, "r", encoding="utf-8") as f:
            import json
            for line in f:
                chunks.append(json.loads(line))
        _bm25_search = BM25Search(chunks)
        
        # Initialize reranker
        logger.info("Initializing reranker...")
        _reranker = CrossEncoderReranker()
        
        # Create hybrid search
        logger.info("Creating hybrid search...")
        _retrieval_system = HybridSearch(
            dense_search=_vector_store,
            bm25_search=_bm25_search,
            dense_weight=0.6,
            sparse_weight=0.4
        )
        
        logger.info("✅ Retrieval system initialized successfully")
        
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize retrieval: {e}")
        logger.warning("System will run without real retrieval - check embeddings and data paths")
        _retrieval_system = None


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


# ============================================================================
# Helper Functions
# ============================================================================

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


def _retrieve_passages(query: str, top_k: int = 10) -> List[PassageInput]:
    """Call real retrieval pipeline to get passages."""
    if _retrieval_system is None:
        logger.warning("Retrieval system not initialized")
        return []
    
    try:
        # Get query embedding
        from retrieval import create_embedding
        query_vector = create_embedding(query)
        
        # Perform hybrid search
        raw_results = _retrieval_system.search(
            query=query,
            query_vector=query_vector,
            top_k=top_k
        )
        
        # Rerank results (note: candidates first, then query)
        reranked_results = _reranker.rerank(raw_results, query)
        
        # Convert to PassageInput objects
        passages = []
        for rank, result in enumerate(reranked_results[:top_k], 1):
            passages.append(PassageInput(
                rank=rank,
                chunk_id=result.get("chunk_id", ""),
                text=result.get("text", ""),
                source_url=result.get("source_url", ""),
                heading_path=result.get("heading_path", ""),
                page_type=result.get("page_type", ""),
                effective_date=result.get("effective_date", ""),
                pre_rerank_score=result.get("pre_rerank_score", 0.0),
                post_rerank_score=result.get("score", 0.0),
            ))
        
        logger.info(f"Retrieved {len(passages)} passages for query: {query}")
        return passages
        
    except Exception as e:
        logger.error(f"Error retrieving passages: {e}")
        return []


# ============================================================================
# Endpoints
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize retrieval system on startup."""
    _init_retrieval()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "HomeBoot Backend API",
        "version": "2.0.0",
        "retrieval_available": _retrieval_system is not None,
    }


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
        
        # Step 1: Retrieve real passages
        passages = _retrieve_passages(request.query, request.top_k)
        
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
        
        if should_refuse_answer:
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
        answer = generate_answer(request.query, context)
        
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
