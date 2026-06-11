# ==========================================
# ClutterKill — Python App Container
# ==========================================
# Acest Dockerfile construiește doar containerul aplicației Python.
# Ollama (AI) rulează separat ca serviciu Docker (vezi docker-compose.yml).

FROM python:3.12-slim

# Prevenim .pyc files și asigurăm output instant în consolă
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dependențe de sistem pentru OCR și procesare PDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-ron \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Instalăm dependențele Python (cache Docker layer)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiem proiectul (suprascris de volum în docker-compose pentru dev)
COPY . .

CMD ["tail", "-f", "/dev/null"]
