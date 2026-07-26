import json

from retrieval.bm25_search import BM25Search


# Load real chunks created from chunking pipeline
with open(
    "data/chunks/chunks.jsonl",
    "r",
    encoding="utf-8"
) as f:
    chunks = [json.loads(line) for line in f]


# Build BM25 index
bm25 = BM25Search(chunks)


query = "My washing machine is not draining"


# BM25 keyword retrieval
# No metadata filter here because chunks store
# category/title/url at the root level, not inside metadata.
results = bm25.search(
    query,
    top_k=5
)


print("\nQuery:")
print(query)

print("\nBM25 Results:\n")


for i, result in enumerate(results):
    print("Rank:", i + 1)
    print("Score:", round(result["score"], 4))

    # Real chunk fields
    print("Chunk ID:", result.get("id"))

    # Metadata fields are stored directly in chunks.jsonl
    print("Title:", result.get("title"))
    print("Category:", result.get("category"))
    print("Brand:", result.get("brand"))
    print("URL:", result.get("url"))

    print("Text:", result["text"][:300])
    print("-" * 70)