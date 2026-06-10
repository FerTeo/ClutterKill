@echo off
echo =======================================================
echo    Initializare ClutterKill...
echo =======================================================

REM Asigura-te ca ruleaza containerul de AI
docker-compose up -d ollama

REM 1. Verificam daca exista Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [Eroare] Python nu este instalat sau nu este in PATH.
    pause
    exit /b 1
)

REM 2. Cream mediul virtual daca nu exista
if not exist ".venv\Scripts\activate" (
    echo [Info] Cream mediul virtual Python (.venv)...
    python -m venv .venv
)

REM 3. Activam mediul virtual
call .venv\Scripts\activate.bat

REM 4. Instalam dependentele
echo [Info] Instalam dependentele din requirements.txt...
pip install -r requirements.txt -q

REM 5. Setare variabile mediu
if not exist ".env" (
    echo [Info] Fisierul .env nu exista. Se copiaza din .env.example...
    copy .env.example .env
)

REM 6. Pornire aplicatie
echo [Info] Totul este gata! Se lanseaza interfata grafica...
python main.py
pause
