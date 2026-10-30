import pytest
from agents.rag.vector_store import build_vector_store
from agents.rag.pdf_loader import load_pdf

from agents.rag.text_chunker import chunk_pages
from agents.rag.retriever import retrieve_clauses


def test_chunker_preserves_source_and_page():
    pages = [{
        "source": "sample_test.pdf",
        "page": 3,
        "text": "Synthetic text for testing source citations."
    }]

    chunks = chunk_pages(pages)

    assert chunks
    assert chunks[0]["source"] == "sample_test.pdf"
    assert chunks[0]["page"] == 3


def test_retriever_rejects_blank_question():
    try:
        retrieve_clauses(
            "   ",
            "data/chroma_validation_test",
            1
        )
    except ValueError as exc:
        assert "Question cannot be empty" in str(exc)
    else:
        raise AssertionError("Blank question should be rejected")


def test_retriever_rejects_zero_top_k():
    try:
        retrieve_clauses(
            "sample query",
            "data/chroma_validation_test",
            0
        )
    except ValueError as exc:
        assert "top_k must be at least 1" in str(exc)
    else:
        raise AssertionError("top_k=0 should be rejected")




def test_loader_rejects_missing_pdf(tmp_path):
    missing_pdf = tmp_path / "missing.pdf"

    with pytest.raises(FileNotFoundError):
        load_pdf(str(missing_pdf))


def test_loader_rejects_non_pdf_file(tmp_path):
    text_file = tmp_path / "rules.txt"
    text_file.write_text("Synthetic test content", encoding="utf-8")

    with pytest.raises(ValueError, match="must be a PDF"):
        load_pdf(str(text_file))




def test_vector_store_upserts_chunks_without_duplicates(tmp_path):
    db_path = str(tmp_path / "chroma_db")
    chunks = [
        {
            "source": "synthetic_test.pdf",
            "page": 1,
            "text": "Synthetic passage about setbacks and road width."
        }
    ]

    first_count = build_vector_store(chunks, db_path)
    second_count = build_vector_store(chunks, db_path)

    assert first_count == 1
    assert second_count == 1
def test_end_to_end_pdf_index_retrieval_and_citation(tmp_path):
    from pathlib import Path
    from pypdf import PdfWriter
    from pypdf.generic import (
        DictionaryObject,
        DecodedStreamObject,
        NameObject,
    )
    from agents.rag.indexer import index_pdf
    from agents.rag.retriever import retrieve_clauses

    pdf_path = tmp_path / "synthetic_test.pdf"
    db_path = str(tmp_path / "chroma_db")

    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)

    font = DictionaryObject()
    font.update({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    fonts = DictionaryObject()
    fonts[NameObject("/F1")] = writer._add_object(font)
    resources = DictionaryObject()
    resources[NameObject("/Font")] = fonts
    page[NameObject("/Resources")] = resources

    stream = DecodedStreamObject()
    stream.set_data(
        b"BT /F1 12 Tf 72 720 Td "
        b"(Synthetic test passage about setbacks and road width.) Tj ET"
    )
    page[NameObject("/Contents")] = writer._add_object(stream)

    with pdf_path.open("wb") as file:
        writer.write(file)

    indexed = index_pdf(str(pdf_path), db_path)
    assert indexed["pages_extracted"] == 1
    assert indexed["chunks_created"] == 1

    results = retrieve_clauses(
        "setbacks and road width",
        db_path,
        3,
    )

    assert results
    assert "Synthetic test passage" in results[0]["text"]
    assert results[0]["source"] == "synthetic_test.pdf"
    assert results[0]["page"] == 1
def test_reindexing_removes_stale_chunks(tmp_path):
    from agents.rag.vector_store import build_vector_store
    import chromadb

    db_path = str(tmp_path / "chroma_db")

    original = [
        {"source": "changing.pdf", "page": 1, "text": "First old chunk."},
        {"source": "changing.pdf", "page": 1, "text": "Second old chunk."},
    ]
    updated = [
        {"source": "changing.pdf", "page": 1, "text": "Updated single chunk."},
    ]

    build_vector_store(original, db_path)
    count = build_vector_store(updated, db_path)

    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_collection("building_bye_laws")

    assert count == 1
    assert collection.count() == 1
    assert collection.get()["documents"] == ["Updated single chunk."]
def test_retriever_returns_empty_for_empty_collection(tmp_path):
    import chromadb
    from agents.rag.retriever import retrieve_clauses

    db_path = str(tmp_path / "empty_db")
    client = chromadb.PersistentClient(path=db_path)
    from agents.rag.local_embeddings import LocalHashEmbeddingFunction
    client.get_or_create_collection(
        "building_bye_laws",
        embedding_function=LocalHashEmbeddingFunction(),
        metadata={"embedding_strategy": "local_hash_ngrams_v1"},
    )

    results = retrieve_clauses(
        "What are the building setback rules?",
        db_path,
        3,
    )

    assert results == []


def test_retrieved_clauses_include_source_and_page(tmp_path):
    from agents.rag.vector_store import build_vector_store
    from agents.rag.retriever import retrieve_clauses

    db_path = str(tmp_path / "citation_db")
    build_vector_store(
        [
            {
                "source": "official_test.pdf",
                "page": 7,
                "text": "Setback requirements are described in this test passage.",
            }
        ],
        db_path,
    )

    results = retrieve_clauses(
        "setback requirements",
        db_path,
        1,
    )

    assert results
    assert results[0]["source"] == "official_test.pdf"
    assert results[0]["page"] == 7
    assert results[0]["text"]

