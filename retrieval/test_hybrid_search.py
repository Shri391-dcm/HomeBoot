import json
import chromadb

from retrieval.embeddings import create_embedding
from retrieval.bm25_search import BM25Search
from retrieval.hybrid_search import HybridSearch


# Load chunks for BM25
with open(
    "data/chunks/chunks.jsonl",
    "r",
    encoding="utf-8"
) as f:
    chunks = [json.loads(line) for line in f]


bm25 = BM25Search(chunks)


# ChromaDB
client = chromadb.PersistentClient(
    path="data/vector_db"
)

collection = client.get_collection(
    name="homeboot_chunks"
)


class DenseSearch:

    def search(self, query_vector, top_k=5):

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


hybrid = HybridSearch(
    dense_search=dense,
    bm25_search=bm25,
    dense_weight=0.6,
    sparse_weight=0.4
)


query = "My washing machine is not draining"

query_embedding = create_embedding(query).tolist()


results = hybrid.search(
    query=query,
    query_vector=query_embedding,
    top_k=20
)


print("\nQuery:")
print(query)

print("\nHybrid Retrieval Results:\n")


for i, result in enumerate(results):

    print("Rank:", i + 1)
    print("Score:", round(result["score"], 4))
    print("Dense Score:", round(result["dense_score"], 4))
    print("BM25 Score:", round(result["bm25_score"], 4))
    print("Title:", result.get("title"))
    print("Category:", result.get("category"))
    print("Brand:", result.get("brand"))
    print("URL:", result.get("url"))
    print("Text:", result["text"][:300])
    print("-" * 70)