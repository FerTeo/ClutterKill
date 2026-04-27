"""
PDF Document Parser

Extracts text from PDF files using ``pdfplumber``, which provides
excellent layout-aware text extraction for digitally-generated PDFs
(reports, invoices, contracts, etc.).

For scanned/image-only PDFs the parser automatically falls back to
OCR: each page is rendered as an image and processed through the
configured :class:`~agents.ocr_engine.OCREngine`.

Key design decisions
--------------------
* **Page-level granularity**: text is extracted page-by-page and stored
  in ``raw_pages`` so the downstream chunker can avoid merging content
  across page boundaries.
* **max_pages cap**: defaults to 10 (matching User Story #4) to keep
  LLM context windows manageable.  Fully configurable.
* **Async-ready**: the heavy I/O work runs inside
  :func:`asyncio.to_thread` so the event loop is never blocked.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import pdfplumber

from PIL import Image

from agents.ocr_engine import OCREngine, OCREngineFactory
from agents.parsers.base import BaseDocumentParser, ParsedDocument

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

_DEFAULT_MAX_PAGES: int = 10

# If more than this fraction of pages return empty text, the PDF is
# considered "image-only" and should be processed by OCR.
_IMAGE_ONLY_THRESHOLD: float = 0.80


# ── Helpers ──────────────────────────────────────────────────────────────────

def _extract_pdf_metadata(pdf: pdfplumber.PDF) -> dict:
    """Pull author, title, creator, and dates from the PDF info dict.

    ``pdfplumber`` exposes the raw PDF ``/Info`` dictionary, which may
    contain keys like ``/Author``, ``/Title``, ``/CreationDate``, etc.
    We normalise them into a clean Python ``dict``.
    """
    info: dict = pdf.metadata or {}
    return {
        "author": info.get("Author"),
        "title": info.get("Title"),
        "creator": info.get("Creator"),
        "producer": info.get("Producer"),
        "creation_date": info.get("CreationDate"),
        "modification_date": info.get("ModDate"),
    }


def _sync_extract(file_path: Path, max_pages: int | None) -> tuple[
    list[str], list[list[dict]], int, dict, bool
]:
    """Synchronous core — runs inside a worker thread.

    Returns
    -------
    (raw_pages, total_page_count, metadata, is_image_only)
    """
    raw_pages: list[str] = []
    word_bboxes: list[list[dict]] = []
    total_pages: int = 0
    metadata: dict = {}

    with pdfplumber.open(str(file_path)) as pdf:
        total_pages = len(pdf.pages)
        metadata = _extract_pdf_metadata(pdf)

        pages_to_read = pdf.pages
        if max_pages is not None:
            pages_to_read = pdf.pages[:max_pages]

        empty_count = 0
        for page in pages_to_read:
            text = (page.extract_text() or "").strip()
            raw_pages.append(text)
            
            # Extract bounding boxes
            words = page.extract_words()
            page_bboxes = []
            for w in words:
                page_bboxes.append({
                    "text": w["text"],
                    "x0": w["x0"],
                    "y0": w["top"],
                    "x1": w["x1"],
                    "y1": w["bottom"],
                })
            word_bboxes.append(page_bboxes)
            
            if not text:
                empty_count += 1

    # Determine if the PDF is "image-only"
    pages_read = len(raw_pages)
    is_image_only = (
        pages_read > 0
        and (empty_count / pages_read) >= _IMAGE_ONLY_THRESHOLD
    )

    return raw_pages, word_bboxes, total_pages, metadata, is_image_only


# ── Parser ───────────────────────────────────────────────────────────────────

class PDFParser(BaseDocumentParser):
    """Parse PDF files using ``pdfplumber`` for native text extraction.

    If the PDF is detected as image-only (scanned), the parser
    automatically falls back to OCR: each page is converted to an
    image and processed through the configured :class:`OCREngine`.

    Parameters
    ----------
    default_max_pages : int
        Fallback value for ``max_pages`` when the caller does not
        specify one.  Defaults to 10.
    ocr_engine : OCREngine or None
        Injected OCR engine for scanned-PDF fallback.  ``None``
        lazily creates a default :class:`TesseractOCREngine`.

    Examples
    --------
    >>> parser = PDFParser()
    >>> doc = await parser.parse(Path("report.pdf"), max_pages=5)
    >>> print(doc.page_count, len(doc.raw_pages))
    42 5
    """

    def __init__(
        self,
        default_max_pages: int = _DEFAULT_MAX_PAGES,
        ocr_engine: OCREngine | None = None,
    ) -> None:
        self._default_max_pages = default_max_pages
        self._ocr_engine = ocr_engine
        self._engine_initialised = ocr_engine is not None

    def _get_engine(self) -> OCREngine:
        """Lazy-initialise the OCR engine on first use."""
        if not self._engine_initialised:
            self._ocr_engine = OCREngineFactory.create()
            self._engine_initialised = True
        assert self._ocr_engine is not None
        return self._ocr_engine

    async def _ocr_pages(
        self, file_path: Path, max_pages: int
    ) -> tuple[list[str], list[list[dict]]]:
        """Render PDF pages as images and OCR each one.

        Uses ``pdfplumber``'s built-in page-to-image conversion
        (which wraps ``Wand`` / ``Pillow``) to produce a raster
        image for each page, then passes it to the OCR engine.

        Returns
        -------
        list[str]
            One text string per page.
        """
        engine = self._get_engine()
        ocr_pages: list[str] = []
        ocr_bboxes: list[list[dict]] = []

        def _render_page_images(
            fp: Path, n: int,
        ) -> list[Image.Image]:
            """Render up to *n* pages to PIL Images (sync)."""
            images: list[Image.Image] = []
            with pdfplumber.open(str(fp)) as pdf:
                for page in pdf.pages[:n]:
                    pil_img = page.to_image(resolution=300).original
                    images.append(pil_img)
            return images

        page_images = await asyncio.to_thread(
            _render_page_images, file_path, max_pages
        )

        for idx, img in enumerate(page_images):
            logger.info(
                "OCR fallback: processing page %d/%d of '%s'",
                idx + 1, len(page_images), file_path.name,
            )
            text, bboxes = await engine.extract_text(img)
            ocr_pages.append(text)
            ocr_bboxes.append(bboxes)

        return ocr_pages, ocr_bboxes

    async def parse(
        self,
        file_path: Path,
        max_pages: int | None = None,
    ) -> ParsedDocument:
        """Extract text from a PDF file.

        The extraction runs on a worker thread to keep the async event
        loop responsive.

        Parameters
        ----------
        file_path : Path
            Absolute path to the ``.pdf`` file.
        max_pages : int or None
            Cap on pages to read.  Falls back to
            ``self._default_max_pages`` if ``None``.

        Returns
        -------
        ParsedDocument
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        effective_max = max_pages or self._default_max_pages

        logger.info(
            "Parsing PDF '%s' (max_pages=%s)", file_path.name, effective_max
        )

        raw_pages, word_bboxes, total_pages, metadata, is_image_only = await asyncio.to_thread(
            _sync_extract, file_path, effective_max
        )

        used_ocr = False

        if is_image_only:
            logger.warning(
                "PDF '%s' detected as image-only (%d/%d pages empty). "
                "Triggering OCR fallback.",
                file_path.name,
                sum(1 for p in raw_pages if not p),
                len(raw_pages),
            )
            raw_pages, word_bboxes = await self._ocr_pages(file_path, effective_max)
            used_ocr = True

        full_text = "\n\n".join(page for page in raw_pages if page)

        logger.info(
            "PDF '%s': %d pages read, %d chars extracted, image_only=%s",
            file_path.name,
            len(raw_pages),
            len(full_text),
            is_image_only,
        )

        return ParsedDocument(
            text=full_text,
            source_path=str(file_path.resolve()),
            mime_type="application/pdf",
            page_count=total_pages,
            is_ocr_result=used_ocr,
            metadata=metadata,
            raw_pages=raw_pages,
            word_bboxes=word_bboxes,
        )
