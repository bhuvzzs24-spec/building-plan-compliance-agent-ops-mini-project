import chromadb

from agents.rag.local_embeddings import LocalHashEmbeddingFunction
from agents.rag.vector_store import COLLECTION_NAME


def retrieve_clauses(
    question: str,
    persist_dir: str = "data/chroma_db",
    top_k: int = 5,
) -> list[dict]:
    """Retrieve top passages with source and PDF page metadata."""
    if not question.strip():
        raise ValueError("Question cannot be empty")
    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    client = chromadb.PersistentClient(path=persist_dir)
    try:
        collection = client.get_collection(
            COLLECTION_NAME,
            embedding_function=LocalHashEmbeddingFunction(),
        )
    except Exception as exc:
        raise ValueError(
            "The building_bye_laws collection was not found. "
            "Index the corpus first."
        ) from exc
    if collection.count() == 0:
        return []

    results = collection.query(
        query_texts=[question],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    documents = results.get("documents") or [[]]
    metadatas = results.get("metadatas") or [[]]
    distances = results.get("distances") or [[]]
    return [
        {
            "text": text,
            "source": metadata.get("source", "unknown"),
            "page": metadata.get("page"),
            "distance": distance,
        }
        for text, metadata, distance in zip(documents[0], metadatas[0], distances[0])
    ]
