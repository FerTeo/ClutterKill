@echo off
REM ClutterKill — Docker setup script (Windows)
setlocal enabledelayedexpansion

echo === ClutterKill Docker Setup (Windows) ===

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
echo [4/5] Setting up Ollama models (via Docker)...
where docker >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   ERROR: Docker is required but not installed.
    echo   Install Docker Desktop from https://docker.com
    pause
    exit /b 1
)

docker-compose up -d ollama
echo   Waiting for Ollama to start...
timeout /t 15 /nobreak >nul
docker exec -it clutterkill_ollama ollama pull gemma2:2b || docker exec clutterkill_ollama ollama pull gemma2:2b
docker exec -it clutterkill_ollama ollama pull llava:7b || docker exec clutterkill_ollama ollama pull llava:7b
docker exec -it clutterkill_ollama ollama create ck-model -f /app/ai/Modelfile || docker exec clutterkill_ollama ollama create ck-model -f /app/ai/Modelfile
docker exec -it clutterkill_ollama ollama create ck-extractor -f /app/ai/Modelfile.extractor || docker exec clutterkill_ollama ollama create ck-extractor -f /app/ai/Modelfile.extractor
docker exec -it clutterkill_ollama ollama create ck-vision -f /app/ai/Modelfile.vision || docker exec clutterkill_ollama ollama create ck-vision -f /app/ai/Modelfile.vision
echo   Models created inside Docker container.

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
echo   start.bat
pause
