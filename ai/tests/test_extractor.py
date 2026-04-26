"""
Integration tests for the DocumentExtractor pipeline.

These tests verify the full end-to-end flow: file → parse → metadata →
noise filter → chunking → ExtractionResult.

Uses mock OCR to avoid requiring Tesseract in CI.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

from agents.extractor import DocumentExtractor, ExtractionResult


class TestDocumentExtractorDocx:
    """Integration tests using real DOCX files."""

    @pytest.mark.asyncio
    async def test_full_pipeline_docx(self, sample_docx: Path):
        extractor = DocumentExtractor(max_pages=10)
        result = await extractor.extract(sample_docx)

        assert isinstance(result, ExtractionResult)
        assert result.success is True
        assert result.errors == []
        assert len(result.chunks) > 0
        assert result.metadata.word_count > 0
        assert result.metadata.file_name == "test_document.docx"
        assert result.processing_time_ms > 0
        assert "first paragraph" in result.document.text

    @pytest.mark.asyncio
    async def test_metadata_populated(self, sample_docx: Path):
        extractor = DocumentExtractor()
        result = await extractor.extract(sample_docx)

        assert result.metadata.author == "Test Author"
        assert result.metadata.title == "Test Title"
        assert result.metadata.file_size_bytes > 0
        assert result.metadata.created_at is not None


class TestDocumentExtractorImage:
    """Integration tests using image files with mocked OCR."""

    @pytest.mark.asyncio
    async def test_full_pipeline_image(
        self, sample_text_image: Path, mock_ocr_engine
    ):
        extractor = DocumentExtractor(ocr_engine=mock_ocr_engine)
        result = await extractor.extract(sample_text_image)

        assert result.success is True
        assert result.document.is_ocr_result is True
        assert result.document.page_count == 1
        assert len(result.chunks) > 0


class TestDocumentExtractorErrors:
    """Test error handling in the pipeline."""

    @pytest.mark.asyncio
    async def test_unsupported_format(self, tmp_dir: Path):
        # Create a .xyz file
        weird = tmp_dir / "data.xyz"
        weird.write_text("some data")

        extractor = DocumentExtractor()
        result = await extractor.extract(weird)

        assert result.success is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_nonexistent_file(self, tmp_dir: Path):
        extractor = DocumentExtractor()
        result = await extractor.extract(tmp_dir / "ghost.pdf")

        assert result.success is False
        assert len(result.errors) > 0


class TestBatchExtraction:
    """Test batch processing."""

    @pytest.mark.asyncio
    async def test_batch_multiple_files(self, sample_docx: Path):
        extractor = DocumentExtractor()

        # Process the same file twice to test concurrency
        results = await extractor.extract_batch(
            [sample_docx, sample_docx],
            concurrency=2,
        )

        assert len(results) == 2
        assert all(r.success for r in results)
        assert all(r.metadata.word_count > 0 for r in results)

    @pytest.mark.asyncio
    async def test_batch_with_failures(self, sample_docx: Path, tmp_dir: Path):
        extractor = DocumentExtractor()
        bad_file = tmp_dir / "bad.xyz"
        bad_file.write_text("invalid")

        results = await extractor.extract_batch(
            [sample_docx, bad_file],
            concurrency=2,
        )

        assert len(results) == 2
        # One should succeed, one should fail
        successes = [r for r in results if r.success]
        failures = [r for r in results if not r.success]
        assert len(successes) == 1
        assert len(failures) == 1

    @pytest.mark.asyncio
    async def test_batch_empty_list(self):
        extractor = DocumentExtractor()
        results = await extractor.extract_batch([])
        assert results == []
