"""
Image Document Parser

Extracts text from raster images (PNG, JPG, TIFF, BMP) by delegating
entirely to the :class:`~agents.ocr_engine.OCREngine`.

Unlike the PDF parser (which tries native text extraction first),
images **always** require OCR — there is no "selectable text" layer.

Design notes
------------
* The parser accepts an ``OCREngine`` via constructor injection
  (Dependency Inversion).  If none is provided, it lazily creates a
  default :class:`TesseractOCREngine`.
* Basic image metadata (dimensions, colour mode, format) is extracted
  from the Pillow ``Image.info`` and EXIF data.
* ``page_count`` is always ``1`` and ``raw_pages`` contains a single
  entry — the full OCR text.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from PIL import Image
from PIL.ExifTags import TAGS as EXIF_TAGS

from agents.ocr_engine import OCREngine, OCREngineFactory
from agents.parsers.base import BaseDocumentParser, ParsedDocument

logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _extract_image_metadata(image: Image.Image, file_path: Path) -> dict:
    """Extract technical metadata from a PIL Image.

    Pulls dimensions, colour mode, format, and any available EXIF
    tags (camera model, date taken, orientation, etc.).
    """
    metadata: dict = {
        "width": image.width,
        "height": image.height,
        "mode": image.mode,
        "format": image.format,
        "dpi": image.info.get("dpi"),
    }

    # EXIF data (mainly for JPEGs from cameras/scanners)
    exif_data = image.getexif()
    if exif_data:
        for tag_id, value in exif_data.items():
            tag_name = EXIF_TAGS.get(tag_id, str(tag_id))
            # Only keep common, serialisable tags
            if tag_name in (
                "DateTime",
                "DateTimeOriginal",
                "Make",
                "Model",
                "Software",
                "ImageDescription",
                "Orientation",
            ):
                metadata[f"exif_{tag_name}"] = str(value)

    return metadata


# ── Parser ───────────────────────────────────────────────────────────────────

class ImageParser(BaseDocumentParser):
    """Parse raster images (PNG, JPG, etc.) using OCR.

    This parser opens the image, extracts technical metadata, and
    delegates text extraction to the configured :class:`OCREngine`.

    Parameters
    ----------
    ocr_engine : OCREngine or None
        Injected OCR engine.  ``None`` lazily creates a default
        :class:`TesseractOCREngine`.

    Examples
    --------
    >>> parser = ImageParser()
    >>> doc = await parser.parse(Path("scanned_invoice.png"))
    >>> print(doc.is_ocr_result)
    True
    >>> print(doc.text[:80])
    'INVOICE No. 2024-0042  Date: 15/03/2024  ...'
    """

    def __init__(self, ocr_engine: OCREngine | None = None) -> None:
        self._ocr_engine = ocr_engine
        self._engine_initialised = ocr_engine is not None

    def _get_engine(self) -> OCREngine:
        """Lazy-initialise the OCR engine on first use."""
        if not self._engine_initialised:
            self._ocr_engine = OCREngineFactory.create()
            self._engine_initialised = True
        assert self._ocr_engine is not None
        return self._ocr_engine

    async def parse(
        self,
        file_path: Path,
        max_pages: int | None = None,  # ignored for images
    ) -> ParsedDocument:
        """Extract text from an image file via OCR.

        Parameters
        ----------
        file_path : Path
            Path to the image file (PNG, JPG, TIFF, BMP).
        max_pages : int or None
            Ignored — images are single-page by definition.

        Returns
        -------
        ParsedDocument
            With ``is_ocr_result=True`` and ``page_count=1``.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        logger.info("Parsing image '%s'", file_path.name)

        # Open image and extract metadata (sync but fast)
        image = await asyncio.to_thread(Image.open, file_path)
        # Force-load the pixel data while we're on the thread
        await asyncio.to_thread(image.load)

        metadata = _extract_image_metadata(image, file_path)

        # OCR — the engine handles preprocessing + thread offloading
        engine = self._get_engine()
        text, bboxes = await engine.extract_text(image)

        # Determine MIME type from Pillow format
        format_to_mime = {
            "PNG": "image/png",
            "JPEG": "image/jpeg",
            "TIFF": "image/tiff",
            "BMP": "image/bmp",
        }
        mime = format_to_mime.get(image.format or "", "image/unknown")

        logger.info(
            "Image '%s' (%dx%d): %d chars extracted via OCR",
            file_path.name,
            image.width,
            image.height,
            len(text),
        )

        return ParsedDocument(
            text=text,
            source_path=str(file_path.resolve()),
            mime_type=mime,
            page_count=1,
            is_ocr_result=True,
            metadata=metadata,
            raw_pages=[text],
            word_bboxes=[bboxes],
        )
