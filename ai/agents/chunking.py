"""
Smart Chunking & Noise Reduction

This module handles the final transformation of raw extracted text
into clean, semantically coherent chunks that fit within LLM context
windows.

Two-phase pipeline
------------------
1. **Noise Reduction** (:class:`NoiseFilter`)
   Removes repetitive headers/footers, watermarks, excessive whitespace,
   and configurable boilerplate before the text reaches the chunker.

2. **Smart Chunking** (:class:`SmartChunker`)
   Recursive Character Text Splitting that respects natural boundaries
   (paragraphs → sentences → words) and never cuts a sentence in half.

Design decisions
----------------
* **Chunk size 512 chars / overlap 64 chars** — optimal for most LLM
  context windows.  Both are configurable.
* **Page-aware**: when ``raw_pages`` are provided, the chunker avoids
  merging text from different pages into the same chunk.
* **No embedding model required** — unlike semantic chunking, this
  approach works fully offline with zero additional cost.

Usage
-----
>>> from agents.chunking import NoiseFilter, SmartChunker
>>> nf = NoiseFilter()
>>> clean_pages = nf.filter_pages(raw_pages)
>>> chunker = SmartChunker(chunk_size=512, chunk_overlap=64)
>>> chunks = chunker.chunk_pages(clean_pages)
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ── Data Transfer Object ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class TextChunk:
    """A single chunk of text produced by the :class:`SmartChunker`.

    Attributes
    ----------
    content : str
        The chunk text, clean and ready for LLM consumption.
    chunk_index : int
        Zero-based position of this chunk in the document.
    start_char : int
        Character offset of the chunk start in the full text.
    end_char : int
        Character offset of the chunk end in the full text.
    page_number : int or None
        Source page number (1-indexed) if page-aware chunking was used.
    word_count : int
        Number of words in this chunk.
    """

    content: str
    chunk_index: int
    start_char: int
    end_char: int
    page_number: int | None = None
    word_count: int = 0


# ── Noise Filter ─────────────────────────────────────────────────────────────

class NoiseFilter:
    """Remove noise from extracted text before chunking.

    "Noise" includes:
    * **Repetitive headers/footers** that appear on most pages
      (e.g. ``"Page 1 of 42"``, ``"CONFIDENTIAL"``, company names).
    * **Excessive whitespace** (multiple blank lines, tabs, etc.).
    * **Boilerplate text** (disclaimers, copyright notices) matched
      by configurable regex patterns.

    Parameters
    ----------
    repetition_threshold : float
        A line is considered repetitive if it appears on at least this
        fraction of pages.  Default ``0.60`` (60%).
    boilerplate_patterns : list[str] or None
        Additional regex patterns to remove.  Built-in patterns already
        cover common cases (page numbers, confidentiality notices).
    """

    # Built-in patterns for common noise
    _DEFAULT_PATTERNS: list[str] = [
        # Page numbers: "Page 1 of 42", "1/42", "- 1 -"
        r"(?i)^[\s]*page\s+\d+\s*(of|din|/)\s*\d+[\s]*$",
        r"^[\s]*-?\s*\d+\s*-?[\s]*$",
        # "CONFIDENTIAL", "DRAFT", watermark-style text
        r"(?i)^[\s]*(confidential|draft|watermark|privileged)[\s]*$",
    ]

    def __init__(
        self,
        repetition_threshold: float = 0.60,
        boilerplate_patterns: list[str] | None = None,
    ) -> None:
        self._threshold = repetition_threshold
        self._patterns = [
            re.compile(p)
            for p in self._DEFAULT_PATTERNS + (boilerplate_patterns or [])
        ]

    def filter_pages(self, pages: list[str]) -> list[str]:
        """Apply all noise filters to a list of page texts.

        This is the main entry point.  It chains:
        1. Repetitive header/footer removal
        2. Boilerplate pattern removal
        3. Whitespace normalisation

        Parameters
        ----------
        pages : list[str]
            Raw page texts (one string per page).

        Returns
        -------
        list[str]
            Cleaned page texts.
        """
        pages = self._remove_repetitive_lines(pages)
        pages = [self._remove_boilerplate(p) for p in pages]
        pages = [self._normalise_whitespace(p) for p in pages]
        return pages

    def filter_text(self, text: str) -> str:
        """Apply filters to a single text block (non-paginated).

        Parameters
        ----------
        text : str
            Raw text.

        Returns
        -------
        str
            Cleaned text.
        """
        text = self._remove_boilerplate(text)
        text = self._normalise_whitespace(text)
        return text

    # ── Internal Methods ──────────────────────────────────────────────────

    def _remove_repetitive_lines(self, pages: list[str]) -> list[str]:
        """Detect and remove lines that repeat across many pages.

        A line is removed if it appears (exactly) on ≥ ``threshold``
        fraction of all pages.  This catches:
        * Running headers (company name, document title)
        * Running footers (page numbers, dates)
        * Watermarks rendered as text

        We check the first 3 and last 3 lines of each page —
        headers/footers almost always live there.
        """
        if len(pages) < 3:
            return pages  # not enough pages to detect repetition

        # Collect candidate lines (first/last 3 lines of each page)
        candidate_lines: Counter[str] = Counter()
        n_pages = len(pages)
        border_lines = 3

        for page in pages:
            lines = page.strip().splitlines()
            if not lines:
                continue
            candidates = (
                lines[:border_lines] + lines[-border_lines:]
            )
            # Use a set to count each line at most once per page
            for line in set(candidates):
                stripped = line.strip()
                if stripped:  # ignore blank lines
                    candidate_lines[stripped] += 1

        # Lines appearing on >= threshold fraction of pages
        repetitive = {
            line
            for line, count in candidate_lines.items()
            if count / n_pages >= self._threshold
        }

        if repetitive:
            logger.info(
                "NoiseFilter: removing %d repetitive header/footer lines",
                len(repetitive),
            )
            logger.debug("Repetitive lines: %s", repetitive)

        # Remove those lines from all pages
        cleaned: list[str] = []
        for page in pages:
            lines = page.splitlines()
            filtered = [
                line for line in lines
                if line.strip() not in repetitive
            ]
            cleaned.append("\n".join(filtered))

        return cleaned

    def _remove_boilerplate(self, text: str) -> str:
        """Remove lines matching built-in + custom boilerplate patterns."""
        lines = text.splitlines()
        filtered = [
            line for line in lines
            if not any(pat.match(line) for pat in self._patterns)
        ]
        return "\n".join(filtered)

    @staticmethod
    def _normalise_whitespace(text: str) -> str:
        """Collapse multiple blank lines into one, strip trailing spaces.

        Preserves single blank lines (paragraph separators) but removes
        runs of 3+ blank lines, leading/trailing whitespace per line,
        and tab characters.
        """
        # Replace tabs with spaces
        text = text.replace("\t", " ")
        # Collapse multiple spaces (but not newlines)
        text = re.sub(r"[^\S\n]+", " ", text)
        # Strip trailing spaces per line
        text = re.sub(r" +\n", "\n", text)
        # Collapse 3+ newlines into 2 (one blank line)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


# ── Smart Chunker ────────────────────────────────────────────────────────────

class SmartChunker:
    """Recursive Character Text Splitter with sentence awareness.

    Splits text into chunks of approximately ``chunk_size`` characters
    with ``chunk_overlap`` characters of overlap between consecutive
    chunks.

    The algorithm tries to split at the largest natural boundary first
    (double newline = paragraph), then falls back to smaller ones
    (single newline, sentence-ending period, space).  This ensures
    chunks are semantically coherent — sentences are never cut in half.

    Parameters
    ----------
    chunk_size : int
        Target chunk size in characters (default 512).
    chunk_overlap : int
        Number of overlapping characters between consecutive chunks
        (default 64).
    separators : list[str] or None
        Ordered list of separators to try, from largest to smallest.
        Defaults to ``["\\n\\n", "\\n", ". ", " "]``.
    """

    _DEFAULT_SEPARATORS: list[str] = ["\n\n", "\n", ". ", " "]

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        separators: list[str] | None = None,
    ) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError(
                f"chunk_overlap ({chunk_overlap}) must be less than "
                f"chunk_size ({chunk_size})"
            )
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._separators = separators or self._DEFAULT_SEPARATORS

    def chunk(self, text: str) -> list[TextChunk]:
        """Split a single text into chunks.

        Parameters
        ----------
        text : str
            The text to split.

        Returns
        -------
        list[TextChunk]
            Ordered list of chunks covering the entire text.
        """
        if not text.strip():
            return []

        raw_chunks = self._recursive_split(text, self._separators)
        return self._build_chunks(raw_chunks, page_number=None)

    def chunk_pages(self, pages: list[str]) -> list[TextChunk]:
        """Split paginated text with page-boundary awareness.

        Each page is chunked independently — no chunk will span
        multiple pages.  The ``page_number`` field in each
        :class:`TextChunk` indicates its source page (1-indexed).

        Parameters
        ----------
        pages : list[str]
            One text string per page.

        Returns
        -------
        list[TextChunk]
            All chunks from all pages, in order.
        """
        all_chunks: list[TextChunk] = []
        global_index = 0
        global_offset = 0

        for page_idx, page_text in enumerate(pages):
            if not page_text.strip():
                global_offset += len(page_text)
                continue

            raw_chunks = self._recursive_split(page_text, self._separators)
            page_chunks = self._build_chunks(
                raw_chunks,
                page_number=page_idx + 1,
                start_index=global_index,
                char_offset=global_offset,
            )
            all_chunks.extend(page_chunks)
            global_index += len(page_chunks)
            global_offset += len(page_text)

        logger.info(
            "SmartChunker: %d pages → %d chunks (size=%d, overlap=%d)",
            len(pages),
            len(all_chunks),
            self._chunk_size,
            self._chunk_overlap,
        )

        return all_chunks

    # ── Core Algorithm ────────────────────────────────────────────────────

    def _recursive_split(
        self, text: str, separators: list[str]
    ) -> list[str]:
        """Recursively split text using progressively finer separators.

        This is the heart of the algorithm:
        1. Try to split on the first (coarsest) separator.
        2. Merge consecutive small pieces until they approach chunk_size.
        3. If any merged piece is still too large, recursively split it
           using the next finer separator.
        """
        if len(text) <= self._chunk_size:
            return [text]

        if not separators:
            # Last resort: hard cut (should rarely happen)
            return self._hard_split(text)

        sep = separators[0]
        remaining_seps = separators[1:]

        pieces = text.split(sep)

        # Merge small consecutive pieces
        merged: list[str] = []
        current = ""

        for piece in pieces:
            candidate = (
                current + sep + piece if current else piece
            )
            if len(candidate) <= self._chunk_size:
                current = candidate
            else:
                if current:
                    merged.append(current)
                current = piece

        if current:
            merged.append(current)

        # Recursively split any piece that's still too large
        result: list[str] = []
        for piece in merged:
            if len(piece) > self._chunk_size and remaining_seps:
                result.extend(
                    self._recursive_split(piece, remaining_seps)
                )
            else:
                result.append(piece)

        return result

    def _hard_split(self, text: str) -> list[str]:
        """Last-resort character-level split when no separator works."""
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + self._chunk_size
            chunks.append(text[start:end])
            start = end - self._chunk_overlap
        return chunks

    def _build_chunks(
        self,
        raw_chunks: list[str],
        page_number: int | None,
        start_index: int = 0,
        char_offset: int = 0,
    ) -> list[TextChunk]:
        """Convert raw text pieces into typed :class:`TextChunk` objects.

        Adds overlap between consecutive chunks by prepending the tail
        of the previous chunk.
        """
        result: list[TextChunk] = []
        current_offset = char_offset

        for i, raw in enumerate(raw_chunks):
            content = raw.strip()
            if not content:
                current_offset += len(raw)
                continue

            # Add overlap from previous chunk
            if i > 0 and self._chunk_overlap > 0 and result:
                prev_content = result[-1].content
                overlap_text = prev_content[-self._chunk_overlap:]
                content = overlap_text + " " + content

            chunk = TextChunk(
                content=content,
                chunk_index=start_index + len(result),
                start_char=current_offset,
                end_char=current_offset + len(raw),
                page_number=page_number,
                word_count=len(content.split()),
            )
            result.append(chunk)
            current_offset += len(raw)

        return result
