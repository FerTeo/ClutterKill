"""
File Metadata Extraction Module

Extracts technical and semantic metadata from files to give the
LLM-based decision agent richer context for classification.

Metadata sources
----------------
* **OS-level**: file size, creation date, modification date (``os.stat``).
* **Format-specific**: author, title, etc. — already captured by each
  parser and embedded in :attr:`ParsedDocument.metadata`.
* **Derived**: word count, estimated reading time, language hint.

The :func:`extract_metadata` function combines OS-level stats with
the parser-provided metadata dict into a single, typed
:class:`FileMetadata` dataclass.

Usage
-----
>>> from agents.metadata import extract_metadata
>>> meta = extract_metadata(Path("invoice.pdf"), parsed_doc.metadata, parsed_doc.text)
>>> print(meta.file_size_human, meta.author, meta.word_count)
'1.4 MB' 'Acme Corp' 3842
"""

from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Data Transfer Object ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class FileMetadata:
    """Unified metadata container for any document.

    Combines OS-level file information with format-specific properties
    extracted during parsing.

    Attributes
    ----------
    file_name : str
        Base name of the file (e.g. ``"invoice.pdf"``).
    file_size_bytes : int
        Size in bytes.
    file_size_human : str
        Human-readable size (e.g. ``"2.3 MB"``).
    mime_type : str
        Detected MIME type.
    created_at : datetime or None
        File creation timestamp (OS-level).
    modified_at : datetime or None
        Last modification timestamp (OS-level).
    author : str or None
        Document author (from PDF info / DOCX core properties).
    title : str or None
        Document title (from PDF info / DOCX core properties).
    page_count : int or None
        Number of pages (if applicable).
    word_count : int
        Approximate word count derived from the extracted text.
    char_count : int
        Character count of the extracted text.
    estimated_reading_time_min : float
        Estimated reading time in minutes (based on 250 words/min).
    """

    file_name: str
    file_size_bytes: int
    file_size_human: str
    mime_type: str
    created_at: datetime | None
    modified_at: datetime | None
    author: str | None
    title: str | None
    page_count: int | None
    word_count: int
    char_count: int
    estimated_reading_time_min: float


# ── Helpers ──────────────────────────────────────────────────────────────────

_SIZE_UNITS = ["B", "KB", "MB", "GB", "TB"]


def _human_readable_size(size_bytes: int) -> str:
    """Convert bytes to a human-readable string.

    Examples
    --------
    >>> _human_readable_size(0)
    '0 B'
    >>> _human_readable_size(1536)
    '1.5 KB'
    >>> _human_readable_size(2_500_000)
    '2.4 MB'
    """
    if size_bytes == 0:
        return "0 B"

    exponent = int(math.log(size_bytes, 1024))
    exponent = min(exponent, len(_SIZE_UNITS) - 1)
    value = size_bytes / (1024 ** exponent)
    return f"{value:.1f} {_SIZE_UNITS[exponent]}"


def _safe_datetime(timestamp: float | None) -> datetime | None:
    """Convert a POSIX timestamp to a timezone-aware ``datetime``.

    Returns ``None`` if the timestamp is missing or invalid.
    """
    if timestamp is None:
        return None
    try:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    except (OSError, ValueError, OverflowError):
        return None


def _count_words(text: str) -> int:
    """Count words using simple whitespace splitting.

    This is intentionally naive — we don't need NLP-level tokenisation,
    just a rough estimate for context and reading-time calculation.
    """
    return len(text.split())


# ── Main API ─────────────────────────────────────────────────────────────────

def extract_metadata(
    file_path: Path,
    parser_metadata: dict | None = None,
    extracted_text: str = "",
    mime_type: str = "application/octet-stream",
    page_count: int | None = None,
) -> FileMetadata:
    """Build a :class:`FileMetadata` by combining OS stats with parser data.

    Parameters
    ----------
    file_path : Path
        Path to the original file on disk.
    parser_metadata : dict or None
        Metadata dict produced by the parser (may contain ``"author"``,
        ``"title"``, ``"created"``, etc.).
    extracted_text : str
        The full text extracted from the document.  Used to compute
        word count and reading time.
    mime_type : str
        MIME type as detected during parsing.
    page_count : int or None
        Number of pages (passed through from the parser).

    Returns
    -------
    FileMetadata
        Frozen dataclass with all metadata fields populated.
    """
    file_path = Path(file_path)
    meta = parser_metadata or {}

    # OS-level stats
    try:
        stat = file_path.stat()
        size_bytes = stat.st_size
        created = _safe_datetime(stat.st_ctime)
        modified = _safe_datetime(stat.st_mtime)
    except OSError:
        logger.warning("Could not stat file '%s'", file_path)
        size_bytes = 0
        created = None
        modified = None

    # Derived metrics
    word_count = _count_words(extracted_text)
    char_count = len(extracted_text)
    reading_time = word_count / 250.0 if word_count > 0 else 0.0

    # Format-specific fields (normalise keys)
    author = meta.get("author") or meta.get("Author")
    title = meta.get("title") or meta.get("Title")

    result = FileMetadata(
        file_name=file_path.name,
        file_size_bytes=size_bytes,
        file_size_human=_human_readable_size(size_bytes),
        mime_type=mime_type,
        created_at=created,
        modified_at=modified,
        author=str(author) if author else None,
        title=str(title) if title else None,
        page_count=page_count,
        word_count=word_count,
        char_count=char_count,
        estimated_reading_time_min=round(reading_time, 1),
    )

    logger.info(
        "Metadata for '%s': %s, %d words, author='%s'",
        file_path.name,
        result.file_size_human,
        word_count,
        author or "N/A",
    )

    return result
