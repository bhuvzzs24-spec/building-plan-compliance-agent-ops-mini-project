from pathlib import Path

import chromadb

from agents.rag.local_embeddings import LocalHashEmbeddingFunction


COLLECTION_NAME = "building_bye_laws"
EMBEDDING_STRATEGY = "local_hash_ngrams_v1"


def _collection(client):
    try:
        collection = client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=LocalHashEmbeddingFunction(),
        )
        if (collection.metadata or {}).get("embedding_strategy") != EMBEDDING_STRATEGY:
            client.delete_collection(COLLECTION_NAME)
            collection = None
    except Exception:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        collection = None

    if collection is None:
        collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=LocalHashEmbeddingFunction(),
            metadata={"embedding_strategy": EMBEDDING_STRATEGY},
            configuration={"hnsw": {"space": "cosine"}},
        )
    return collection


def build_vector_store(
    chunks: list[dict],
    persist_dir: str = "data/chroma_db",
) -> int:
    """Idempotently replace chunks for the sources supplied in this batch."""
    if not chunks:
        raise ValueError("No text chunks provided to index.")

    db_path = Path(persist_dir)
    db_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(db_path))
    collection = _collection(client)

    ids = []
    documents = []
    metadatas = []
    for i, chunk in enumerate(chunks):
        text = chunk.get("text", "").strip()
        if not text:
            continue
        source = str(chunk.get("source", "unknown"))
        page = chunk.get("page")
        chunk_id = f"{source}-page-{page}-chunk-{i}"
        ids.append(chunk_id)
        documents.append(text)
        metadatas.append({
            "source": source,
            "page": int(page) if page is not None else 0,
        })

    if not documents:
        raise ValueError("All supplied chunks were empty.")

    sources = sorted({metadata["source"] for metadata in metadatas})
    for source in sources:
        collection.delete(where={"source": source})
    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    return collection.count()


def remove_sources_not_in(persist_dir: str, active_sources: set[str]) -> int:
    """Remove stale source documents after a complete corpus scan."""
    db_path = Path(persist_dir)
    if not db_path.exists():
        return 0
    client = chromadb.PersistentClient(path=str(db_path))
    try:
        collection = client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=LocalHashEmbeddingFunction(),
        )
    except Exception:
        return 0
    existing = collection.get(include=["metadatas"]).get("metadatas") or []
    stale = sorted({
        str(item.get("source"))
        for item in existing
        if item.get("source") and item.get("source") not in active_sources
    })
    for source in stale:
        collection.delete(where={"source": source})
    return len(stale)



