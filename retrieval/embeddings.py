"""Embeddings utilities for document and query encoding."""

from typing import List

from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-small-en-v1.5"

model = SentenceTransformer(MODEL_NAME)


def create_embeddings(texts: List[str]):
    return model.encode(
        texts,
        normalize_embeddings=True
    )


def create_embedding(text: str):
    return model.encode(
        text,
        normalize_embeddings=True
    )


if __name__ == "__main__":
    question = "My washing machine is not draining."

    embedding = create_embedding(question)

    print("Model:", MODEL_NAME)
    print("Embedding dimension:", len(embedding))
    print("First 5 values:", embedding[:5])
