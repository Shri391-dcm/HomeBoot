import json
import time

import chromadb

from retrieval.bm25_search import BM25Search
from retrieval.embeddings import create_embedding
from retrieval.hybrid_search import HybridSearch
from retrieval.reranker import CrossEncoderReranker


# --------------------------------------------------
# Configuration
# --------------------------------------------------

GOLDEN_QUERIES_PATH = "evaluation/golden_queries.json"
CHUNKS_PATH = "data/chunks/chunks.jsonl"
CHROMA_PATH = "data/vector_db"
COLLECTION_NAME = "homeboot_chunks"

CANDIDATE_K = 20
FINAL_K = 5


# --------------------------------------------------
# Load evaluation queries
# --------------------------------------------------

with open(
    GOLDEN_QUERIES_PATH,
    "r",
    encoding="utf-8",
) as file:
    golden_data = json.load(file)

# Supports both:
# 1. A simple JSON list
# 2. The newer {"items": [...]} format
if isinstance(golden_data, dict):
    evaluation_queries = golden_data.get("items", [])
else:
    evaluation_queries = golden_data

if not evaluation_queries:
    raise ValueError("No evaluation queries were found.")


# --------------------------------------------------
# Load chunks for BM25
# --------------------------------------------------

with open(
    CHUNKS_PATH,
    "r",
    encoding="utf-8",
) as file:
    chunks = [
        json.loads(line)
        for line in file
        if line.strip()
    ]

bm25 = BM25Search(chunks)


# --------------------------------------------------
# ChromaDB dense search
# --------------------------------------------------

client = chromadb.PersistentClient(
    path=CHROMA_PATH
)

collection = client.get_collection(
    name=COLLECTION_NAME
)


class DenseSearch:
    """Search document embeddings stored in ChromaDB."""

    def search(
        self,
        query_vector,
        top_k=20,
    ):
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
        )

        output = []

        for index in range(
            len(results["ids"][0])
        ):
            metadata = (
                results["metadatas"][0][index]
                or {}
            )

            output.append(
                {
                    "id": results["ids"][0][index],
                    "score": (
                        1
                        - results["distances"][0][index]
                    ),
                    "text": results["documents"][0][index],
                    "metadata": metadata,
                    "title": metadata.get(
                        "title",
                        "",
                    ),
                    "category": metadata.get(
                        "category",
                        "",
                    ),
                    "brand": metadata.get(
                        "brand",
                        "",
                    ),
                    "url": metadata.get(
                        "url",
                        "",
                    ),
                    "page_type": metadata.get(
                        "page_type",
                        "",
                    ),
                }
            )

        return output


dense = DenseSearch()


# --------------------------------------------------
# Hybrid search and reranker
# --------------------------------------------------

hybrid = HybridSearch(
    dense_search=dense,
    bm25_search=bm25,
)

reranker = CrossEncoderReranker()


# --------------------------------------------------
# Relevance and metrics
# --------------------------------------------------

def is_relevant(result, gold_item):
    """
    Determine whether a retrieved result is relevant.

    Preferred method:
    Match against manually verified chunk IDs.

    Temporary fallback:
    Match against expected appliance category.
    """

    relevant_chunk_ids = set(
        gold_item.get("relevant_chunk_ids")
        or gold_item.get("expected_chunk_ids")
        or []
    )

    if relevant_chunk_ids:
        return result.get("id") in relevant_chunk_ids

    expected_category = gold_item.get(
        "expected_category"
    )

    if expected_category:
        result_category = (
            result.get("category")
            or result.get(
                "metadata",
                {},
            ).get("category")
        )

        return result_category == expected_category

    return False


def recall_at_k(
    results,
    gold_item,
    k,
):
    """Return 1 when at least one relevant result is in top K."""

    return int(
        any(
            is_relevant(result, gold_item)
            for result in results[:k]
        )
    )


def reciprocal_rank(
    results,
    gold_item,
):
    """Return reciprocal rank of the first relevant result."""

    for rank, result in enumerate(
        results,
        start=1,
    ):
        if is_relevant(result, gold_item):
            return 1 / rank

    return 0.0


# --------------------------------------------------
# Run evaluation
# --------------------------------------------------

methods = {
    "Hybrid": [],
    "Hybrid + Reranker": [],
}

evaluated_queries = 0


