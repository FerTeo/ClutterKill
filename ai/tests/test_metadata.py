"""
Tests for the FileMetadata extraction module.
"""

import pytest
from pathlib import Path

from agents.metadata import extract_metadata, FileMetadata, _human_readable_size


class TestHumanReadableSize:
    """Test the byte-to-human conversion helper."""

    def test_zero(self):
        assert _human_readable_size(0) == "0 B"

    def test_bytes(self):
        assert _human_readable_size(500) == "500.0 B"

    def test_kilobytes(self):
        result = _human_readable_size(1536)
        assert "KB" in result

    def test_megabytes(self):
        result = _human_readable_size(2_500_000)
        assert "MB" in result


class TestExtractMetadata:
    """Test the main extract_metadata function."""

    def test_basic_extraction(self, sample_docx: Path):
        meta = extract_metadata(
            file_path=sample_docx,
            parser_metadata={"author": "Daria", "title": "Test"},
            extracted_text="word " * 100,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            page_count=3,
        )

        assert isinstance(meta, FileMetadata)
        assert meta.file_name == "test_document.docx"
        assert meta.file_size_bytes > 0
        assert meta.author == "Daria"
        assert meta.title == "Test"
        assert meta.word_count == 100
        assert meta.char_count == 500
        assert meta.page_count == 3
        assert meta.estimated_reading_time_min > 0
        assert "KB" in meta.file_size_human or "B" in meta.file_size_human

    def test_missing_metadata(self, sample_docx: Path):
        meta = extract_metadata(
            file_path=sample_docx,
            parser_metadata=None,
            extracted_text="hello",
        )

        assert meta.author is None
        assert meta.title is None
        assert meta.word_count == 1

    def test_frozen(self, sample_docx: Path):
        meta = extract_metadata(file_path=sample_docx)
        with pytest.raises(AttributeError):
            meta.author = "changed"

    def test_nonexistent_file(self, tmp_dir: Path):
        # Should not raise — returns defaults for missing file
        meta = extract_metadata(
            file_path=tmp_dir / "ghost.txt",
            extracted_text="some text",
        )
        assert meta.file_size_bytes == 0
        assert meta.created_at is None
