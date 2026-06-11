# 🗂️ ClutterKill

**ClutterKill** este o aplicație desktop multi-agent pentru **organizarea automată a fișierelor** folosind inteligență artificială. Arunci un folder plin de haos (PDF-uri, poze, documente Word), definești o regulă, apeși un buton și AI-ul le sortează, redenumește și mută automat.

> **Cross-Platform:** Aplicația este construită în **Python** și **PyQt6** — funcționează pe **macOS**, **Windows** și **Linux**.

---

## 📑 Cuprins

- [Cum funcționează](#-cum-funcționează)
- [Cerințe de sistem](#-cerințe-de-sistem)
- [Instalare rapidă](#-instalare-rapidă)
  - [macOS / Linux](#macos--linux)
  - [Windows](#windows)
- [Configurare AI Provider](#-configurare-ai-provider)
  - [Opțiunea 1: Google Gemini (recomandat)](#opțiunea-1-google-gemini-recomandat--rapid-fără-docker)
  - [Opțiunea 2: Ollama Local (Docker)](#opțiunea-2-ollama-local-docker--gratuit-offline)
- [Lansare aplicație](#-lansare-aplicație)
- [User Stories](#-user-stories)
- [Arhitectură proiect](#-arhitectură-proiect)
- [AI Model Registry](#-ai-model-registry)
- [Pipeline de procesare](#-pipeline-de-procesare)
- [Dependențe Python](#-dependențe-python)
- [Code Formatting & Pre-Commit](#-code-formatting--pre-commit-hooks)
- [Troubleshooting](#-troubleshooting)
- [Changelog](#-changelog)

---

## 🧠 Cum funcționează

```text
┌─────────────────────────────────────────────────────────────────┐
│                         ClutterKill                             │
│                                                                 │
│  📂 Folder Sursă          📂 Folder Destinație                  │
│  (haos total)              (organizat de AI)                    │
│                                                                 │
│  factura_scan123.pdf  ──►  2024_eMAG_Laptop_Gaming.pdf         │
│  IMG_20231225.jpeg    ──►  Christmas_Family_Dinner.jpeg        │
│  doc(1)(2).docx       ──►  Referat_Economia_Digitala.docx     │
│  ???_unknown.pdf      ──►  🔒 Quarantine (AI nesigur)          │
└─────────────────────────────────────────────────────────────────┘
```

Aplicația folosește **3 agenți AI** care lucrează în lanț:

| Agent | Rol | Ce face concret |
|-------|-----|-----------------|
| **Agent 0** (Compiler) | Înțelege regula ta | Transformă instrucțiunea ta ("Facturi eMAG") într-un JSON structurat |
| **Agent 1** (Extractor) | Citește fișierul | Extrage text din PDF/DOCX/imagini, generează un rezumat tehnic |
| **Agent 2** (Decider) | Ia decizia finală | Combină regula cu rezumatul și decide: mută + redenumește SAU carantină |

---

## 📋 Cerințe de sistem

| Cerință | Detalii |
|---------|---------|
| **Python** | 3.10 sau mai nou |
| **Docker Desktop** | Doar dacă folosești Ollama local (fără Google API key) |
| **Tesseract OCR** | Opțional — necesar doar pentru extragerea textului din imagini |
| **Spațiu pe disk** | ~500MB (doar Google Gemini) sau ~7GB (cu modele Ollama locale) |

---

## 🚀 Instalare rapidă

### macOS / Linux

```bash
# 1. Clonează repo-ul
git clone https://github.com/FerTeo/ClutterKill.git
cd ClutterKill

# 2. (Opțional) Setează Google API key ÎNAINTE de setup
cp .env.example .env
# Editează .env și pune cheia ta reală la GOOGLE_API_KEY=...

# 3. Rulează setup-ul automat
bash setup.sh

# 4. Pornește aplicația
bash start.sh
```

**Ce face `setup.sh` automat:**
1. ✅ Creează mediul virtual Python (`.venv`)
2. ✅ Instalează toate dependențele din `requirements.txt`
3. ✅ Generează fișierul `.env` din template (dacă nu există)
4. ✅ Detectează dacă ai `GOOGLE_API_KEY`:
   - **Dacă DA** → gata, nu mai face nimic cu Docker
   - **Dacă NU** → pornește `docker compose up -d` și descarcă modelele AI automat

### Windows

```cmd
REM 1. Clonează repo-ul
git clone https://github.com/FerTeo/ClutterKill.git
cd ClutterKill

REM 2. (Opțional) Setează Google API key ÎNAINTE de setup
copy .env.example .env
REM Editează .env cu Notepad și pune cheia la GOOGLE_API_KEY=...

REM 3. Rulează setup-ul automat
setup.bat

REM 4. Pornește aplicația
start.bat
```

> [!NOTE]
> Pe Windows, scripturile `.bat` fac exact același lucru ca cele `.sh` de pe Mac/Linux. Aceeași logică de auto-detect pentru Google API key.

---

## ⚙️ Configurare AI Provider

Aplicația detectează **automat** ce provider AI să folosească pe baza fișierului `.env`:

```text
Există GOOGLE_API_KEY valid în .env?
  ├── ✅ DA  →  Google Gemini (cloud, rapid, fără Docker)
  └── ❌ NU  →  Ollama local (Docker, offline, gratuit)
```

### Opțiunea 1: Google Gemini (recomandat — rapid, fără Docker)

1. Obține un API key gratuit de pe [Google AI Studio](https://aistudio.google.com/apikey)
2. Deschide fișierul `.env` și înlocuiește placeholder-ul:

```env
# ─── Google Gemini ─────────────────────────────────────────────
GOOGLE_API_KEY=AIzaSyD...cheia_ta_reala_aici
GOOGLE_MODEL_NAME=gemini-2.0-flash
```

3. Rulează `bash setup.sh` (sau `setup.bat` pe Windows) — va detecta key-ul și va sări peste Docker
4. Gata! Aplicația va folosi Google Gemini instant

> [!TIP]
> Cu Google Gemini, procesarea unui folder de 10 fișiere durează **sub 30 de secunde**. Cu Ollama local pe CPU, aceeași operație poate dura **5-10 minute**.

### Opțiunea 2: Ollama Local (Docker — gratuit, offline)

Dacă **nu** ai sau **nu vrei** un API key Google, aplicația folosește modele AI locale care rulează prin Docker.

**Cerințe suplimentare:**
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalat și pornit
- Minim **10GB spațiu liber** pe disk (modelele au ~6GB)

**Setup:**
```bash
# setup.sh detectează automat că nu ai Google key și pornește Docker
bash setup.sh
```

Ce se întâmplă în spate:
1. `docker compose up -d` pornește 3 servicii:
   - **`ollama`** — serverul Ollama (rulează permanent)
   - **`ollama-setup`** — descarcă modelele de bază (`gemma2:2b` + `llava:7b`) și creează modelele custom (`ck-model`, `ck-extractor`, `ck-vision`). Rulează **o singură dată** la prima instalare.
   - **`app`** — containerul Python (opțional, pentru teste)
2. Modelele sunt salvate persistent într-un volum Docker (`ollama_data`), deci nu se re-descarcă la fiecare restart

**Monitorizare descărcare modele:**
```bash
docker compose logs -f ollama-setup
# Când vezi "=== Toate modelele sunt gata! ===" poți porni aplicația
```

**Verificare modele instalate:**
```bash
docker exec clutterkill_ollama ollama list
# Ar trebui să vezi: ck-model, ck-extractor, ck-vision, gemma2:2b, llava:7b
```

---

## ▶️ Lansare aplicație

### macOS / Linux
```bash
bash start.sh
```

### Windows
```cmd
start.bat
```

**Ce face `start.sh` / `start.bat`:**
1. Activează mediul virtual Python
2. Verifică dacă ai Google API key:
   - **DA** → pornește direct aplicația (fără Docker)
   - **NU** → pornește containerul Ollama și așteaptă să fie gata
3. Lansează interfața grafică (`python main.py`)

**Alternativ (manual):**
```bash
source .venv/bin/activate   # Mac/Linux
# SAU: .venv\Scripts\activate.bat   # Windows

python main.py
```

---

## 📖 User Stories

| # | Titlu | Descriere |
|---|-------|-----------|
| US1 | **Selecție foldere** | Selectez un folder sursă și un folder destinație prin butoane de "Browse" |
| US2 | **Reguli Standard (Drag & Drop)** | Trag blocuri logice (`[An]`, `[Emitent]`) pentru a forma șabloane vizuale de redenumire |
| US3 | **Salvare Șabloane** | Salvez șabloanele sub un nume personalizat (ex: "Regulă Facturi") pentru reutilizare |
| US4 | **Optimizare PDF-uri** | Setez o limită de pagini citite pentru PDF-uri mari (ex: doar primele 10 pagini) |
| US5 | **Monitorizare Progres** | Apăs "Start Kill" și văd o bară de progres animată cu statusul în timp real |
| US6 | **Transparență AI** | Un log vizual (terminal integrat) afișează deciziile AI în timp real |
| US7 | **Zona de Carantină** | Fișierele despre care AI-ul nu e sigur ajung în tab-ul "Quarantine Zone" |
| US8 | **Decizie Rapidă (Split Screen)** | Click pe un fișier din Carantină → split screen: previzualizare + propunerea AI |
| US9 | **Corectare Manuală** | Editez manual numele propus de AI și apăs "Approve" |
| US10 | **Undo (Safety Net)** | Tab "Activity History" cu ultimele 50 de fișiere mutate + buton "Undo" pe fiecare rând |
| US11 | **Reguli Avansate AI** | Scriu o regulă complexă în limbaj natural (ex: "Dacă e factură eMAG, pune-l în Facturi/") |

---

## 🏗️ Arhitectură proiect

```text
ClutterKill/
├── 📄 main.py                    # Punctul de intrare — lansează interfața PyQt6
├── 📄 requirements.txt           # Dependențe Python
├── 📄 Dockerfile                 # Container Python app (tesseract + dependențe)
├── 📄 docker-compose.yml         # Orchestrare: ollama + ollama-setup + app
├── 📄 .dockerignore              # Exclude .venv, .git etc. din build context
├── 📄 .env.example               # Template pentru variabilele de mediu
├── 📄 setup.sh / setup.bat       # Setup automat (Mac/Linux / Windows)
├── 📄 start.sh / start.bat       # Lansare aplicație (Mac/Linux / Windows)
│
├── 📂 ai/                        # MODULUL AI
│   ├── llm_config.py             # Factory LLM — auto-detect Google vs Ollama
│   ├── vision_tools.py           # Vision AI — analiză vizuală imagini
│   ├── tools.py                  # Extragere text din PDF, imagini, DOCX
│   ├── agent_compiler.py         # Agent 0: Regulă naturală → JSON structurat
│   ├── agent_extractor.py        # Agent 1: Fișier fizic → rezumat tehnic
│   ├── agent_decider.py          # Agent 2: Rezumat + regulă → decizie finală
│   ├── Modelfile                 # Config model Ollama (clasificare)
│   ├── Modelfile.extractor       # Config model Ollama (extragere)
│   └── Modelfile.vision          # Config model Ollama (vision/imagini)
│
├── 📂 core/                      # LOGICA BACKEND
│   ├── file_manager.py           # Mutare, redenumire fișiere (cross-platform)
│   ├── undo_manager.py           # Stiva de Undo (ultimele 50 acțiuni)
│   ├── quarantine_db.py          # SQLite DB pentru fișierele nesigure
│   └── scan_worker.py            # QThread: pipeline complet de scanare
│
├── 📂 ui/                        # INTERFAȚA GRAFICĂ (PyQt6)
│   ├── app_window.py             # QMainWindow principal
│   ├── style.qss                 # Dark Theme (Catppuccin Macchiato)
│   └── tabs/
│       ├── scan_tab.py           # Tab Scanare: Start, Progress, Terminal
│       ├── rules_tab.py          # Tab Reguli: Drag&Drop + AI Chat
│       ├── quarantine_tab.py     # Tab Carantină: Split-screen preview
│       └── history_tab.py        # Tab Istoric: Tabel + Undo
│
├── 📂 tests/                     # TESTE
│   ├── test_core.py              # Unit tests file_manager, undo
│   └── evals/
│       └── test_agents.py        # Teste agenți AI (JSON valid)
│
├── 📂 scripts/                   # UTILITARE
│   └── generate_mock_data.py     # Generează fișiere de test
│
└── 📂 docs/                      # DOCUMENTAȚIE
    ├── RAPORT_AI.md              # Raport utilizare LLM-uri
    └── arhitectura.md            # Diagrame UML și flux (Mermaid)
```

---

## 🧠 AI Model Registry

ClutterKill folosește modele AI diferite în funcție de provider:

### Modul Google Gemini (cloud)
| Funcție | Model folosit | Descriere |
|---------|---------------|-----------|
| Clasificare + Decizie | `gemini-2.0-flash` | Rapid, gratuit cu limite |
| Extragere text | `gemini-2.0-flash` | Rezumat tehnic documente |
| Vision (imagini) | `gemini-2.0-flash` | Multimodal — identificare vizuală |

### Modul Ollama Local (Docker)
| Model Custom | Model de Bază | Scop | Fișier Config | Mărime |
|-------------|---------------|------|---------------|--------|
| `ck-model` | `gemma2:2b` | Agent 0 (Compiler) + Agent 2 (Decider) | `ai/Modelfile` | ~1.6GB |
| `ck-extractor` | `gemma2:2b` | Agent 1 (Extractor) — rezumat documente | `ai/Modelfile.extractor` | ~1.6GB |
| `ck-vision` | `llava:7b` | Vision AI — identificare vizuală imagini | `ai/Modelfile.vision` | ~4.5GB |

---

## 🔄 Pipeline de procesare

### Pentru documente (PDF, DOCX, TXT):
```text
📄 Document  →  Extragere text (PyMuPDF / python-docx)
             →  Agent 1 (Extractor): rezumat tehnic
             →  Agent 2 (Decider): decizie + redenumire
             →  ✅ Mutat SAU 🔒 Carantină
```

### Pentru imagini (JPG, PNG, BMP):
```text
📷 Imagine  →  Vision AI (Gemini sau LLaVA): identificare vizuală → "dog"
            →  OCR (Tesseract): text extras din imagine
            →  Rezumat combinat (vizual + text)
            →  Agent 2 (Decider): decizie + redenumire
            →  ✅ Dog_Playing_Park.jpeg SAU 🔒 Carantină
```

---

## 📦 Dependențe Python

Toate dependențele sunt în `requirements.txt`:

| Pachet | Scop |
|--------|------|
| `PyQt6` | Interfață grafică desktop |
| `langchain`, `langchain-core`, `langchain-community` | Orchestrare agenți AI |
| `langchain-ollama` | Conector LangChain → Ollama local |
| `langchain-google-genai` | Conector LangChain → Google Gemini |
| `PyMuPDF` | Extragere text din PDF-uri |
| `pytesseract` | OCR — text din imagini |
| `Pillow` | Procesare imagini |
| `python-docx` | Citire fișiere Word (.docx) |
| `fpdf2` | Generare PDF-uri de test |
| `pydantic` | Validare date structurate |
| `python-dotenv` | Citire variabile din `.env` |
| `pytest` | Framework de testare |
| `ruff` | Linting și formatare cod |

### Instalare Tesseract OCR (opțional):

| OS | Comandă |
|----|---------|
| **macOS** | `brew install tesseract tesseract-lang` |
| **Windows** | Descarcă installerul de la [UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) |
| **Linux (Ubuntu)** | `sudo apt-get install tesseract-ocr tesseract-ocr-ron` |

---

## 🛠️ Code Formatting & Pre-Commit Hooks

Proiectul folosește **`pre-commit`** cu **`ruff`** pentru formatare automată la fiecare commit.

```bash
# Instalare (o singură dată)
pip install pre-commit
pre-commit install

# De acum, la fiecare git commit, ruff va formata automat codul.
# Dacă face modificări, commit-ul se anulează — dă git add și commit din nou.
```

---

## 🔧 Troubleshooting

### ❌ "Connection refused" / "Connection reset by peer"
**Cauza:** Containerul Ollama nu este pornit sau nu a terminat de descărcat modelele.
**Fix:**
```bash
# Verifică dacă containerul rulează
docker ps

# Verifică progresul descărcării modelelor
docker compose logs -f ollama-setup

# Repornește totul
docker compose down && docker compose up -d
```

### ❌ "input/output error" / "no space left on device"
**Cauza:** Hard disk-ul este plin. Docker folosește mult spațiu pentru Build Cache.
**Fix:**
```bash
docker builder prune -a -f
docker system prune -f
# Apoi rulează din nou: bash setup.sh
```

### ❌ "suggested_name: Input should be a valid string"
**Cauza:** Bug vechi Pydantic în `agent_decider.py` — a fost reparat.
**Fix:** Asigură-te că ai ultima versiune a codului (`git pull`).

### ❌ Aplicația e lentă (minute per fișier)
**Cauza:** Folosești Ollama local pe CPU în loc de Google Gemini.
**Fix:** Setează `GOOGLE_API_KEY` în `.env` cu o cheie reală de la [Google AI Studio](https://aistudio.google.com/apikey).

### ❌ "API Rate Limit Hit (429)"
**Cauza:** Ai depășit limita gratuită a API-ului Google Gemini.
**Fix:** Aplicația face automat retry cu sleep de 15 secunde. Dacă persistă, așteaptă câteva minute.

### ❌ Tesseract nu funcționează / OCR dezactivat
**Cauza:** Tesseract OCR nu este instalat pe sistemul tău.
**Fix:** Instalează-l conform tabelului de mai sus (secțiunea Dependențe Python).

---

## 🌟 Changelog

- **Auto-detect AI Provider:** Aplicația detectează automat dacă ai Google API key → folosește Gemini. Fără key → fallback la Ollama local prin Docker. Nu mai trebuie setat manual `AI_PROVIDER`.
- **Setup simplificat:** Un singur `bash setup.sh` (sau `setup.bat` pe Windows) face totul automat. Docker descarcă modelele prin `docker-compose.yml` (serviciul `ollama-setup`).
- **Scripturi Windows:** `setup.bat` și `start.bat` funcționează identic cu variantele `.sh` de pe Mac/Linux.
- **UI Revamp (Dark Theme Premium):** Interfața a primit un redesign complet bazat pe paleta Catppuccin Macchiato.
- **Visual Builder Funcțional:** Tab-ul "Rules" suportă șabloane stricte cu butoane "Click-to-Insert" pentru variabile (`[An]`, `[Luna]`, `[Emitent]`).
- **Flattened Output:** Fișierele redenumite de AI sunt exportate direct în root-ul folderului destinație (fără sub-foldere forțate).
- **Fix ExtractorAgent:** Rezolvat bug cauzat de noul SDK Google V2 care bloca parsarea imaginilor.
- **Rate-Limiting Gemini:** Mecanism automat de sleep (15s) la HTTP 429.

---

*Pentru instrucțiuni detaliate de DevOps și QA, consultă [README_ingineri.md](README_ingineri.md).*
