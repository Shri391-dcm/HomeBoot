import chromadb
from retrieval.embeddings import create_embedding

DB_PATH = "data/vector_db"

client = chromadb.PersistentClient(path=DB_PATH)

collection = client.get_collection(
    name="homeboot_chunks"
)

query = "My washing machine is not draining"

query_embedding = create_embedding(query).tolist()

results = collection.query(
    query_embeddings=[query_embedding],
    n_results=5,
    where={
        "category": "washer"
    }
)

print("\nQuery:")
print(query)

print("\nTop Dense Retrieval Results:\n")

for i in range(len(results["ids"][0])):
    print("Rank:", i + 1)
    print("Distance:", results["distances"][0][i])
    print("Title:", results["metadatas"][0][i]["title"])
    print("Category:", results["metadatas"][0][i]["category"])
    print("URL:", results["metadatas"][0][i]["url"])
    print("Text:", results["documents"][0][i][:300])
    print("-" * 70)
