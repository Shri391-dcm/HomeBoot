"""Configuration constants for generation, safety, and refusal logic."""

# Safety keywords that trigger human referral instead of generated answer
SAFETY_KEYWORDS = {
    "electrical": [
        "shock",
        "electrocution",
        "live wire",
        "electrical hazard",
        "electric shock",
        "exposed wire",
    ],
    "gas": ["gas", "propane", "natural gas", "leak", "gas leak", "carbon monoxide"],
    "recall": [
        "recall",
        "dangerous",
        "safety issue",
        "hazard",
        "fire risk",
        "burn risk",
        "fire",
        "smoke",
        "burning",
        "flames",
        "smell smoke",
    ],
    "warranty": ["warranty void", "authorized service", "authorized repair"],
}

# Safety referral contacts (domain-specific)
SAFETY_REFERRAL = {
    "electrical": "Please contact a qualified electrician or our support team.",
    "gas": "Please contact a qualified technician or our support team immediately.",
    "recall": "Please contact our support team immediately for safety concerns.",
    "warranty": "Please contact our authorized service center to avoid voiding your warranty.",
}

# Refusal threshold: if top retrieval score < this, refuse to answer
CONFIDENCE_THRESHOLD = 0.3

# Citation validation
MAX_QUOTE_LENGTH = 25  # Maximum words per quote
MIN_QUOTE_LENGTH = 3  # Minimum words per quote

# Ollama model configuration
OLLAMA_MODEL = "qwen2.5:7b-instruct"
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_TIMEOUT = 30  # seconds

# Grounding prompt template
GROUNDING_PROMPT_TEMPLATE = """You are a helpful appliance support assistant for Whirlpool and GE Appliances.

IMPORTANT RULES:
1. Answer ONLY using the provided context below.
2. If the context doesn't contain enough information to answer the question, respond with exactly: "I don't have that information."
3. Do NOT make up or guess information.
4. Be concise and practical.

Context:
{context}

Question: {question}

Answer:"""

# Retrieval trace configuration
RETRIEVAL_TRACE_INCLUDE_PASSAGES = True  # Include full passage text in trace
