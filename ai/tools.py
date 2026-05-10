"""
Extraction Tools — ai/tools.py

Acest modul conține funcții utilitare pentru extragerea textului din
diferite tipuri de fișiere (PDF, imagini), folosite ulterior de către
agenții AI pentru procesare.
"""

import logging
from pathlib import Path
from typing import Union

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


def extract_text_from_pdf(path: Union[str, Path], max_pages: int = 10) -> str:
    """
    Extrage textul dintr-un fișier PDF folosind PyMuPDF.

    Pentru a optimiza consumul de memorie și procesare, se limitează
    numărul maxim de pagini citite (util pentru documente foarte mari).

    Args:
        path: Calea către fișierul PDF.
        max_pages: Numărul maxim de pagini de citit (implicit: 10).

    Returns:
        Textul extras din PDF ca un singur string. Returnează un string gol în caz de eroare.
    """
    file_path = Path(path)
    if not file_path.exists():
        logger.error(f"Fișierul PDF nu a fost găsit: {file_path}")
        return ""

    try:
        text_content = []
        doc = fitz.open(file_path)

        pages_to_read = min(len(doc), max_pages)
        for page_num in range(pages_to_read):
            page = doc[page_num]
            text_content.append(page.get_text())

        doc.close()
        return "\n".join(text_content).strip()
    except Exception as e:
        logger.error(f"Eroare la extragerea textului din PDF ({file_path}): {e}")
        return ""


def extract_text_from_image(path: Union[str, Path]) -> str:
    """
    Extrage textul dintr-o imagine folosind Tesseract OCR.

    Args:
        path: Calea către fișierul imagine (PNG, JPG, etc.).

    Returns:
        Textul extras din imagine ca string. Returnează un string gol în caz de eroare.
    """
    file_path = Path(path)
    if not file_path.exists():
        logger.error(f"Imaginea nu a fost găsită: {file_path}")
        return ""

    try:
        # Pytesseract necesită un obiect de tip Image din biblioteca Pillow
        img = Image.open(file_path)
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        logger.error(f"Eroare la extragerea textului din imagine ({file_path}): {e}")
        return ""
