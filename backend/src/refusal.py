"""Refusal detection - Determine when to refuse to answer."""

from typing import List, Tuple
from backend.src.constants import CONFIDENCE_THRESHOLD


def should_refuse(
    retrieval_scores: List[float],
    threshold: float = CONFIDENCE_THRESHOLD,
) -> Tuple[bool, str]:
    """
    Determine if we should refuse to answer based on retrieval confidence.
    
    Args:
        retrieval_scores: List of retrieval scores (0.0 to 1.0) from reranker
        threshold: Confidence threshold below which we refuse
    
    Returns:
        (should_refuse: bool, reason: str)
    """
    if not retrieval_scores:
        return True, "No passages retrieved"

    max_score = max(retrieval_scores)

    if max_score < threshold:
        return (
            True,
            f"Low confidence: best score {max_score:.2f} below threshold {threshold}",
        )

    return False, ""


def should_refuse_by_score_distribution(
    retrieval_scores: List[float], min_passages_for_answer: int = 2
) -> Tuple[bool, str]:
    """
    Stricter refusal: require both high top score AND multiple good passages.
    
    Args:
        retrieval_scores: List of retrieval scores
        min_passages_for_answer: Minimum number of passages > 0.5 needed
    
    Returns:
        (should_refuse: bool, reason: str)
    """
    if not retrieval_scores:
        return True, "No passages retrieved"

    high_confidence_passages = sum(1 for s in retrieval_scores if s > 0.5)

    if high_confidence_passages < min_passages_for_answer:
        return (
            True,
            f"Only {high_confidence_passages} high-confidence passages, need {min_passages_for_answer}",
        )

    return False, ""
