from hashlib import sha256
from pathlib import Path

from agents.rag.pdf_loader import load_pdf
from agents.rag.text_chunker import chunk_pages
from agents.rag.vector_store import build_vector_store


def index_pdf(
    pdf_path: str,
    persist_dir: str = "data/chroma_db",
) -> dict:
    """Parse one PDF, chunk by page, and upsert with source/page metadata."""
    path = Path(pdf_path)
    pages = load_pdf(str(path))
    if not pages:
        raise ValueError("No text was extracted. The PDF may be scanned and need OCR.")
    chunks = chunk_pages(pages)
    if not chunks:
        raise ValueError("No text chunks were created.")
    count = build_vector_store(chunks, persist_dir)
    return {
        "file": path.name,
        "sha256": sha256(path.read_bytes()).hexdigest(),
        "pages_extracted": len(pages),
        "chunks_created": len(chunks),
        "total_chunks_in_collection": count,
    }
