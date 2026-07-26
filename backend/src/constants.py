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
CONFIDENCE_THRESHOLD = 0.2  # Lower threshold to allow more answers with context-aware retrieval

# Citation validation
MAX_QUOTE_LENGTH = 25  # Maximum words per quote
MIN_QUOTE_LENGTH = 3  # Minimum words per quote

# Ollama model configuration
OLLAMA_MODEL = "qwen2.5:7b-instruct"
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_TIMEOUT = 30  # seconds

# Grounding prompt template
GROUNDING_PROMPT_TEMPLATE = """You are a helpful appliance support assistant for Whirlpool and GE Appliances. Your goal is to guide users through troubleshooting in a conversational way.

IMPORTANT RULES:
1. Answer ONLY using the provided context below.
2. Guide users through troubleshooting STEP-BY-STEP, not all at once.
3. When instructed to continue diagnosing, ask ONE clarifying or diagnostic question at a time.
4. When instructed to conclude, give the most likely finding and next action instead of another question.
5. Be conversational and friendly, not robotic.
6. Example good response: "Thanks for that info. Next, I need to know: are you using HE detergent?" 
7. Example bad response: "Here are all the things you need to check: water temp, detergent type, load size, cycle selection, etc."
8. Use the provided context to diagnose, but ask questions rather than list everything.
9. Only respond with "I don't have that information" if context has NO relevant info.
10. Do NOT make up information beyond the context.

Context:
{context}

Conversation and latest user reply: {question}

Answer:"""

# Retrieval trace configuration
RETRIEVAL_TRACE_INCLUDE_PASSAGES = True  # Include full passage text in trace
