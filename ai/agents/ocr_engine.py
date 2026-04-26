"""
Asynchronous OCR Engine — Strategy Pattern

Provides a high-accuracy Tesseract OCR backend with advanced image
preprocessing to maximise character recognition precision on scanned
documents, faxes, and photographs of text.

Architecture
------------
* **Strategy Pattern**: :class:`OCREngine` is the abstract interface;
  :class:`TesseractOCREngine` is the concrete strategy.  Swapping to
  PaddleOCR or EasyOCR requires only a new subclass — zero changes to
  callers.
* **Async-safe**: all CPU-heavy image processing and OCR inference run
  inside :func:`asyncio.to_thread`, keeping the event loop free.
* **Preprocessing pipeline** (key to accuracy):
  1. Grayscale conversion
  2. DPI normalisation (upscale to 300 DPI if lower)
  3. Contrast enhancement (CLAHE-like via Pillow)
  4. Sharpening
  5. Adaptive binarisation (Otsu-style threshold)
  6. Noise removal (median filter)

Configuration
-------------
Set these in ``.env`` (all optional — sensible defaults are used):

    TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe
    OCR_LANGUAGES=eng+ron
    OCR_DPI=300
    OCR_PSM=3
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)

# ── Constants / Defaults ─────────────────────────────────────────────────────

_DEFAULT_LANGUAGES: str = "eng+ron"
_TARGET_DPI: int = 300
_MIN_DPI_THRESHOLD: int = 200  # below this we upscale

# Tesseract Page Segmentation Modes (PSM):
#   3 = Fully automatic page segmentation (default, best for full pages)
#   6 = Assume a single uniform block of text
#  11 = Sparse text — find as much text as possible in no particular order
_DEFAULT_PSM: int = 3

# Tesseract OEM (OCR Engine Mode):
#   1 = LSTM neural net only (most accurate for modern Tesseract 4/5)
_DEFAULT_OEM: int = 1


# ── Image Preprocessing Pipeline ────────────────────────────────────────────

class ImagePreprocessor:
    """Multi-step image preprocessing to maximise OCR accuracy.

    Each method returns a new :class:`PIL.Image.Image`, leaving the
    original untouched (immutability).

    The full pipeline is executed by :meth:`prepare`, which chains
    all steps in the optimal order.
    """

    def __init__(self, target_dpi: int = _TARGET_DPI) -> None:
        self._target_dpi = target_dpi

    def prepare(self, image: Image.Image) -> Image.Image:
        """Run the full preprocessing pipeline.

        Parameters
        ----------
        image : Image.Image
            Input image (any mode: RGB, RGBA, L, P, …).

        Returns
        -------
        Image.Image
            Preprocessed grayscale image optimised for OCR.
        """
        img = self._to_grayscale(image)
        img = self._normalise_dpi(img)
        img = self._enhance_contrast(img)
        img = self._sharpen(img)
        img = self._binarise(img)
        img = self._denoise(img)
        return img

    # ── Individual Steps ──────────────────────────────────────────────────

    @staticmethod
    def _to_grayscale(img: Image.Image) -> Image.Image:
        """Convert to 8-bit grayscale (mode 'L').

        Grayscale reduces noise from colour channels and is the
        expected input for most OCR engines.
        """
        return img.convert("L")

    def _normalise_dpi(self, img: Image.Image) -> Image.Image:
        """Upscale low-resolution images to the target DPI.

        Tesseract accuracy drops sharply below 200 DPI.  If the image
        DPI is below ``_MIN_DPI_THRESHOLD`` (or unknown), we resize
        proportionally to reach ``_TARGET_DPI``.
        """
        dpi_info = img.info.get("dpi", (72, 72))
        current_dpi = max(dpi_info) if isinstance(dpi_info, (tuple, list)) else dpi_info

        if current_dpi >= _MIN_DPI_THRESHOLD:
            return img

        scale_factor = self._target_dpi / current_dpi
        new_size = (
            int(img.width * scale_factor),
            int(img.height * scale_factor),
        )
        logger.debug(
            "Upscaling from %d DPI to %d DPI (factor %.2f)",
            current_dpi, self._target_dpi, scale_factor,
        )
        return img.resize(new_size, Image.Resampling.LANCZOS)

    @staticmethod
    def _enhance_contrast(img: Image.Image) -> Image.Image:
        """Boost contrast to make text stand out from the background.

        A factor of 1.8 is aggressive but effective on washed-out
        scans and fax copies.
        """
        enhancer = ImageEnhance.Contrast(img)
        return enhancer.enhance(1.8)

    @staticmethod
    def _sharpen(img: Image.Image) -> Image.Image:
        """Sharpen edges so character boundaries are crisp.

        Uses Pillow's ``SHARPEN`` kernel — a lightweight 3×3
        convolution that doesn't introduce ringing artefacts.
        """
        return img.filter(ImageFilter.SHARPEN)

    @staticmethod
    def _binarise(img: Image.Image) -> Image.Image:
        """Convert to pure black-and-white using Otsu-style threshold.

        We compute the optimal threshold by analysing the histogram
        of the grayscale image (Otsu's method approximation) and
        apply a hard cutoff.  This eliminates background gradients
        and shadow artefacts.
        """
        # Simple Otsu approximation via histogram analysis
        histogram = img.histogram()
        total_pixels = img.width * img.height

        # Weighted mean calculation for threshold
        cumulative_sum = 0
        cumulative_weight = 0
        max_variance = 0
        threshold = 128  # default fallback

        total_sum = sum(i * histogram[i] for i in range(256))

        for t in range(256):
            cumulative_weight += histogram[t]
            if cumulative_weight == 0:
                continue

            background_weight = total_pixels - cumulative_weight
            if background_weight == 0:
                break

            cumulative_sum += t * histogram[t]

            mean_foreground = cumulative_sum / cumulative_weight
            mean_background = (
                (total_sum - cumulative_sum) / background_weight
            )

            variance = (
                cumulative_weight
                * background_weight
                * (mean_foreground - mean_background) ** 2
            )

            if variance > max_variance:
                max_variance = variance
                threshold = t

        return img.point(lambda p: 255 if p > threshold else 0, mode="L")

    @staticmethod
    def _denoise(img: Image.Image) -> Image.Image:
        """Remove salt-and-pepper noise with a median filter.

        Kernel size 3 is the sweet spot: removes speckle noise without
        eroding thin character strokes.
        """
        return img.filter(ImageFilter.MedianFilter(size=3))


# ── Abstract OCR Engine ──────────────────────────────────────────────────────

class OCREngine(ABC):
    """Abstract interface for OCR engines (Strategy Pattern).

    Concrete implementations must provide :meth:`extract_text` and
    :meth:`extract_text_from_path`.
    """

    @abstractmethod
    async def extract_text(
        self,
        image: Image.Image,
        lang: str | None = None,
    ) -> str:
        """Extract text from an in-memory PIL image.

        Parameters
        ----------
        image : Image.Image
            The image to OCR.
        lang : str or None
            Tesseract language codes (e.g. ``"eng+ron"``).
            ``None`` uses the engine's default.

        Returns
        -------
        str
            Extracted text (may be empty if nothing was recognised).
        """
        ...

    @abstractmethod
    async def extract_text_from_path(
        self,
        image_path: Path,
        lang: str | None = None,
    ) -> str:
        """Extract text from an image file on disk.

        Parameters
        ----------
        image_path : Path
            Path to a PNG, JPG, TIFF, or BMP file.
        lang : str or None
            Language codes.

        Returns
        -------
        str
        """
        ...


# ── Tesseract Implementation ────────────────────────────────────────────────

class TesseractOCREngine(OCREngine):
    """High-accuracy Tesseract OCR with advanced image preprocessing.

    This engine applies a 6-step preprocessing pipeline before
    invoking Tesseract, which dramatically improves accuracy on:
    * Low-resolution scans (< 200 DPI)
    * Faded / low-contrast documents
    * Noisy fax copies
    * Photographs of documents (slight skew, shadows)

    All CPU-intensive work runs on a background thread via
    :func:`asyncio.to_thread`.

    Parameters
    ----------
    languages : str
        Tesseract language codes, e.g. ``"eng+ron"``.
    tesseract_cmd : str or None
        Path to the Tesseract binary.  ``None`` reads from
        ``TESSERACT_CMD`` env var or uses the system default.
    psm : int
        Page Segmentation Mode (default 3 = fully automatic).
    oem : int
        OCR Engine Mode (default 1 = LSTM neural net).
    preprocessor : ImagePreprocessor or None
        Custom preprocessor.  ``None`` uses the default pipeline.
    """

    def __init__(
        self,
        languages: str | None = None,
        tesseract_cmd: str | None = None,
        psm: int | None = None,
        oem: int | None = None,
        preprocessor: ImagePreprocessor | None = None,
    ) -> None:
        import pytesseract

        self._languages = (
            languages
            or os.getenv("OCR_LANGUAGES", _DEFAULT_LANGUAGES)
        )
        self._psm = psm or int(os.getenv("OCR_PSM", str(_DEFAULT_PSM)))
        self._oem = oem or int(os.getenv("OCR_OEM", str(_DEFAULT_OEM)))
        self._preprocessor = preprocessor or ImagePreprocessor()

        # Configure Tesseract binary path
        cmd = tesseract_cmd or os.getenv("TESSERACT_CMD")
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd

        logger.info(
            "TesseractOCREngine initialised: lang=%s, psm=%d, oem=%d",
            self._languages,
            self._psm,
            self._oem,
        )

    def _build_config(self) -> str:
        """Build the Tesseract ``--oem`` / ``--psm`` config string."""
        return f"--oem {self._oem} --psm {self._psm}"

    def _sync_ocr(self, image: Image.Image, lang: str) -> str:
        """Run preprocessing + Tesseract synchronously (for to_thread)."""
        import pytesseract

        t0 = time.perf_counter()

        # Preprocess for maximum accuracy
        processed = self._preprocessor.prepare(image)

        t_preprocess = time.perf_counter() - t0

        # Run Tesseract
        text = pytesseract.image_to_string(
            processed,
            lang=lang,
            config=self._build_config(),
        ).strip()

        t_total = time.perf_counter() - t0

        logger.info(
            "OCR complete: %d chars in %.1fms (preprocess: %.1fms, "
            "inference: %.1fms)",
            len(text),
            t_total * 1000,
            t_preprocess * 1000,
            (t_total - t_preprocess) * 1000,
        )

        return text

    async def extract_text(
        self,
        image: Image.Image,
        lang: str | None = None,
    ) -> str:
        """OCR an in-memory image with full preprocessing.

        Runs on a background thread to avoid blocking the event loop.
        """
        effective_lang = lang or self._languages
        return await asyncio.to_thread(self._sync_ocr, image, effective_lang)

    async def extract_text_from_path(
        self,
        image_path: Path,
        lang: str | None = None,
    ) -> str:
        """Load an image from disk and OCR it.

        Parameters
        ----------
        image_path : Path
            Path to the image file.
        lang : str or None
            Language override.

        Returns
        -------
        str
            Extracted text.

        Raises
        ------
        FileNotFoundError
            If *image_path* does not exist.
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        image = Image.open(image_path)
        return await self.extract_text(image, lang)


# ── Factory ──────────────────────────────────────────────────────────────────

class OCREngineFactory:
    """Create the configured OCR engine.

    Reads ``OCR_ENGINE`` from ``.env`` (default: ``"tesseract"``).
    Currently only Tesseract is implemented; the factory is here so
    that future engines (PaddleOCR, EasyOCR) can be added without
    touching existing code.

    Usage
    -----
    >>> engine = OCREngineFactory.create()
    >>> text = await engine.extract_text(some_image)
    """

    @staticmethod
    def create(engine_name: str | None = None) -> OCREngine:
        """Return an OCR engine instance.

        Parameters
        ----------
        engine_name : str or None
            ``"tesseract"`` (default) or a future engine name.

        Raises
        ------
        ValueError
            If the engine name is not recognised.
        """
        name = (engine_name or os.getenv("OCR_ENGINE", "tesseract")).lower()

        if name == "tesseract":
            return TesseractOCREngine()

        raise ValueError(
            f"Unknown OCR engine: '{name}'.  "
            f"Supported engines: tesseract"
        )
