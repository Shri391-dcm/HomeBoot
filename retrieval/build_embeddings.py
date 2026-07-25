import json
import chromadb

from retrieval.embeddings import create_embeddings


CHUNKS_FILE = "data/chunks/chunks.jsonl"
DB_PATH = "data/vector_db"
COLLECTION_NAME = "homeboot_chunks"


# Load chunk data
with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
    chunks = [json.loads(line) for line in f]

print("Chunks loaded:", len(chunks))


# Create ChromaDB persistent store
client = chromadb.PersistentClient(path=DB_PATH)

collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}
)


# Extract text for embedding
texts = [chunk["text"] for chunk in chunks]


# Generate BGE embeddings
print("Creating embeddings...")
embeddings = create_embeddings(texts).tolist()


# Store vectors + metadata
collection.upsert(
    ids=[chunk["chunk_id"] for chunk in chunks],
    documents=texts,
    embeddings=embeddings,
    metadatas=[
        {
            "strategy": chunk["strategy"],
            "heading_path": chunk["heading_path"] or "",
            "url": chunk["url"],
            "brand": chunk["brand"],
            "category": chunk["category"],
            "title": chunk["title"],
            "has_table": str(chunk["has_table"]),
        }
        for chunk in chunks
    ],
)


print("Embedding complete!")
print("Chunks in ChromaDB:", collection.count())
print("Embedding dimension:", len(embeddings[0]))

