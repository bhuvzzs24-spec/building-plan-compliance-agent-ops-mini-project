from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import os
import argparse
import time

from agents.rag.indexer import index_pdf
from agents.rag.local_embeddings import LocalHashEmbeddingFunction
from agents.rag.vector_store import COLLECTION_NAME, remove_sources_not_in


ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = Path(os.getenv("CORPUS_DIR", str(ROOT / "data" / "bye_laws")))
DB_DIR = Path(os.getenv("CHROMA_PERSIST_DIR", str(ROOT / "data" / "chroma_db")))
MANIFEST_PATH = Path(os.getenv("INDEX_MANIFEST_PATH", str(ROOT / "data" / "index_manifest.json")))


def _source_is_indexed(source: str, db_dir: Path) -> bool:
    if not db_dir.exists():
        return False
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_collection(
            COLLECTION_NAME,
            embedding_function=LocalHashEmbeddingFunction(),
        )
        result = collection.get(where={"source": source}, include=["metadatas"])
        return bool(result.get("ids"))
    except Exception:
        return False


def source_is_current(
    pdf_path: Path, db_dir: Path, manifest_entry: dict | None, digest: str | None = None
) -> bool:
    """True only if both source bytes and indexed chunks match the manifest."""
    if not manifest_entry or not db_dir.exists():
        return False
    digest = digest or sha256(pdf_path.read_bytes()).hexdigest()
    return (
        digest == manifest_entry.get("sha256")
        and _source_is_indexed(pdf_path.name, db_dir)
    )


def main(force: bool = False):
    started = time.perf_counter()
    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        raise SystemExit(
            f"No corpus PDFs found in {PDF_DIR}. Add authority-issued PDFs before indexing."
        )

    try:
        previous_manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous_manifest = {}
    previous_documents = {
        item.get("file"): item
        for item in previous_manifest.get("documents", [])
        if isinstance(item, dict) and item.get("file")
    }

    sources = set()
    documents = []
    failures = []
    newly_indexed_chunks = 0
    reused_chunks = 0
    for pdf_path in pdf_files:
        sources.add(pdf_path.name)
        try:
            digest = sha256(pdf_path.read_bytes()).hexdigest()
            previous = previous_documents.get(pdf_path.name)
            if not force and source_is_current(pdf_path, DB_DIR, previous, digest):
                documents.append({**previous, "skipped_unchanged": True})
                reused_chunks += int(previous.get("chunks_created", 0))
                print(f"Reusing unchanged index for {pdf_path.name}")
                continue

            result = index_pdf(str(pdf_path), str(DB_DIR))
            documents.append({
                **result,
                "sha256": digest,
                "path": pdf_path.relative_to(ROOT).as_posix(),
                "skipped_unchanged": False,
            })
            newly_indexed_chunks += int(result.get("chunks_created", 0))
        except Exception as exc:
            failures.append({"source": pdf_path.name, "error_type": type(exc).__name__})
            print(f"Failed to index {pdf_path.name}: {type(exc).__name__}: {exc}")

    stale_sources_removed = remove_sources_not_in(str(DB_DIR), sources)
    elapsed = time.perf_counter() - started
    manifest = {
        "embedding_strategy": "local_hash_ngrams_v1",
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "documents": documents,
        "document_count": len(documents),
        "chunks_indexed": sum(item["chunks_created"] for item in documents),
        "chunks_reused": reused_chunks,
        "chunks_created_this_run": newly_indexed_chunks,
        "stale_sources_removed": stale_sources_removed,
        "elapsed_seconds": round(elapsed, 6),
        "chunks_per_second": round(newly_indexed_chunks / elapsed, 3) if elapsed else 0.0,
        "failures": failures,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Idempotently index local building-rule PDFs")
    parser.add_argument("--force", action="store_true", help="Rebuild indexes even when source hashes match")
    main(force=parser.parse_args().force)
