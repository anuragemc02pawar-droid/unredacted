import pytest
from unittest.mock import MagicMock, patch
from analysis.contradiction import (
    _extract_specific_values,
    _values_conflict,
    _build_conflict_hint,
    ContradictionDetector,
)
from store.document_store import RetrievedChunk


def make_chunk(chunk_id, doc_id, text, title="Test"):
    return RetrievedChunk(
        chunk_id=chunk_id,
        doc_id=doc_id,
        text=text,
        score=0.9,
        title=title,
        source_url="http://example.com",
        source_site="example.com",
        page_start=1,
    )


class TestExtractSpecificValues:

    def test_extracts_crore_amounts(self):
        text = "The government allocated 2400 crore for this scheme."
        values = _extract_specific_values(text)
        assert any("crore" in v.lower() for v in values)

    def test_extracts_years(self):
        text = "In 2019 the policy was introduced."
        values = _extract_specific_values(text)
        assert any("2019" in v for v in values)

    def test_extracts_percentages(self):
        text = "GDP growth was 7.2% in the last quarter."
        values = _extract_specific_values(text)
        assert any("%" in v for v in values)

    def test_empty_text_returns_empty(self):
        assert _extract_specific_values("") == []


class TestValuesConflict:

    def test_disjoint_sets_conflict(self):
        assert _values_conflict(["2400 crore"], ["1800 crore"]) is True

    def test_overlapping_sets_dont_conflict(self):
        assert _values_conflict(["2400 crore"], ["2400 crore"]) is False

    def test_empty_values_dont_conflict(self):
        assert _values_conflict([], ["2400 crore"]) is False
        assert _values_conflict(["2400 crore"], []) is False


class TestContradictionDetector:

    def test_needs_at_least_two_chunks(self):
        detector = ContradictionDetector()
        chunk = make_chunk("a", "doc1", "Some text about policy.")
        result = detector.detect([chunk])
        assert result == []

    def test_skips_same_document_chunks(self):
        detector = ContradictionDetector()
        chunk_a = make_chunk("a", "doc1", "Allocated 2400 crore for education.")
        chunk_b = make_chunk("b", "doc1", "Allocated 1800 crore for education.")
        result = detector.detect([chunk_a, chunk_b])
        assert result == []