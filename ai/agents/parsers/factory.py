"""
Document Parser Factory

Selects the correct parser for a given file based on its MIME type.
Uses the ``filetype`` library to detect the format from file-header
magic bytes — much more reliable than guessing from the extension.

This is a classic *Factory Pattern* implementation (SOLID — Open/Closed
Principle): adding support for a new format means registering one
new entry in ``_REGISTRY``; no existing code needs to change.

Usage
-----
>>> from agents.parsers.factory import DocumentParserFactory
>>> parser = DocumentParserFactory.create(Path("invoice.pdf"))
>>> doc = await parser.parse(Path("invoice.pdf"))
"""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import TYPE_CHECKING

import filetype

if TYPE_CHECKING:
    from agents.parsers.base import BaseDocumentParser


# ── Custom Exceptions ────────────────────────────────────────────────────────

class UnsupportedFormatError(Exception):
    """Raised when no parser is registered for the file's MIME type."""


# ── MIME Detection ────────────────────────────────────────────────────────────

def detect_mime_type(file_path: Path) -> str:
    """Detect the MIME type of a file using magic-byte inspection.

    Falls back to extension-based guessing when magic bytes are
    inconclusive (e.g. for ``.docx`` files which are ZIP-wrapped XML).

    Parameters
    ----------
    file_path : Path
        Path to the file to inspect.

    Returns
    -------
    str
        A MIME type string such as ``"application/pdf"`` or
        ``"image/png"``.

    Raises
    ------
    FileNotFoundError
        If *file_path* does not exist.
    ValueError
        If the MIME type cannot be determined by any method.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # 1) Try magic-byte detection (most reliable)
    kind = filetype.guess(str(file_path))
    if kind is not None:
        return kind.mime

    # 2) Fallback: extension-based guess (needed for .docx, .txt, etc.)
    mime, _ = mimetypes.guess_type(str(file_path))
    if mime is not None:
        return mime

    raise ValueError(
        f"Cannot determine MIME type for '{file_path.name}'. "
        "The file may be empty or in an unrecognised format."
    )


# ── Factory ──────────────────────────────────────────────────────────────────

class DocumentParserFactory:
    """Create the right parser for a given file path.

    The factory inspects the file's MIME type and looks it up in an
    internal registry that maps MIME strings to concrete parser classes.

    The registry is populated lazily (imports happen inside
    :meth:`create`) to avoid circular-import issues and to keep
    start-up fast.

    Class Methods
    -------------
    create(file_path)
        Return a parser instance suitable for *file_path*.
    supported_types()
        Return the set of MIME types that have a registered parser.
    """

    # Lazy-loaded to avoid circular imports.  Populated on first call
    # to ``create()`` or ``supported_types()``.
    _REGISTRY: dict[str, type[BaseDocumentParser]] | None = None

    @classmethod
    def _ensure_registry(cls) -> dict[str, type[BaseDocumentParser]]:
        """Build the MIME → parser mapping on first use."""
        if cls._REGISTRY is None:
            from agents.parsers.pdf_parser import PDFParser
            from agents.parsers.docx_parser import DocxParser
            from agents.parsers.image_parser import ImageParser

            cls._REGISTRY = {
                # PDF
                "application/pdf": PDFParser,
                # Word (OOXML)
                "application/vnd.openxmlformats-officedocument"
                ".wordprocessingml.document": DocxParser,
                # Images
                "image/png": ImageParser,
                "image/jpeg": ImageParser,
            }
        return cls._REGISTRY

    @classmethod
    def create(cls, file_path: Path) -> BaseDocumentParser:
        """Return a parser for *file_path* based on its MIME type.

        Parameters
        ----------
        file_path : Path
            The document to be parsed.

        Returns
        -------
        BaseDocumentParser
            A ready-to-use parser instance.

        Raises
        ------
        FileNotFoundError
            If *file_path* does not exist.
        UnsupportedFormatError
            If no parser is registered for the detected MIME type.
        """
        mime = detect_mime_type(file_path)
        registry = cls._ensure_registry()

        parser_cls = registry.get(mime)
        if parser_cls is None:
            supported = ", ".join(sorted(registry.keys()))
            raise UnsupportedFormatError(
                f"No parser registered for MIME type '{mime}' "
                f"(file: {file_path.name}).  "
                f"Supported types: {supported}"
            )
        return parser_cls()

    @classmethod
    def supported_types(cls) -> set[str]:
        """Return every MIME type that has a registered parser."""
        return set(cls._ensure_registry().keys())
