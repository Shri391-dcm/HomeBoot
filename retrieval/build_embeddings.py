"""Build a clean ChromaDB vector index from the current chunks."""

from __future__ import annotations

import json
import math

import chromadb

from retrieval.embeddings import create_embeddings


CHUNKS_FILE = "data/chunks/chunks.jsonl"
DB_PATH = "data/vector_db"
COLLECTION_NAME = "homeboot_chunks"
EXPECTED_EMBEDDING_DIMENSION = 384


# --------------------------------------------------
# Load current chunks
# --------------------------------------------------

with open(
    CHUNKS_FILE,
    "r",
    encoding="utf-8",
) as file:
    chunks = [
        json.loads(line)
        for line in file
        if line.strip()
    ]

if not chunks:
    raise ValueError(
        "No chunks were found in data/chunks/chunks.jsonl"
    )

print("Chunks loaded:", len(chunks))


# --------------------------------------------------
# Verify deterministic chunk IDs
# --------------------------------------------------

chunk_ids = [
    chunk["chunk_id"]
    for chunk in chunks
]

if len(chunk_ids) != len(set(chunk_ids)):
    raise ValueError(
        "Duplicate chunk IDs were found in chunks.jsonl"
    )


# --------------------------------------------------
# Connect to ChromaDB
# --------------------------------------------------

client = chromadb.PersistentClient(
    path=DB_PATH
)


# --------------------------------------------------
# Delete the old collection
# --------------------------------------------------

existing_collections = client.list_collections()

existing_collection_names = {
    collection.name
    if hasattr(collection, "name")
    else str(collection)
    for collection in existing_collections
}

if COLLECTION_NAME in existing_collection_names:
    print(
        "Deleting old ChromaDB collection:",
        COLLECTION_NAME,
    )

    client.delete_collection(
        name=COLLECTION_NAME
    )
else:
    print(
        "No existing ChromaDB collection found."
    )


# --------------------------------------------------
# Create a clean collection
# --------------------------------------------------

collection = client.create_collection(
    name=COLLECTION_NAME,
    metadata={
        "hnsw:space": "cosine",
    },
)


# --------------------------------------------------
# Prepare embedding text, original text and metadata
# --------------------------------------------------

embedding_texts = []
original_texts = []
metadatas = []

for chunk in chunks:

    title = chunk.get("title") or ""
    heading_path = (
        chunk.get("heading_path") or ""
    )
    category = chunk.get("category") or ""
    page_type = (
        chunk.get("page_type")
        or "general_support"
    )
    original_text = chunk.get("text") or ""

    embedding_text = (
        f"Title: {title}\n"
        f"Appliance: {category}\n"
        f"Page Type: {page_type}\n"
        f"Heading: {heading_path}\n"
        f"Content: {original_text}"
    )

    embedding_texts.append(
        embedding_text
    )

    # Store only the original chunk text for answers
    # and citations.
    original_texts.append(
        original_text
    )

    metadatas.append(
        {
            "strategy": (
                chunk.get("strategy")
                or ""
            ),
            "heading_path": heading_path,
            "url": (
                chunk.get("url")
                or ""
            ),
            "brand": (
                chunk.get("brand")
                or ""
            ),
            "category": category,
            "title": title,
            "page_type": page_type,
            "has_table": str(
                bool(
                    chunk.get(
                        "has_table",
                        False,
                    )
                )
            ),
        }
    )


# --------------------------------------------------
# Generate embeddings
# --------------------------------------------------

print("Creating embeddings...")

embeddings = create_embeddings(
    embedding_texts
).tolist()

print("Embedding complete!")


# --------------------------------------------------
# Validate embeddings
# --------------------------------------------------

if len(embeddings) != len(chunks):
    raise ValueError(
        "Embedding count does not match chunk count. "
        f"Chunks={len(chunks)}, "
        f"Embeddings={len(embeddings)}"
    )

if not embeddings:
    raise ValueError(
        "No embeddings were generated."
    )

embedding_dimension = len(
    embeddings[0]
)

if (
    embedding_dimension
    != EXPECTED_EMBEDDING_DIMENSION
):
    raise ValueError(
        "Unexpected embedding dimension. "
        f"Expected={EXPECTED_EMBEDDING_DIMENSION}, "
        f"Actual={embedding_dimension}"
    )

sample_vector_norm = math.sqrt(
    sum(
        value * value
        for value in embeddings[0]
    )
)

if not 0.99 <= sample_vector_norm <= 1.01:
    raise ValueError(
        "The embeddings are not normalized. "
        f"Sample norm={sample_vector_norm}"
    )


# --------------------------------------------------
# Store vectors and metadata
# --------------------------------------------------

collection.add(
    ids=chunk_ids,
    documents=original_texts,
    embeddings=embeddings,
    metadatas=metadatas,
)


# --------------------------------------------------
# Verify the vector index
# --------------------------------------------------

chunk_count = len(chunks)
vector_count = collection.count()

print()
print("Embedding build complete!")
print(
    "Chunks in JSONL:",
    chunk_count,
)
print(
    "Vectors in ChromaDB:",
    vector_count,
)
print(
    "Embedding dimension:",
    embedding_dimension,
)
print(
    "Sample vector norm:",
    round(
        sample_vector_norm,
        4,
    ),
)

if vector_count != chunk_count:
    raise ValueError(
        "Vector count does not match chunk count. "
        f"JSONL={chunk_count}, "
        f"ChromaDB={vector_count}"
    )

print(
    "Verification passed: "
    "every current chunk has one vector."
)