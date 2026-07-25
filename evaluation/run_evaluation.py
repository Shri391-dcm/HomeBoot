import json
import time

from retrieval.embeddings import create_embedding
from retrieval.bm25_search import BM25Search
from retrieval.hybrid_search import HybridSearch
from retrieval.reranker import CrossEncoderReranker

import chromadb


# -----------------------------
# Load evaluation queries
# -----------------------------

with open(
    "evaluation/golden_queries.json",
    "r",
    encoding="utf-8"
) as f:
    evaluation_queries = json.load(f)


# -----------------------------
# Load chunks for BM25
# -----------------------------

with open(
    "data/chunks/chunks.jsonl",
    "r",
    encoding="utf-8"
) as f:
    chunks = [json.loads(line) for line in f]


bm25 = BM25Search(chunks)


# -----------------------------
# Chroma dense search
# -----------------------------

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


# -----------------------------
# Hybrid + Reranker
# -----------------------------

hybrid = HybridSearch(
    dense_search=dense,
    bm25_search=bm25
)


reranker = CrossEncoderReranker()


# -----------------------------
# Metrics
# -----------------------------

def recall_at_k(results, expected_category, k):

    for item in results[:k]:

        if item.get("category") == expected_category:
            return 1

    return 0



def reciprocal_rank(results, expected_category):

    for rank, item in enumerate(results, start=1):

        if item.get("category") == expected_category:
            return 1 / rank

    return 0



# -----------------------------
# Run Evaluation
# -----------------------------

methods = {
    "Hybrid": [],
    "Hybrid + Reranker": []
}


for item in evaluation_queries:

    query = item["query"]
    expected = item["expected_category"]

    print("\nQuery:", query)

    embedding = create_embedding(query).tolist()


    start = time.time()

    hybrid_results = hybrid.search(
        query=query,
        query_vector=embedding,
        top_k=20
    )

    hybrid_time = time.time() - start


    methods["Hybrid"].append(
        {
            "recall@5": recall_at_k(
                hybrid_results,
                expected,
                5
            ),
            "mrr": reciprocal_rank(
                hybrid_results,
                expected
            ),
            "latency": hybrid_time
        }
    )


    start = time.time()

    reranked_results = reranker.rerank(
        hybrid_results,
        query
    )

    rerank_time = time.time() - start


    methods["Hybrid + Reranker"].append(
        {
            "recall@5": recall_at_k(
                reranked_results,
                expected,
                5
            ),
            "mrr": reciprocal_rank(
                reranked_results,
                expected
            ),
            "latency": hybrid_time + rerank_time
        }
    )


# -----------------------------
# Report
# -----------------------------

print("\n\nEvaluation Results\n")

for name, results in methods.items():

    recall = sum(
        x["recall@5"]
        for x in results
    ) / len(results)


    mrr = sum(
        x["mrr"]
        for x in results
    ) / len(results)


    latency = sum(
        x["latency"]
        for x in results
    ) / len(results)


    print(name)
    print("----------------------")
    print("Recall@5:", round(recall, 3))
    print("MRR:", round(mrr, 3))
    print("Avg Latency:", round(latency, 3), "seconds")
    print()
