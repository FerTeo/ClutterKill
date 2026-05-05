# Folosim o imagine de bază Python minimală și eficientă
FROM python:3.12-slim

# Setăm variabile de mediu pentru a preveni fișierele .pyc și a asigura output-ul instant in consolă
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Setăm directorul de lucru
WORKDIR /app

# Instalăm dependențele de sistem necesare pentru procesarea OCR și PDF-uri
# - tesseract-ocr: motorul OCR necesar pentru pytesseract
# - tesseract-ocr-ron: pachetul de limbă română pentru OCR
# - poppler-utils: utilitare pentru procesarea de PDF-uri (uneori necesare pentru pymupdf / pdf2image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-ron \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copiem doar requirements.txt inițial pentru a folosi cache-ul Docker pentru dependințe
COPY requirements.txt .

# Instalăm dependențele Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# (Opțional) Copiem restul proiectului.
# În docker-compose acest lucru este suprascris de volumul `.:/app`, 
# dar este o practică bună să existe în Dockerfile pentru a avea o imagine completă.
COPY . .

# Comanda default (keep-alive) - utilă pentru development/testing via docker-compose
CMD ["tail", "-f", "/dev/null"]
