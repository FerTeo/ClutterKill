#!/usr/bin/env bash
# ClutterKill — First-time setup script (Linux / macOS)
set -e

echo "=== ClutterKill Setup ==="

# 1. Python virtualenv
if [ ! -d ".venv" ]; then
  echo "[1/5] Creating virtual environment..."
  python3 -m venv .venv
fi
source .venv/bin/activate

# 2. Dependencies
echo "[2/5] Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# 3. .env
if [ ! -f ".env" ]; then
  echo "[3/5] Creating .env from template..."
  cp .env.example .env
else
  echo "[3/5] .env already exists — skipping."
fi

# 4. Ollama models
echo "[4/5] Setting up Ollama models..."
if ! command -v ollama &>/dev/null; then
  echo "  Ollama not found. Trying Docker..."
  if command -v docker &>/dev/null && docker info &>/dev/null; then
    docker-compose up -d ollama
    echo "  Waiting for Ollama to start..."
    sleep 15
    docker exec clutterkill_ollama ollama pull gemma2:2b
    docker exec clutterkill_ollama ollama create ck-model -f /app/ai/Modelfile
    docker exec clutterkill_ollama ollama create ck-extractor -f /app/ai/Modelfile.extractor
    echo "  Models created inside Docker container."
  else
    echo "  ERROR: Neither Ollama nor Docker is available."
    echo "  Install Ollama from https://ollama.com or Docker from https://docker.com"
    exit 1
  fi
else
  # Ollama is installed locally
  ollama pull gemma2:2b
  ollama create ck-model -f ai/Modelfile
  ollama create ck-extractor -f ai/Modelfile.extractor
  echo "  Models created locally."
fi

# 5. Tesseract (optional, for OCR on images)
echo "[5/5] Checking Tesseract OCR..."
if command -v tesseract &>/dev/null; then
  echo "  Tesseract found: $(tesseract --version 2>&1 | head -1)"
else
  echo "  Tesseract not found (OCR on images will be disabled)."
  if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "  Install with: brew install tesseract"
  else
    echo "  Install with: sudo apt-get install tesseract-ocr"
  fi
fi

echo ""
echo "=== Setup complete! Run the app with: ==="
echo "  source .venv/bin/activate"
echo "  python main.py"
