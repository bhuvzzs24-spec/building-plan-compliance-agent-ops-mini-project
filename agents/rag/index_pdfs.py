from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import os
import time

from agents.rag.indexer import index_pdf
from agents.rag.vector_store import remove_sources_not_in


ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = Path(os.getenv("CORPUS_DIR", str(ROOT / "data" / "bye_laws")))
DB_DIR = Path(os.getenv("CHROMA_PERSIST_DIR", str(ROOT / "data" / "chroma_db")))
MANIFEST_PATH = Path(os.getenv("INDEX_MANIFEST_PATH", str(ROOT / "data" / "index_manifest.json")))


def main():
    started = time.perf_counter()
    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        raise SystemExit(
            f"No corpus PDFs found in {PDF_DIR}. Add authority-issued PDFs before indexing."
        )

    sources = set()
    documents = []
    failures = []
    for pdf_path in pdf_files:
        sources.add(pdf_path.name)
        try:
            result = index_pdf(str(pdf_path), str(DB_DIR))
            digest = sha256(pdf_path.read_bytes()).hexdigest()
            documents.append({
                **result,
                "sha256": digest,
                "path": pdf_path.relative_to(ROOT).as_posix(),
            })
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
        "stale_sources_removed": stale_sources_removed,
        "elapsed_seconds": round(elapsed, 6),
        "chunks_per_second": round(
            sum(item["chunks_created"] for item in documents) / elapsed, 3
        ) if elapsed else 0.0,
        "failures": failures,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
