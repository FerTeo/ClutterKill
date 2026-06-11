@echo off
REM ClutterKill — First-time setup script (Windows)
REM Rulează o singură dată. După, folosește doar: start.bat
setlocal enabledelayedexpansion

echo === ClutterKill Setup ===

REM ── 1. Python virtualenv ──────────────────────────────────────
if not exist ".venv\" (
    echo [1/4] Creating virtual environment...
    python -m venv .venv
) else (
    echo [1/4] Virtual environment already exists.
)
call .venv\Scripts\activate.bat

REM ── 2. Python dependencies ────────────────────────────────────
echo [2/4] Installing Python dependencies...
pip install --upgrade pip -q
pip install -r requirements.txt -q

REM ── 3. Environment file ───────────────────────────────────────
if not exist ".env" (
    echo [3/4] Creating .env from template...
    copy .env.example .env
    echo.
    echo   ┌──────────────────────────────────────────────────────────┐
    echo   │  TIP: Daca ai un GOOGLE_API_KEY, seteaza-l in .env     │
    echo   │  si aplicatia va folosi Google Gemini automat.           │
    echo   │  Fara API key = se foloseste Ollama local (Docker).     │
    echo   └──────────────────────────────────────────────────────────┘
    echo.
) else (
    echo [3/4] .env already exists -- skipping.
)

REM ── 4. Docker + Ollama (doar dacă nu există Google API key) ───
REM Citim GOOGLE_API_KEY din .env
set "GOOGLE_KEY="
for /f "tokens=1,* delims==" %%a in ('findstr /i "GOOGLE_API_KEY" .env 2^>nul') do (
    set "GOOGLE_KEY=%%b"
)

if defined GOOGLE_KEY (
    if not "!GOOGLE_KEY!"=="your_google_api_key_here" (
        echo [4/4] Google API key detectat -- se va folosi Google Gemini.
        echo   Ollama Docker NU este necesar. Skipping Docker setup.
        goto :skip_docker
    )
)

echo [4/4] Niciun Google API key -- se configureaza Ollama via Docker...

where docker >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   ERROR: Docker nu este instalat!
    echo   Instaleaza Docker Desktop sau seteaza GOOGLE_API_KEY in .env
    pause
    exit /b 1
)

REM Pornim ollama + ollama-setup (descarcă modelele automat)
docker compose up -d
echo.
echo   Docker descarca modelele AI (gemma2:2b + llava:7b = ~6GB).
echo   La prima rulare poate dura cateva minute (depinde de net).
echo   Progresul poate fi urmarit cu: docker compose logs -f ollama-setup

:skip_docker

REM ── 5. Tesseract OCR (opțional) ──────────────────────────────
echo.
echo [Bonus] Checking Tesseract OCR...
where tesseract >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo   Tesseract found.
) else (
    if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
        echo   Tesseract found at default path.
    ) else (
        echo   Tesseract not found (OCR pe imagini va fi dezactivat).
        echo   Download from: https://github.com/UB-Mannheim/tesseract/wiki
    )
)

echo.
echo === Setup complete! ===
echo   Lanseaza aplicatia cu: start.bat
pause
