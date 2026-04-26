"""
Document Extractor — Async Ingestion Pipeline Coordinator

This is the **top-level orchestrator** for the entire document
ingestion pipeline.  It chains together all lower-level modules in
the correct order:

    1. **Format detection** → :class:`DocumentParserFactory`
    2. **Parsing** → :class:`PDFParser` / :class:`DocxParser` / :class:`ImageParser`
    3. **OCR fallback** → :class:`TesseractOCREngine` (automatic for image-only PDFs)
    4. **Metadata extraction** → :func:`extract_metadata`
    5. **Noise reduction** → :class:`NoiseFilter`
    6. **Smart chunking** → :class:`SmartChunker`

Both single-file and batch processing are supported.  Batch mode uses
:class:`asyncio.Semaphore` to control concurrency and prevent resource
exhaustion.

Usage
-----
>>> from agents.extractor import DocumentExtractor
>>> extractor = DocumentExtractor()
>>> result = await extractor.extract("invoice.pdf")
>>> print(result.metadata.word_count, len(result.chunks))
3842 12

>>> results = await extractor.extract_batch([
...     "invoice.pdf", "scan.png", "contract.docx"
... ], concurrency=3)
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from agents.chunking import NoiseFilter, SmartChunker, TextChunk
from agents.metadata import FileMetadata, extract_metadata
from agents.ocr_engine import OCREngine, OCREngineFactory
from agents.parsers.base import ParsedDocument
from agents.parsers.factory import DocumentParserFactory, UnsupportedFormatError

logger = logging.getLogger(__name__)


# ── Result DTO ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ExtractionResult:
    """Complete result of processing a single document through the pipeline.

    Attributes
    ----------
    document : ParsedDocument
        Raw parsed output (text, raw_pages, parser metadata).
    metadata : FileMetadata
        Unified technical metadata (size, author, word count, etc.).
    chunks : list[TextChunk]
        Semantically coherent text chunks ready for LLM ingestion.
    processing_time_ms : float
        Total wall-clock time for the full pipeline (milliseconds).
    errors : list[str]
        Non-fatal warnings encountered during processing.
    success : bool
        ``True`` if the extraction completed without fatal errors.
    source_path : str
        Absolute path to the original file.
    """

    document: ParsedDocument
    metadata: FileMetadata
    chunks: list[TextChunk]
    processing_time_ms: float
    errors: list[str] = field(default_factory=list)
    success: bool = True
    source_path: str = ""


# ── Extractor Pipeline ────────────────────────────────────────────────────────

class DocumentExtractor:
    """Async pipeline that transforms raw files into clean, chunked text.

    This class is the single entry point for all document ingestion.
    It handles:
    * Automatic format detection and parser selection
    * OCR fallback for scanned documents
    * Metadata extraction from OS + format-specific sources
    * Noise reduction (repetitive headers, boilerplate)
    * Smart chunking with page-boundary awareness

    Parameters
    ----------
    ocr_engine : OCREngine or None
        Shared OCR engine instance.  ``None`` lazily creates a default
        :class:`TesseractOCREngine`.
    chunker : SmartChunker or None
        Custom chunker.  ``None`` uses default settings
        (chunk_size=512, overlap=64).
    noise_filter : NoiseFilter or None
        Custom noise filter.  ``None`` uses default settings.
    max_pages : int
        Default maximum pages to extract from paginated documents.

    Examples
    --------
    >>> ext = DocumentExtractor(max_pages=5)
    >>> result = await ext.extract(Path("report.pdf"))
    >>> print(result.success, len(result.chunks))
    True 8
    """

    def __init__(
        self,
        ocr_engine: OCREngine | None = None,
        chunker: SmartChunker | None = None,
        noise_filter: NoiseFilter | None = None,
        max_pages: int = 10,
    ) -> None:
        self._ocr_engine = ocr_engine
        self._chunker = chunker or SmartChunker()
        self._noise_filter = noise_filter or NoiseFilter()
        self._max_pages = max_pages

    def _get_engine(self) -> OCREngine:
        """Lazy-initialise the OCR engine."""
        if self._ocr_engine is None:
            self._ocr_engine = OCREngineFactory.create()
        return self._ocr_engine

    # ── Single File ───────────────────────────────────────────────────────

    async def extract(
        self,
        file_path: str | Path,
        max_pages: int | None = None,
    ) -> ExtractionResult:
        """Process a single file through the full pipeline.

        Parameters
        ----------
        file_path : str or Path
            Path to the document to process.
        max_pages : int or None
            Override for maximum pages.  ``None`` uses the instance
            default.

        Returns
        -------
        ExtractionResult
            Complete extraction result including chunks and metadata.

        Notes
        -----
        This method **never raises** for recoverable errors — instead
        it returns an :class:`ExtractionResult` with
        ``success=False`` and the error message in ``errors``.
        Only truly unrecoverable exceptions (e.g. ``KeyboardInterrupt``)
        propagate.
        """
        file_path = Path(file_path)
        effective_max = max_pages or self._max_pages
        errors: list[str] = []
        t0 = time.perf_counter()

        logger.info(
            "═══ Pipeline START: '%s' (max_pages=%d) ═══",
            file_path.name,
            effective_max,
        )

        # ── Stage 1: Format detection & parsing ──────────────────────────
        try:
            parser = DocumentParserFactory.create(file_path)
        except (UnsupportedFormatError, FileNotFoundError, ValueError) as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            logger.error("Pipeline FAILED at format detection: %s", exc)
            return ExtractionResult(
                document=ParsedDocument(
                    text="", source_path=str(file_path), mime_type="unknown"
                ),
                metadata=extract_metadata(file_path),
                chunks=[],
                processing_time_ms=elapsed,
                errors=[str(exc)],
                success=False,
                source_path=str(file_path),
            )

        try:
            document = await parser.parse(file_path, max_pages=effective_max)
        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            logger.error("Pipeline FAILED at parsing: %s", exc)
            return ExtractionResult(
                document=ParsedDocument(
                    text="", source_path=str(file_path), mime_type="unknown"
                ),
                metadata=extract_metadata(file_path),
                chunks=[],
                processing_time_ms=elapsed,
                errors=[f"Parsing failed: {exc}"],
                success=False,
                source_path=str(file_path),
            )

        logger.info(
            "  ✓ Parsed: %d chars, %d pages, ocr=%s",
            len(document.text),
            document.page_count or 0,
            document.is_ocr_result,
        )

        # ── Stage 2: Metadata extraction ─────────────────────────────────
        try:
            file_metadata = extract_metadata(
                file_path=file_path,
                parser_metadata=document.metadata,
                extracted_text=document.text,
                mime_type=document.mime_type,
                page_count=document.page_count,
            )
        except Exception as exc:
            logger.warning("Metadata extraction failed: %s", exc)
            errors.append(f"Metadata warning: {exc}")
            file_metadata = extract_metadata(file_path)

        logger.info(
            "  ✓ Metadata: %s, %d words, author='%s'",
            file_metadata.file_size_human,
            file_metadata.word_count,
            file_metadata.author or "N/A",
        )

        # ── Stage 3: Noise reduction ─────────────────────────────────────
        try:
            if document.raw_pages:
                clean_pages = self._noise_filter.filter_pages(
                    document.raw_pages
                )
            else:
                clean_text = self._noise_filter.filter_text(document.text)
                clean_pages = [clean_text]
        except Exception as exc:
            logger.warning("Noise filtering failed: %s", exc)
            errors.append(f"Noise filter warning: {exc}")
            clean_pages = document.raw_pages or [document.text]

        logger.info("  ✓ Noise filtered: %d pages", len(clean_pages))

        # ── Stage 4: Smart chunking ──────────────────────────────────────
        try:
            chunks = self._chunker.chunk_pages(clean_pages)
        except Exception as exc:
            logger.warning("Chunking failed: %s", exc)
            errors.append(f"Chunking warning: {exc}")
            # Fallback: return the entire text as a single chunk
            chunks = [
                TextChunk(
                    content=document.text,
                    chunk_index=0,
                    start_char=0,
                    end_char=len(document.text),
                    page_number=None,
                    word_count=file_metadata.word_count,
                )
            ]

        elapsed = (time.perf_counter() - t0) * 1000

        logger.info(
            "═══ Pipeline COMPLETE: '%s' → %d chunks in %.0fms ═══",
            file_path.name,
            len(chunks),
            elapsed,
        )

        return ExtractionResult(
            document=document,
            metadata=file_metadata,
            chunks=chunks,
            processing_time_ms=elapsed,
            errors=errors,
            success=True,
            source_path=str(file_path.resolve()),
        )

    # ── Batch Processing ──────────────────────────────────────────────────

    async def extract_batch(
        self,
        file_paths: list[str | Path],
        concurrency: int = 4,
        max_pages: int | None = None,
    ) -> list[ExtractionResult]:
        """Process multiple files in parallel with controlled concurrency.

        Uses :class:`asyncio.Semaphore` to limit the number of files
        being processed simultaneously, preventing memory/CPU
        exhaustion when processing large batches.

        Parameters
        ----------
        file_paths : list[str | Path]
            Paths to all files to process.
        concurrency : int
            Maximum number of files processed in parallel (default 4).
        max_pages : int or None
            Override for maximum pages per file.

        Returns
        -------
        list[ExtractionResult]
            One result per input file, in the same order.
            Failed files have ``success=False`` — the batch never
            raises for individual file errors.
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def _limited_extract(path: str | Path) -> ExtractionResult:
            async with semaphore:
                return await self.extract(path, max_pages=max_pages)

        logger.info(
            "Batch extraction: %d files, concurrency=%d",
            len(file_paths),
            concurrency,
        )

        t0 = time.perf_counter()
        results = await asyncio.gather(
            *[_limited_extract(p) for p in file_paths]
        )
        elapsed = (time.perf_counter() - t0) * 1000

        succeeded = sum(1 for r in results if r.success)
        failed = len(results) - succeeded

        logger.info(
            "Batch complete: %d/%d succeeded, %d failed, %.0fms total",
            succeeded,
            len(results),
            failed,
            elapsed,
        )

        return list(results)
