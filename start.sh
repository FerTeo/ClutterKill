#!/bin/bash
# ClutterKill — Start script
# Pornește containerul AI (dacă e cazul) și lansează interfața grafică.

echo "🚀 Inițializare ClutterKill..."

# ── 1. Verificăm dacă există Python ──────────────────────────────
if ! command -v python3 &> /dev/null; then
    echo "❌ Eroare: Python3 nu este instalat."
    exit 1
fi

# ── 2. Mediul virtual ────────────────────────────────────────────
if [ ! -d ".venv" ]; then
    echo "📦 Creare mediu virtual Python (.venv)..."
    python3 -m venv .venv
fi
source .venv/bin/activate

# ── 3. Dependențe ────────────────────────────────────────────────
echo "⬇️  Instalare dependențe din requirements.txt..."
pip install -r requirements.txt -q

# ── 4. Variabile de mediu ────────────────────────────────────────
if [ ! -f ".env" ]; then
    echo "⚠️  Fișierul .env nu există. Copiez din .env.example..."
    cp .env.example .env
fi

# ── 5. Pornim Docker Ollama (doar dacă nu avem Google API key) ───
source .env 2>/dev/null || true
GOOGLE_KEY="${GOOGLE_API_KEY:-}"

if [ -n "$GOOGLE_KEY" ] && [ "$GOOGLE_KEY" != "your_google_api_key_here" ]; then
    echo "🌐 Google API key detectat — se folosește Gemini (fără Docker)."
else
    echo "🐳 Pornire container Ollama..."
    if command -v docker &> /dev/null; then
        docker compose up -d ollama
        echo "   Așteptăm ca Ollama să fie gata..."
        # Așteptăm maxim 60s ca healthcheck-ul să treacă
        for i in $(seq 1 12); do
            if docker exec clutterkill_ollama ollama list &>/dev/null; then
                echo "   ✅ Ollama este gata!"
                break
            fi
            sleep 5
        done
    else
        echo "   ⚠️  Docker nu este instalat. Ollama nu va fi disponibil."
    fi
fi

# ── 6. Pornire aplicație ─────────────────────────────────────────
echo "✅ Totul este gata! Se lansează interfața grafică..."
python main.py
