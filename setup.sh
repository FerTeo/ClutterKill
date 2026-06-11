#!/usr/bin/env bash
# ClutterKill — First-time setup script
# Rulează o singură dată. După, folosește doar: bash start.sh
set -e

echo "=== ClutterKill Setup ==="

# ── 1. Python virtualenv ──────────────────────────────────────────
if [ ! -d ".venv" ]; then
  echo "[1/4] Creating virtual environment..."
  python3 -m venv .venv
else
  echo "[1/4] Virtual environment already exists."
fi
source .venv/bin/activate

# ── 2. Python dependencies ────────────────────────────────────────
echo "[2/4] Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# ── 3. Environment file ───────────────────────────────────────────
if [ ! -f ".env" ]; then
  echo "[3/4] Creating .env from template..."
  cp .env.example .env
  echo ""
  echo "  ┌──────────────────────────────────────────────────────────┐"
  echo "  │  TIP: Dacă ai un GOOGLE_API_KEY, setează-l în .env     │"
  echo "  │  și aplicația va folosi Google Gemini automat.           │"
  echo "  │  Fără API key → se folosește Ollama local (Docker).     │"
  echo "  └──────────────────────────────────────────────────────────┘"
  echo ""
else
  echo "[3/4] .env already exists — skipping."
fi

# ── 4. Docker + Ollama (doar dacă nu există Google API key) ───────
# Citim .env pentru a verifica dacă utilizatorul are Google API key
source .env 2>/dev/null || true
GOOGLE_KEY="${GOOGLE_API_KEY:-}"

if [ -n "$GOOGLE_KEY" ] && [ "$GOOGLE_KEY" != "your_google_api_key_here" ]; then
  echo "[4/4] Google API key detectat — se va folosi Google Gemini."
  echo "  Ollama Docker NU este necesar. Skipping Docker setup."
else
  echo "[4/4] Niciun Google API key → se configurează Ollama via Docker..."

  if ! command -v docker &>/dev/null; then
    echo "  ❌ ERROR: Docker nu este instalat!"
    echo "  Instalează Docker Desktop sau setează GOOGLE_API_KEY în .env"
    exit 1
  fi

  # Pornim ollama + ollama-setup (descarcă modelele automat)
  docker compose up -d
  echo ""
  echo "  ⏳ Docker descarcă modelele AI (gemma2:2b + llava:7b ≈ 6GB)."
  echo "  La prima rulare poate dura câteva minute (depinde de net)."
  echo "  Progresul poate fi urmărit cu: docker compose logs -f ollama-setup"
fi

# ── 5. Tesseract OCR (opțional) ──────────────────────────────────
echo ""
echo "[Bonus] Checking Tesseract OCR..."
if command -v tesseract &>/dev/null; then
  echo "  ✅ Tesseract found: $(tesseract --version 2>&1 | head -1)"
else
  echo "  ⚠️  Tesseract not found (OCR pe imagini va fi dezactivat)."
  if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "  Install with: brew install tesseract"
  else
    echo "  Install with: sudo apt-get install tesseract-ocr"
  fi
fi

echo ""
echo "=== Setup complete! ==="
echo "  Lansează aplicația cu: bash start.sh"
