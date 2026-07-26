"""Generation module - Call Mistral and extract citations."""

import re
import requests
from typing import List, Dict, Tuple
from backend.src.constants import (
    GROUNDING_PROMPT_TEMPLATE,
    OLLAMA_MODEL,
    OLLAMA_API_URL,
    OLLAMA_TIMEOUT,
    MAX_QUOTE_LENGTH,
    MIN_QUOTE_LENGTH,
)


def generate_answer(question: str, context: str) -> str:
    """
    Call Mistral (via Ollama) with grounding prompt.
    
    Args:
        question: User query
        context: Retrieved passages joined together
    
    Returns:
        Generated answer from Mistral
    """
    prompt = GROUNDING_PROMPT_TEMPLATE.format(context=context, question=question)

    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=OLLAMA_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()["response"].strip()
    except requests.exceptions.ConnectionError:
        return "[ERROR] Could not connect to Ollama. Is it running? (ollama serve)"
    except requests.exceptions.Timeout:
        return "[ERROR] Ollama response timed out. Try again."
    except Exception as e:
        return f"[ERROR] Generation failed: {str(e)}"


def extract_citations(
    answer: str, passages: List[Dict], question: str = ""
) -> List[Dict]:
    """
    Extract citations from generated answer by matching sentences to source passages.
    
    Args:
        answer: Generated answer text
        passages: List of retrieved passages with 'text' and 'source_url' keys
        question: Original question (for context)
    
    Returns:
        List of citations: [{"claim": "...", "quote": "...", "source_url": "..."}]
    """
    citations = []

    # Split answer into sentences
    sentences = re.split(r"(?<=[.!?])\s+", answer)

    # Build searchable passage texts
    passage_map = {}  # text -> source_url
    for p in passages:
        if "text" in p:
            passage_map[p["text"]] = {
                "source_url": p.get("source_url", ""),
                "heading_path": p.get("heading_path", ""),
            }

    # For each sentence, try to find a matching passage and extract quote
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence or len(sentence.split()) < 3:
            continue

        # Find best matching passage for this sentence
        best_match = None
        best_score = 0

        for passage_text, metadata in passage_map.items():
            # Simple similarity: count overlapping words
            answer_words = set(sentence.lower().split())
            passage_words = set(passage_text.lower().split())
            overlap = len(answer_words & passage_words)

            score = overlap / (len(answer_words) + 1)  # avoid division by zero
            if score > best_score and score > 0.3:  # threshold
                best_score = score
                best_match = (sentence, passage_text, metadata)

        if best_match:
            claim, passage_text, metadata = best_match

            # Extract a quote from the passage (up to MAX_QUOTE_LENGTH words)
            quote = extract_quote_from_passage(passage_text, claim)

            if quote:
                citations.append(
                    {
                        "claim": claim,
                        "quote": quote,
                        "source_url": metadata["source_url"],
                        "heading_path": metadata.get("heading_path", ""),
                    }
                )

    return citations


def extract_quote_from_passage(passage: str, claim: str) -> str:
    """
    Extract a relevant quote from passage that supports the claim.
    
    Args:
        passage: Full passage text
        claim: Claim to be supported
    
    Returns:
        Quote string (max MAX_QUOTE_LENGTH words)
    """
    MAX_QUOTE_LENGTH = 50
    
    # Strategy 1: Try to find the exact claim in passage
    if claim.lower() in passage.lower():
        idx = passage.lower().find(claim.lower())
        end_idx = idx + len(claim)
        return passage[idx:end_idx]
    
    # Strategy 2: Try to find significant words from the claim in the passage
    claim_words = [w for w in claim.lower().split() if len(w) > 3]  # Filter out small words
    if not claim_words:
        claim_words = claim.lower().split()
    
    # Find the passage position where most claim words appear
    passage_lower = passage.lower()
    best_pos = -1
    best_count = 0
    
    for i in range(len(passage_lower)):
        count = 0
        for word in claim_words[:5]:  # Check first 5 claim words
            if word in passage_lower[i:i+200]:  # Look ahead 200 chars
                count += 1
        if count > best_count:
            best_count = count
            best_pos = i
    
    # If we found relevant words, extract a quote around that position
    if best_pos != -1 and best_count >= 1:
        # Extract words around the best position
        start_idx = max(0, best_pos)
        end_idx = min(len(passage), best_pos + 300)
        quote = passage[start_idx:end_idx]
        
        # Trim to word boundaries
        words = quote.split()[:MAX_QUOTE_LENGTH]
        return ' '.join(words)
    
    # Strategy 3: If still nothing, return first MAX_QUOTE_LENGTH words of passage
    words = passage.split()[:MAX_QUOTE_LENGTH]
    return ' '.join(words) if words else ""


def validate_citation(citation: Dict, original_passage: str) -> bool:
    """
    Validate that quote actually exists in original passage.
    
    Args:
        citation: Citation dict with 'quote' key
        original_passage: Full source passage text
    
    Returns:
        True if quote is valid, False otherwise
    """
    quote = citation.get("quote", "").lower()
    passage = original_passage.lower()

    return quote in passage if quote else False
