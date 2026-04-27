"""
Base Document Parser — Abstract Interface

Defines the core data structures and abstract contract that every
document parser must implement.  This follows the Dependency Inversion
Principle (SOLID-D): high-level pipeline code depends on this
abstraction, never on concrete parsers.

Classes
-------
ParsedDocument
    Immutable result produced by any parser.
BaseDocumentParser
    Abstract base class — subclassed by PDFParser, DocxParser,
    ImageParser, etc.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


# ── Data Transfer Object ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class ParsedDocument:
    """Immutable container for a successfully parsed document.

    Every parser returns one of these, regardless of the source format.
    Down-stream stages (metadata extraction, chunking, LLM ingestion)
    consume this single, unified type.

    Attributes
    ----------
    text : str
        Full extracted text, cleaned and ready for downstream processing.
    source_path : str
        Absolute path to the original file on disk.
    mime_type : str
        Detected MIME type (e.g. ``"application/pdf"``).
    page_count : int or None
        Number of pages for paginated formats (PDF, DOCX).
        ``None`` for single-page assets like images.
    is_ocr_result : bool
        ``True`` when the text was obtained through OCR rather than
        native text extraction.  Useful for downstream confidence scoring.
    metadata : dict
        Format-specific metadata extracted during parsing
        (author, title, creation date, etc.).
    raw_pages : list[str]
        Text content split by page.  This is consumed by the smart
        chunker to avoid merging text across page boundaries.
    """

    text: str
    source_path: str
    mime_type: str
    page_count: int | None = None
    is_ocr_result: bool = False
    metadata: dict = field(default_factory=dict)
    raw_pages: list[str] = field(default_factory=list)
    word_bboxes: list[list[dict]] = field(default_factory=list)


# ── Abstract Base Parser ─────────────────────────────────────────────────────

class BaseDocumentParser(ABC):
    """Abstract contract for all document parsers.

    Every concrete parser (PDF, DOCX, Image …) **must** implement the
    :meth:`parse` coroutine.  The Factory selects the right subclass
    based on the file's MIME type and calls this single method.

    Design notes
    ------------
    * The method is ``async`` so that CPU-heavy work (like OCR) can be
      off-loaded to a thread pool via :func:`asyncio.to_thread` without
      blocking the event loop.
    * ``max_pages`` lets callers cap how many pages are read — critical
      for large PDFs where reading all 300 pages would waste both time
      and LLM context window tokens.
    """

    @abstractmethod
    async def parse(
        self,
        file_path: Path,
        max_pages: int | None = None,
    ) -> ParsedDocument:
        """Parse the file at *file_path* and return a :class:`ParsedDocument`.

        Parameters
        ----------
        file_path : Path
            Absolute path to the file to parse.
        max_pages : int or None
            Maximum number of pages to extract.  ``None`` means *all*.
            Ignored by formats that have no concept of pages (images).

        Returns
        -------
        ParsedDocument
            A frozen dataclass containing the extracted text, metadata,
            and per-page text slices.

        Raises
        ------
        FileNotFoundError
            If *file_path* does not exist.
        ValueError
            If the file is empty or unreadable.
        """
        ...
