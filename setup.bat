@echo off
REM ClutterKill — First-time setup script (Windows)
setlocal enabledelayedexpansion

echo === ClutterKill Setup (Windows) ===

REM 1. Python virtualenv
if not exist ".venv\" (
    echo [1/5] Creating virtual environment...
    python -m venv .venv
)
call .venv\Scripts\activate.bat

REM 2. Dependencies
echo [2/5] Installing Python dependencies...
pip install --upgrade pip -q
pip install -r requirements.txt -q

REM 3. .env
if not exist ".env" (
    echo [3/5] Creating .env from template...
    copy .env.example .env
) else (
    echo [3/5] .env already exists -- skipping.
)

REM 4. Ollama models
echo [4/5] Setting up Ollama models...
where ollama >nul 2>&1
if %ERRORLEVEL% == 0 (
    ollama pull gemma2:2b
    ollama create ck-model -f ai\Modelfile
    ollama create ck-extractor -f ai\Modelfile.extractor
    echo   Models created locally.
) else (
    echo   Ollama not found. Trying Docker...
    where docker >nul 2>&1
    if %ERRORLEVEL% == 0 (
        docker-compose up -d ollama
        echo   Waiting for Ollama to start...
        timeout /t 20 /nobreak >nul
        docker exec clutterkill_ollama ollama pull gemma2:2b
        docker exec clutterkill_ollama ollama create ck-model -f /app/ai/Modelfile
        docker exec clutterkill_ollama ollama create ck-extractor -f /app/ai/Modelfile.extractor
        echo   Models created inside Docker container.
    ) else (
        echo   ERROR: Neither Ollama nor Docker is available.
        echo   Install Ollama from https://ollama.com
        echo   Or Docker Desktop from https://docker.com
        pause
        exit /b 1
    )
)

REM 5. Tesseract check
echo [5/5] Checking Tesseract OCR...
where tesseract >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo   Tesseract found.
) else (
    if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
        echo   Tesseract found at default path.
    ) else (
        echo   Tesseract not found (OCR on images will be disabled).
        echo   Download from: https://github.com/UB-Mannheim/tesseract/wiki
    )
)

echo.
echo === Setup complete! Run the app with: ===
echo   .venv\Scripts\activate
echo   python main.py
pause
