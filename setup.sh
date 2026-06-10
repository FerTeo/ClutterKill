#!/usr/bin/env bash
# ClutterKill — First-time setup script
set -e

echo "=== ClutterKill Setup ==="

# 1. Python virtualenv (Necesar pentru interfața grafică)
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

# 4. Ollama models (ÎN DOCKER EXACT CUM SCRIE ÎN README)
echo "[4/5] Setting up Ollama models (via Docker)..."
if ! command -v docker &>/dev/null; then
  echo "  ERROR: Docker is required but not installed."
  exit 1
fi

docker-compose up -d ollama
echo "  Waiting for Ollama to start..."
sleep 15
docker exec -it clutterkill_ollama ollama pull gemma2:2b || docker exec clutterkill_ollama ollama pull gemma2:2b
docker exec -it clutterkill_ollama ollama pull llava:7b || docker exec clutterkill_ollama ollama pull llava:7b
docker exec -it clutterkill_ollama ollama create ck-model -f /app/ai/Modelfile || docker exec clutterkill_ollama ollama create ck-model -f /app/ai/Modelfile
docker exec -it clutterkill_ollama ollama create ck-extractor -f /app/ai/Modelfile.extractor || docker exec clutterkill_ollama ollama create ck-extractor -f /app/ai/Modelfile.extractor
docker exec -it clutterkill_ollama ollama create ck-vision -f /app/ai/Modelfile.vision || docker exec clutterkill_ollama ollama create ck-vision -f /app/ai/Modelfile.vision
echo "  Models created inside Docker container."

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
echo "  bash start.sh"