for gold_item in evaluation_queries:

    # Unanswerable questions are evaluated separately
    # using refusal accuracy, not retrieval Recall/MRR.
    if gold_item.get("answerable") is False:
        continue

    has_relevance_label = bool(
        gold_item.get("relevant_chunk_ids")
        or gold_item.get("expected_chunk_ids")
        or gold_item.get("expected_category")
    )

    if not has_relevance_label:
        print(
            "Skipping item without relevance labels:",
            gold_item.get("query_id", "unknown"),
        )
        continue

    query = gold_item["query"]

    print("\nQuery:", query)

    # Create a fresh embedding for this query.
    query_embedding = create_embedding(
        query
    ).tolist()

    # ----------------------------------------------
    # Hybrid candidate retrieval
    # ----------------------------------------------

    hybrid_start = time.perf_counter()

    hybrid_results = hybrid.search(
        query=query,
        query_vector=query_embedding,
        top_k=CANDIDATE_K,
    )

    hybrid_latency = (
        time.perf_counter()
        - hybrid_start
    )

    candidate_recall_20 = recall_at_k(
        hybrid_results,
        gold_item,
        CANDIDATE_K,
    )
    if candidate_recall_20 == 0:
    print(
        "FAILED Recall@20:",
        query,
    )

    methods["Hybrid"].append(
        {
            "recall@20": candidate_recall_20,
            "recall@5": recall_at_k(
                hybrid_results,
                gold_item,
                FINAL_K,
            ),
            "mrr": reciprocal_rank(
                hybrid_results,
                gold_item,
            ),
            "latency": hybrid_latency,
        }
    )

    # ----------------------------------------------
    # Cross-encoder reranking
    # ----------------------------------------------

    rerank_start = time.perf_counter()

    reranked_pool = reranker.rerank(
        hybrid_results,
        query,
    )

    rerank_latency = (
        time.perf_counter()
        - rerank_start
    )

    # Professor requires final top 5 or fewer.
    final_reranked_results = (
        reranked_pool[:FINAL_K]
    )

    methods["Hybrid + Reranker"].append(
        {
            # Recall@20 is measured before reranking.
            # This is the reranker's maximum possible ceiling.
            "recall@20": candidate_recall_20,
            "recall@5": recall_at_k(
                final_reranked_results,
                gold_item,
                FINAL_K,
            ),
            "mrr": reciprocal_rank(
                final_reranked_results,
                gold_item,
            ),
            "latency": (
                hybrid_latency
                + rerank_latency
            ),
            "rerank_latency": rerank_latency,
        }
    )

    evaluated_queries += 1


if evaluated_queries == 0:
    raise ValueError(
        "No answerable queries with relevance labels "
        "were available for evaluation."
    )


# --------------------------------------------------
# Report helper
# --------------------------------------------------

def average(results, metric_name):
    return sum(
        result[metric_name]
        for result in results
    ) / len(results)


# --------------------------------------------------
# Print report
# --------------------------------------------------

print("\n\nEvaluation Results")
print("Queries evaluated:", evaluated_queries)
print()

for method_name, results in methods.items():

    recall_20 = average(
        results,
        "recall@20",
    )

    recall_5 = average(
        results,
        "recall@5",
    )

    mrr = average(
        results,
        "mrr",
    )

    latency = average(
        results,
        "latency",
    )

    print(method_name)
    print("----------------------")
    print(
        "Recall@20:",
        round(recall_20, 3),
    )
    print(
        "Recall@5:",
        round(recall_5, 3),
    )
    print(
        "MRR:",
        round(mrr, 3),
    )
    print(
        "Avg Latency:",
        round(latency, 3),
        "seconds",
    )

    if method_name == "Hybrid + Reranker":
        added_reranker_latency = average(
            results,
            "rerank_latency",
        )

        print(
            "Added Reranker Latency:",
            round(
                added_reranker_latency,
                3,
            ),
            "seconds",
        )

    print()


# --------------------------------------------------
# Reranker metric lift
# --------------------------------------------------

hybrid_results_summary = methods["Hybrid"]
reranked_results_summary = methods[
    "Hybrid + Reranker"
]

hybrid_recall_5 = average(
    hybrid_results_summary,
    "recall@5",
)

reranked_recall_5 = average(
    reranked_results_summary,
    "recall@5",
)

hybrid_mrr = average(
    hybrid_results_summary,
    "mrr",
)

reranked_mrr = average(
    reranked_results_summary,
    "mrr",
)

average_reranker_latency = average(
    reranked_results_summary,
    "rerank_latency",
)

print("Reranker Lift")
print("----------------------")
print(
    "Recall@5 Lift:",
    round(
        reranked_recall_5
        - hybrid_recall_5,
        3,
    ),
)
print(
    "MRR Lift:",
    round(
        reranked_mrr
        - hybrid_mrr,
        3,
    ),
)
print(
    "Added Latency:",
    round(
        average_reranker_latency,
        3,
    ),
    "seconds",
)