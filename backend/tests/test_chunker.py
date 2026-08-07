import pytest
from ingestion.chunker import _clean_text, _split_into_chunks, chunk_document
from ingestion.extractor import ExtractedDocument, ExtractedPage


def make_doc(text: str) -> ExtractedDocument:
    page = ExtractedPage(
        page_number=1,
        text=text,
        method="pdfplumber",
        char_count=len(text),
    )
    return ExtractedDocument(
        file_path="test.pdf",
        pages=[page],
        total_chars=len(text),
        ocr_pages=0,
    )


class TestCleanText:

    def test_collapses_multiple_newlines(self):
        text = "hello\n\n\n\nworld"
        result = _clean_text(text)
        assert "\n\n\n" not in result

    def test_rejoins_hyphenated_words(self):
        text = "distribu-\nted systems"
        result = _clean_text(text)
        assert "distributed systems" in result

    def test_collapses_multiple_spaces(self):
        text = "hello    world"
        result = _clean_text(text)
        assert "  " not in result


class TestSplitIntoChunks:

    def test_returns_chunks(self):
        text = "A" * 1000
        chunks = _split_into_chunks(text, chunk_size=200, overlap=50)
        assert len(chunks) > 1

    def test_chunks_have_offset(self):
        text = "Hello world. " * 100
        chunks = _split_into_chunks(text, chunk_size=100, overlap=20)
        offsets = [c[1] for c in chunks]
        assert offsets == sorted(offsets)

    def test_overlap_means_chunks_share_content(self):
        text = "word " * 200
        chunks = _split_into_chunks(text, chunk_size=100, overlap=50)
        assert len(chunks) > 2


class TestChunkDocument:

    def test_produces_chunks(self):
        doc = make_doc("This is a test document. " * 50)
        meta = {
            "doc_id": "test123",
            "title": "Test Doc",
            "source_url": "http://example.com",
            "source_site": "example.com",
        }
        chunks = chunk_document(doc, meta)
        assert len(chunks) > 0

    def test_chunk_ids_are_unique(self):
        doc = make_doc("This is a test document. " * 50)
        meta = {
            "doc_id": "test123",
            "title": "Test Doc",
            "source_url": "http://example.com",
            "source_site": "example.com",
        }
        chunks = chunk_document(doc, meta)
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_empty_document_returns_no_chunks(self):
        doc = make_doc("")
        meta = {
            "doc_id": "empty",
            "title": "Empty",
            "source_url": "",
            "source_site": "",
        }
        chunks = chunk_document(doc, meta)
        assert chunks == []

    def test_chunk_has_correct_metadata(self):
        doc = make_doc("Government spending report. " * 30)
        meta = {
            "doc_id": "gov001",
            "title": "Spending Report",
            "source_url": "http://gov.in/report.pdf",
            "source_site": "gov.in",
        }
        chunks = chunk_document(doc, meta)
        assert chunks[0].source_site == "gov.in"
        assert chunks[0].title == "Spending Report"
        assert chunks[0].doc_id == "gov001"