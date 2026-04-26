"""
Tests for the OCR Engine module.

Uses mock images and verifies that:
- The preprocessing pipeline runs correctly
- The async wrapper works
- The factory returns the right engine
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from PIL import Image

from agents.ocr_engine import (
    ImagePreprocessor,
    OCREngineFactory,
    TesseractOCREngine,
)


# ═══════════════════════════════════════════════════════════════════════════
#  ImagePreprocessor
# ═══════════════════════════════════════════════════════════════════════════

class TestImagePreprocessor:
    """Test the 6-step preprocessing pipeline."""

    def test_to_grayscale(self):
        img = Image.new("RGB", (100, 100), color="red")
        pp = ImagePreprocessor()
        result = pp._to_grayscale(img)
        assert result.mode == "L"

    def test_normalise_dpi_upscales_low_res(self):
        img = Image.new("L", (100, 100))
        img.info["dpi"] = (72, 72)
        pp = ImagePreprocessor(target_dpi=300)
        result = pp._normalise_dpi(img)
        # Should be larger
        assert result.width > 100
        assert result.height > 100

    def test_normalise_dpi_keeps_high_res(self):
        img = Image.new("L", (100, 100))
        img.info["dpi"] = (300, 300)
        pp = ImagePreprocessor(target_dpi=300)
        result = pp._normalise_dpi(img)
        assert result.width == 100

    def test_enhance_contrast_returns_same_size(self):
        img = Image.new("L", (50, 50), color=128)
        result = ImagePreprocessor._enhance_contrast(img)
        assert result.size == (50, 50)

    def test_binarise_produces_black_and_white(self):
        img = Image.new("L", (50, 50), color=128)
        result = ImagePreprocessor._binarise(img)
        pixels = list(result.getdata())
        # All pixels should be either 0 or 255
        assert all(p in (0, 255) for p in pixels)

    def test_full_pipeline_returns_image(self):
        img = Image.new("RGB", (200, 200), color="blue")
        pp = ImagePreprocessor()
        result = pp.prepare(img)
        assert isinstance(result, Image.Image)
        assert result.mode == "L"


# ═══════════════════════════════════════════════════════════════════════════
#  TesseractOCREngine
# ═══════════════════════════════════════════════════════════════════════════

class TestTesseractOCREngine:
    """Test the Tesseract engine with mocked pytesseract."""

    @pytest.mark.asyncio
    async def test_extract_text_calls_pytesseract(self):
        with patch("agents.ocr_engine.pytesseract") as mock_tess:
            mock_tess.image_to_string.return_value = "Hello World"

            engine = TesseractOCREngine(languages="eng")
            img = Image.new("RGB", (100, 50), color="white")
            result = await engine.extract_text(img)

            assert result == "Hello World"
            mock_tess.image_to_string.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_text_from_path(self, sample_text_image: Path):
        with patch("agents.ocr_engine.pytesseract") as mock_tess:
            mock_tess.image_to_string.return_value = "File OCR result"

            engine = TesseractOCREngine(languages="eng")
            result = await engine.extract_text_from_path(sample_text_image)

            assert result == "File OCR result"

    @pytest.mark.asyncio
    async def test_extract_text_from_path_not_found(self):
        with patch("agents.ocr_engine.pytesseract"):
            engine = TesseractOCREngine(languages="eng")
            with pytest.raises(FileNotFoundError):
                await engine.extract_text_from_path(Path("/nonexistent/file.png"))


# ═══════════════════════════════════════════════════════════════════════════
#  OCREngineFactory
# ═══════════════════════════════════════════════════════════════════════════

class TestOCREngineFactory:
    """Test the factory creates the right engine."""

    def test_create_tesseract(self):
        with patch("agents.ocr_engine.pytesseract"):
            engine = OCREngineFactory.create("tesseract")
            assert isinstance(engine, TesseractOCREngine)

    def test_create_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown OCR engine"):
            OCREngineFactory.create("unknown_engine")
