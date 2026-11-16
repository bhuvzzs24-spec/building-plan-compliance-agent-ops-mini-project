import chromadb
import re

from agents.rag.local_embeddings import LocalHashEmbeddingFunction
from agents.rag.vector_store import COLLECTION_NAME


_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "by", "for", "from", "in",
    "is", "it", "of", "on", "or", "the", "this", "to", "what", "with",
}


def _lexical_score(query_tokens: set[str], text: str) -> float:
    """Simple term coverage reranker for short, table-heavy rule passages."""
    if not query_tokens:
        return 0.0
    passage_tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
    return len(query_tokens & passage_tokens) / len(query_tokens)


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

    # Keep Chroma's semantic-ish vector ranking as one signal, then rerank the
    # full small corpus by exact term coverage. Hash embeddings can otherwise
    # bury table rows whose headings/columns contain the decisive terms.
    vector_results = collection.query(
        query_texts=[question],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    vector_documents = vector_results.get("documents") or [[]]
    vector_metadatas = vector_results.get("metadatas") or [[]]
    vector_distances = vector_results.get("distances") or [[]]
    vector_rank = {
        (metadata.get("source"), metadata.get("page"), text): rank
        for rank, (text, metadata) in enumerate(
            zip(vector_documents[0], vector_metadatas[0])
        )
    }
    all_items = collection.get(include=["documents", "metadatas"])
    documents = all_items.get("documents") or []
    metadatas = all_items.get("metadatas") or []
    query_tokens = {
        token for token in re.findall(r"[a-z0-9]+", question.lower())
        if token not in _STOP_WORDS and len(token) > 1
    }
    ranked = []
    for text, metadata in zip(documents, metadatas):
        key = (metadata.get("source"), metadata.get("page"), text)
        lexical = _lexical_score(query_tokens, text)
        # Vector top-k is a modest tie-breaker so exact table wording can enter
        # the results without discarding the baseline's broader associations.
        vector_bonus = max(0.0, 1.0 - vector_rank.get(key, top_k) / max(top_k, 1))
        distance = next((
            d for t, m, d in zip(
                vector_documents[0], vector_metadatas[0], vector_distances[0]
            ) if (m.get("source"), m.get("page"), t) == key
        ), None)
        ranked.append((lexical + 0.05 * vector_bonus, {
            "text": text,
            "source": metadata.get("source", "unknown"),
            "page": metadata.get("page"),
            "distance": distance,
            "lexical_score": round(lexical, 4),
        }))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item for _, item in ranked[:top_k]]
