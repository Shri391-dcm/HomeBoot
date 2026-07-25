"""Safety detection - Flag safety-critical questions for human referral."""

from typing import Tuple
from src.constants import SAFETY_KEYWORDS, SAFETY_REFERRAL


def detect_safety_issue(question: str) -> Tuple[bool, str, str]:
    """
    Detect if question is safety-critical and needs human referral.
    
    Args:
        question: User question
    
    Returns:
        (is_safety_issue: bool, category: str, referral_message: str)
    """
    question_lower = question.lower()

    for category, keywords in SAFETY_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in question_lower:
                referral = SAFETY_REFERRAL.get(
                    category, "Please contact our support team."
                )
                return True, category, referral

    return False, "", ""


def get_safety_referral_message(category: str) -> str:
    """Get the appropriate referral message for a safety category."""
    return SAFETY_REFERRAL.get(category, "Please contact our support team.")
