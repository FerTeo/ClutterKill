@echo off
echo =======================================================
echo    Initializare ClutterKill...
echo =======================================================

REM ── 1. Verificam daca exista Python ────────────────────────
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [Eroare] Python nu este instalat sau nu este in PATH.
    pause
    exit /b 1
)

REM ── 2. Mediul virtual ─────────────────────────────────────
if not exist ".venv\Scripts\activate" (
    echo [Info] Cream mediul virtual Python (.venv)...
    python -m venv .venv
)
call .venv\Scripts\activate.bat

REM ── 3. Dependente ─────────────────────────────────────────
echo [Info] Instalam dependentele din requirements.txt...
pip install -r requirements.txt -q

REM ── 4. Variabile de mediu ─────────────────────────────────
if not exist ".env" (
    echo [Info] Fisierul .env nu exista. Se copiaza din .env.example...
    copy .env.example .env
)

REM ── 5. Pornim Docker Ollama (doar dacă nu avem Google API key) ──
setlocal enabledelayedexpansion
set "GOOGLE_KEY="
for /f "tokens=1,* delims==" %%a in ('findstr /i "GOOGLE_API_KEY" .env 2^>nul') do (
    set "GOOGLE_KEY=%%b"
)

if defined GOOGLE_KEY (
    if not "!GOOGLE_KEY!"=="your_google_api_key_here" (
        echo [Info] Google API key detectat -- se foloseste Gemini (fara Docker).
        goto :start_app
    )
)

echo [Info] Pornire container Ollama...
where docker >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [Warning] Docker nu este instalat. Ollama nu va fi disponibil.
    goto :start_app
)

docker compose up -d ollama
echo   Asteptam ca Ollama sa fie gata...
timeout /t 15 /nobreak >nul

:start_app
endlocal

REM ── 6. Pornire aplicatie ──────────────────────────────────
echo [Info] Totul este gata! Se lanseaza interfata grafica...
python main.py
pause
