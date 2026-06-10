#!/bin/bash

echo "🚀 Inițializare ClutterKill..."

# 1. Verificăm dacă există Python
if ! command -v python3 &> /dev/null
then
    echo "❌ Eroare: Python3 nu este instalat."
    exit 1
fi

# 2. Creăm mediul virtual dacă nu există
if [ ! -d ".venv" ]; then
    echo "📦 Creare mediu virtual Python (.venv)..."
    python3 -m venv .venv
fi

# 3. Activăm mediul virtual
source .venv/bin/activate

# 4. Instalăm dependențele
echo "⬇️ Instalare dependențe din requirements.txt..."
pip install -r requirements.txt -q

# 5. Setare variabile mediu
if [ ! -f ".env" ]; then
    echo "⚠️ Fișierul .env nu există. Copiez din .env.example..."
    cp .env.example .env
fi

# 6. Pornire aplicație
echo "✅ Totul este gata! Se lansează interfața grafică..."
python main.py
