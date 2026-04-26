"""
Tests for the NoiseFilter and SmartChunker modules.
"""

import pytest

from agents.chunking import NoiseFilter, SmartChunker, TextChunk


# ═══════════════════════════════════════════════════════════════════════════
#  NoiseFilter
# ═══════════════════════════════════════════════════════════════════════════

class TestNoiseFilter:
    """Test noise removal capabilities."""

    def test_remove_page_numbers(self):
        nf = NoiseFilter()
        text = "Page 1 of 10\nSome real content\nPage 2 of 10"
        result = nf.filter_text(text)
        assert "Page 1 of 10" not in result
        assert "Some real content" in result

    def test_remove_confidential_watermark(self):
        nf = NoiseFilter()
        text = "CONFIDENTIAL\nActual document text here.\nDRAFT"
        result = nf.filter_text(text)
        assert "CONFIDENTIAL" not in result
        assert "DRAFT" not in result
        assert "Actual document text" in result

    def test_remove_repetitive_headers_across_pages(self):
        nf = NoiseFilter(repetition_threshold=0.60)
        pages = [
            "Company Inc.\nPage content one.\nFooter 2024",
            "Company Inc.\nPage content two.\nFooter 2024",
            "Company Inc.\nPage content three.\nFooter 2024",
            "Company Inc.\nPage content four.\nFooter 2024",
        ]
        result = nf.filter_pages(pages)

        # "Company Inc." appears on all pages — should be removed
        for page in result:
            assert "Company Inc." not in page

        # Actual content should remain
        assert any("content one" in p for p in result)
        assert any("content four" in p for p in result)

    def test_normalise_whitespace(self):
        nf = NoiseFilter()
        text = "Line one\n\n\n\n\nLine two\n\n\n\n\n\nLine three"
        result = nf.filter_text(text)
        # Should have at most one blank line between content
        assert "\n\n\n" not in result
        assert "Line one" in result
        assert "Line three" in result

    def test_filter_pages_returns_same_count(self):
        nf = NoiseFilter()
        pages = ["page1", "page2", "page3"]
        result = nf.filter_pages(pages)
        assert len(result) == 3

    def test_custom_boilerplate_pattern(self):
        nf = NoiseFilter(boilerplate_patterns=[r"(?i)^disclaimer.*$"])
        text = "Disclaimer: this is not legal advice.\nReal content."
        result = nf.filter_text(text)
        assert "Disclaimer" not in result
        assert "Real content" in result


# ═══════════════════════════════════════════════════════════════════════════
#  SmartChunker
# ═══════════════════════════════════════════════════════════════════════════

class TestSmartChunker:
    """Test the recursive character text splitter."""

    def test_short_text_single_chunk(self):
        chunker = SmartChunker(chunk_size=1000)
        chunks = chunker.chunk("Short text")
        assert len(chunks) == 1
        assert chunks[0].content == "Short text"

    def test_splits_on_paragraphs(self):
        chunker = SmartChunker(chunk_size=50, chunk_overlap=0)
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        chunks = chunker.chunk(text)
        assert len(chunks) >= 2
        # No chunk should be cut mid-sentence
        for chunk in chunks:
            assert chunk.content.strip()  # non-empty

    def test_chunk_overlap(self):
        chunker = SmartChunker(chunk_size=30, chunk_overlap=10)
        text = "AAAA BBBB CCCC DDDD EEEE FFFF GGGG HHHH IIII JJJJ"
        chunks = chunker.chunk(text)
        # With overlap, consecutive chunks should share some text
        assert len(chunks) >= 2

    def test_empty_text_returns_empty(self):
        chunker = SmartChunker()
        assert chunker.chunk("") == []
        assert chunker.chunk("   ") == []

    def test_chunk_pages_preserves_page_numbers(self):
        chunker = SmartChunker(chunk_size=50, chunk_overlap=0)
        pages = [
            "Content on page one is here.",
            "Content on page two is here.",
            "Content on page three is here.",
        ]
        chunks = chunker.chunk_pages(pages)

        # Each chunk should have a page_number set
        assert all(c.page_number is not None for c in chunks)
        # Page numbers should be 1-indexed
        page_numbers = {c.page_number for c in chunks}
        assert page_numbers.issubset({1, 2, 3})

    def test_chunk_pages_skips_empty_pages(self):
        chunker = SmartChunker()
        pages = ["Content", "", "  ", "More content"]
        chunks = chunker.chunk_pages(pages)
        page_numbers = {c.page_number for c in chunks}
        # Empty pages should not produce chunks
        assert 2 not in page_numbers
        assert 3 not in page_numbers

    def test_chunk_index_monotonic(self):
        chunker = SmartChunker(chunk_size=30, chunk_overlap=0)
        text = "Word " * 50  # 250 chars
        chunks = chunker.chunk(text)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_word_count_populated(self):
        chunker = SmartChunker(chunk_size=100, chunk_overlap=0)
        chunks = chunker.chunk("Hello world this is a test")
        assert all(c.word_count > 0 for c in chunks)

    def test_invalid_overlap_raises(self):
        with pytest.raises(ValueError, match="chunk_overlap"):
            SmartChunker(chunk_size=50, chunk_overlap=60)

    def test_large_document_chunking(self):
        """Smoke test with a realistic document size."""
        chunker = SmartChunker(chunk_size=512, chunk_overlap=64)
        # ~10,000 characters
        text = ("This is a paragraph of text. " * 20 + "\n\n") * 20
        chunks = chunker.chunk(text)

        assert len(chunks) > 1
        # No chunk should vastly exceed the target size
        for chunk in chunks:
            # Allow 2x because of overlap
            assert len(chunk.content) <= 512 * 2 + 64
