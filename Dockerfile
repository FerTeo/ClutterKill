# ==========================================
# Stage 1: Ollama Service
# ==========================================
FROM ollama/ollama AS ollama-service

# Copiem fișierele modelului (Modelfile, etc.)
COPY ./ai /app/ai

# Pornim serverul ollama în background, descărcăm modelele de bază și le creăm pe cele custom
RUN nohup bash -c "ollama serve &" && sleep 5 && \
    ollama pull gemma2:2b && \
    ollama pull llava:7b && \
    ollama create ck-model -f /app/ai/Modelfile && \
    ollama create ck-extractor -f /app/ai/Modelfile.extractor && \
    ollama create ck-vision -f /app/ai/Modelfile.vision

# ==========================================
# Stage 2: App Service
# ==========================================
FROM python:3.12-slim AS app-service

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-ron \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["tail", "-f", "/dev/null"]
