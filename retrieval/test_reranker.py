import chromadb
import json

from retrieval.embeddings import create_embedding
from retrieval.bm25_search import BM25Search
from retrieval.hybrid_search import HybridSearch
from retrieval.reranker import CrossEncoderReranker


# Load chunks for BM25
with open(
    "data/chunks/chunks.jsonl",
    "r",
    encoding="utf-8"
) as f:
    chunks = [json.loads(line) for line in f]


bm25 = BM25Search(chunks)


# ChromaDB dense search
client = chromadb.PersistentClient(
    path="data/vector_db"
)

collection = client.get_collection(
    name="homeboot_chunks"
)


class DenseSearch:

    def search(self, query_vector, top_k=20):

        results = collection.query(
            query_embeddings=[query_vector],
            n_results=top_k
        )

        output = []

        for i in range(len(results["ids"][0])):

            metadata = results["metadatas"][0][i]

            output.append(
                {
                    "id": results["ids"][0][i],
                    "score": 1 - results["distances"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": metadata,
                    "title": metadata.get("title"),
                    "category": metadata.get("category"),
                    "brand": metadata.get("brand"),
                    "url": metadata.get("url"),
                }
            )

        return output


dense = DenseSearch()


# Hybrid retrieval
hybrid = HybridSearch(
    dense_search=dense,
    bm25_search=bm25
)


query = "My washing machine is not draining"

query_embedding = create_embedding(query).tolist()


# Get candidates
candidates = hybrid.search(
    query=query,
    query_vector=query_embedding,
    top_k=20
)


print("\nHybrid Results Before Reranking:\n")

for i, item in enumerate(candidates[:5]):
    print("Rank:", i + 1)
    print("Title:", item.get("title"))
    print("Category:", item.get("category"))
    print("Score:", round(item["score"], 4))
    print("-" * 70)


# Rerank candidates
reranker = CrossEncoderReranker()

reranked = reranker.rerank(
    candidates,
    query
)


print("\nFinal Reranked Results:\n")

for i, item in enumerate(reranked[:5]):

    print("Rank:", i + 1)
    print("Rerank Score:", round(item["rerank_score"], 4))
    print("Title:", item.get("title"))
    print("Category:", item.get("category"))
    print("Brand:", item.get("brand"))
    print("URL:", item.get("url"))
    print("Text:", item["text"][:300])
    print("-" * 70)
