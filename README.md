# ClutterKill

ClutterKill is a multi-agent desktop application for automated file organization using local AI. 

> **Cross-Platform:** Această aplicație este construită în Python și PyQt6, ceea ce o face 100% **Cross-Platform**. Funcționează perfect pe macOS, Windows și Linux, atâta timp cât ai Python instalat. Mici diferențe pot apărea la instalarea dependențelor de sistem (ex. Tesseract OCR).

# User Stories

## US 1 (Selecție foldere): 
Ca utilizator, vreau să pot selecta printr-un buton de „Browse” un folder sursă și un folder destinație, astfel încât aplicația să știe de unde preia haosul și unde livrează documentele organizate.


## US 2 (Reguli Standard - Drag & Drop): 
Ca utilizator începător, vreau să folosesc un panou de tip „Drag and Drop” pentru a trage blocuri logice (ex: [An], [Emitent]) și a forma șabloane vizuale de redenumire, astfel încât să nu scriu cod sau expresii regulate.

## US 3 (Salvare Șabloane): 
Ca utilizator, vreau să pot salva aceste șabloane sub un nume personalizat (ex: „Regulă Facturi”), astfel încât să le pot refolosi rapid la următoarele scanări.

## US 4 (Optimizare PDF-uri): 
Ca utilizator, vreau să pot seta o limită de citire pentru documentele PDF foarte mari (ex: doar primele 10 pagini), astfel încât să optimizez timpul de procesare și memoria consumată de AI.

## US 5 (Monitorizare Progres):
 Ca utilizator, vreau să pot apăsa butonul „Start Kill” și să văd imediat o bară de progres animată, astfel încât să știu în timp real cât mai durează procesarea folderului.

## US 6 (Transparență AI): 
Ca utilizator, vreau ca interfața să afișeze un log vizual (un terminal integrat) cu deciziile luate în timp real (ex: „📄 doc_1.pdf → 🧠 Factură eMAG → ✅ Mutat”), astfel încât să înțeleg cum gândește AI-ul.

## US 7 (Zona de Carantină): 
Ca utilizator, vreau să accesez un tab numit „Quarantine Zone” cu fișierele pe care AI-ul nu a fost 100% sigur cum să le clasifice, astfel încât deciziile ambigue să nu fie luate fără mine.

## US 8 (Decizie Rapidă - Split Screen):
Ca utilizator, vreau ca la click pe un fișier din Carantină ecranul să se împartă în două: în stânga previzualizarea documentului, în dreapta propunerea AI, pentru a lua o decizie vizuală rapidă.

## US 9 (Corectare Manuală): 
Ca utilizator, vreau să pot edita manual, într-un câmp text, numele propus de AI în Carantină și să apăs „Approve”, pentru a corecta erorile înainte de mutarea definitivă.

## US 10 (Safety Net - Undo):
 Ca utilizator, vreau să am un tab „Activity History” cu ultimele 50 de fișiere mutate și un buton „Undo” pe fiecare rând, astfel încât să readuc instantaneu un fișier la locația și numele original dacă m-am răzgândit.

## US 11 (Reguli Avansate AI - NOU): 
Ca utilizator avansat, vreau să pot scrie o regulă complexă sub formă de text natural (ex: "Dacă e document de la facultate, pune-l în Semestru/Materie/Curs"), astfel încât AI-ul (Agentul 0) să deducă automat ierarhiile complexe de foldere fără ca eu să folosesc blocurile de Drag & Drop.

# Project Structure

```text
ClutterKill/
├── 📄 main.py                  # Punctul de intrare: lansează interfața grafică PyQt6
├── 📄 requirements.txt         # Dependințele: PyQt6, langchain, pydantic, pymupdf, pytest etc.
├── 📄 docker-compose.yml       # Setup-ul pentru containerul Ollama local
├── 📄 .gitignore               # Fișiere de ignorat (venv, test_data/, __pycache__)
├── 📄 .pre-commit-config.yaml  # Configurarea hook-urilor pre-commit (Ruff etc.)
├── 📄 README.md                # Documentația principală a proiectului
│
├── 📂 docs/                    # DOCUMENTAȚIE (Pentru evaluarea MDS)
│   ├── 📄 RAPORT_AI.md         # Raportul utilizării LLM-urilor în dezvoltare
│   └── 🖼️ arhitectura.md       # Diagramele UML și de flux (Mermaid)
│
├── 📂 scripts/                 # UTILITARE PENTRU DEZVOLTATORI
│   └── 📄 generate_mock_data.py # Generează haosul de test (PDF-uri, Word, imagini OCR)
│
├── 📂 test_data/               # FOLDER DE TESTARE (Generat automat, ignorat de Git)
│   ├── 📂 source/              # Folderul sursă cu fișiere dezorganizate
│   └── 📂 destination/         # Folderul destinație unde AI-ul le va muta
│
├── 📂 ai/                      # MODULUL AI (Inteligența Aplicației)
│   ├── 📄 __init__.py
│   ├── 📄 Modelfile            # Definiția modelului Gemma 2:2b (Agent 0 & 2 - Clasificare)
│   ├── 📄 Modelfile.extractor  # Definiția modelului Gemma 2:2b (Agent 1 - Extragere)
│   ├── 📄 Modelfile.vision     # Definiția modelului LLaVA 7B (Vision - Analiză vizuală imagini)
│   ├── 📄 llm_config.py        # Factory + configurare LLM (Ollama / Google)
│   ├── 📄 tools.py             # Funcții: extract_text_from_pdf, extract_text_from_image, extract_text_from_docx
│   ├── 📄 vision_tools.py      # Modul Vision AI: describe_image() — trimite poze la LLaVA pentru identificare
│   ├── 📄 agent_compiler.py    # AGENT 0: Traduce promptul natural în JSON (Reguli)
│   ├── 📄 agent_extractor.py   # AGENT 1: Rezumă fișierul fizic (chain-of-thought extraction)
│   └── 📄 agent_decider.py     # AGENT 2: Combină Agent 0 cu Agent 1 și ia decizia finală
│
├── 📂 core/                    # LOGICA BACKEND (Sistemul de operare)
│   ├── 📄 __init__.py
│   ├── 📄 file_manager.py      # Mutare, redenumire (cross-platform cu pathlib)
│   ├── 📄 undo_manager.py      # Logica pentru stiva de Undo (ultimele 50 acțiuni)
│   ├── 📄 quarantine_db.py     # Baza de date SQLite pentru fișierele nesigure
│   └── 📄 scan_worker.py       # QThread: pipeline-ul complet de scanare (Vision + Extragere + Decizie)
│
├── 📂 ui/                      # INTERFAȚA GRAFICĂ (PyQt6)
│   ├── 📄 __init__.py
│   ├── 📄 styles.qss           # Design System (Dark Theme, culori, fonturi)
│   ├── 📄 app_window.py        # QMainWindow și gestionarea thread-urilor
│   └── 📂 tabs/                
│       ├── scan_tab.py         # Start, Progress Bar, Terminal vizual
│       ├── rules_tab.py        # Switch între Drag&Drop și AI Chat Box
│       ├── quarantine_tab.py   # Split-screen (Previzualizare vs Editare AI)
│       └── history_tab.py      # Tabelul cu acțiuni și butoane de Undo
│
└── 📂 tests/                   # TESTARE ȘI EVALUARE (Barem)
    ├── 📄 __init__.py
    ├── 📄 test_core.py         # Unit tests pentru file_manager și undo
    └── 📂 evals/               
        └── test_agents.py      # Verifică dacă Agenții 0 și 2 scot JSON valid
```

## 🧠 AI Model Registry

ClutterKill folosește **4 modele AI locale** rulând prin Ollama în Docker:

| Model | Bază | Scop | Fișier Config | Mărime |
|-------|------|------|---------------|--------|
| `ck-model` | `gemma2:2b` | Agent 0 (Compiler) + Agent 2 (Decider) — clasificare și decizie | `ai/Modelfile` | ~1.6GB |
| `ck-extractor` | `gemma2:2b` | Agent 1 (Extractor) — rezumat tehnic documente | `ai/Modelfile.extractor` | ~1.6GB |
| `ck-vision` | `llava:7b` | Vision AI — identificare vizuală imagini (dog, cat, sign...) | `ai/Modelfile.vision` | ~4.5GB |
| `gemma2:2b` | - | Model de bază (descărcat automat) | - | ~1.6GB |
| `llava:7b` | - | Model de bază multimodal (descărcat automat) | - | ~4.5GB |

### Pipeline de procesare imagini

```text
📷 Imagine (.jpg/.png)  →  Vision AI (ck-vision / llava:7b)  →  "dog"
                        →  OCR (Tesseract)                   →  text extras
                        →  Combinate în rezumat               →  Decizie: Dog.jpeg
```

Pentru **documente** (PDF, DOCX, TXT) se folosește doar pipeline-ul text clasic (fără Vision AI).

## 📁 Directory Architecture

The project follows a structured modular architecture:

- **`ui/`**: Contains the graphical user interface components built with `PyQt6`.
- **`core/`**: Houses the core application logic (file management, quarantine, undo mechanisms).
- **`ai/`**: Contains AI models, agents, and configuration for handling language models and extraction tasks.
- **`tests/`**: Includes all the unit and integration tests driven by `pytest`.
- **`scripts/`**: Utility scripts (e.g., generating mock data for testing).
- **`docs/`**: Documentation files (architecture, AI models reports, etc.).

*Note: The `ui/`, `core/`, `ai/`, and `tests/` directories are Python packages and contain `__init__.py` files.*

## 📦 Dependencies & Installation

The project's Python dependencies are listed in `requirements.txt`, which include:
- **PyQt6**: For the desktop graphical interface.
- **Langchain & Langchain-Community**: For building and orchestrating AI agents.
- **PyMuPDF, Pytesseract, Pillow, python-docx, fpdf**: For processing and analyzing various document and image formats.
- **Pydantic**: For data validation.
- **Pytest**: For testing the codebase.
- **Ruff**: For extremely fast Python linting and code formatting.

### How to Install:

**1. System Dependencies (OCR)**
To process images (PNG, JPG), you must install Tesseract OCR on your host machine:
- **macOS**: `brew install tesseract tesseract-lang`
- **Windows**: Download the installer from [UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
- **Linux (Ubuntu/Debian)**: `sudo apt-get install tesseract-ocr tesseract-ocr-ron`

**2. Python Dependencies**
To set up your environment, install the dependencies using `pip`:
```bash
pip install -r requirements.txt
```
*(If you use `uv`, you can also run `uv pip install -r requirements.txt`)*

## 🛠️ Code Formatting & Pre-Commit Hooks

To ensure consistent code quality and formatting, this project is configured to use **`pre-commit`** with **`ruff`**. This will automatically format your Python code every time you make a commit.

### How to Use:
1. Ensure `pre-commit` is installed globally:
   ```bash
   pip install pre-commit
   ```
2. Install the Git hook script within your local repository:
   ```bash
   pre-commit install
   ```


Once installed, `ruff` will automatically format your code on `git commit`. If changes are made by the formatter, the commit will abort—simply `git add` the updated files and run `git commit` again.

## 🐳 Environment & Local AI Setup

Aplicația funcționează în **două moduri**, alese automat:

| Mod | Când se activează | Ce folosește | Docker necesar? |
|-----|-------------------|--------------|-----------------|
| ☁️ **Google Gemini** | Dacă `GOOGLE_API_KEY` este setat valid în `.env` | API-ul Google Gemini (cloud) | ❌ Nu |
| 🐳 **Ollama Local** | Dacă NU există `GOOGLE_API_KEY` (sau e placeholder) | Modele locale prin Docker | ✅ Da |

**Aplicația detectează automat** care mod să folosească. Dacă ai un API key Google setat, nu se mai atinge de Docker deloc.

### Instalare (o singură comandă):

```bash
bash setup.sh
```

Scriptul `setup.sh` face totul automat:
1. Creează mediul virtual Python și instalează dependențele
2. Generează fișierul `.env` din template (dacă nu există)
3. **Verifică** dacă ai `GOOGLE_API_KEY` setat:
   - ✅ Dacă **DA** → gata, nu mai face nimic cu Docker
   - ❌ Dacă **NU** → pornește `docker compose up -d` care:
     - Pornește containerul Ollama (serverul AI local)
     - Descarcă automat modelele (`gemma2:2b` ≈ 1.6GB + `llava:7b` ≈ 4.5GB)
     - Creează modelele custom (`ck-model`, `ck-extractor`, `ck-vision`)

> [!TIP]
> **Recomandat:** Dacă ai un API key Google Gemini, setează-l în `.env` înainte de `setup.sh`:
> ```bash
> cp .env.example .env
> # editează .env și pune GOOGLE_API_KEY=cheia_ta_reala
> bash setup.sh
> ```
> Astfel nu vei avea nevoie de Docker deloc și aplicația va rula instant.

> [!WARNING]
> **Probleme cu Docker pe Mac (Out of Space):**
> Modelele AI locale au ~6GB. Dacă ai puțin spațiu pe disk, Docker poate crăpa cu erori de `input/output error`. Fix:
> ```bash
> docker builder prune -a -f
> docker system prune -f
> ```
> Apoi rulează din nou `bash setup.sh`.

### Lansare aplicație:

```bash
bash start.sh
```

Scriptul `start.sh` pornește automat containerul Ollama (dacă e cazul) și lansează interfața grafică.

## 🌟 Changelog / Update-uri Recente
- **Auto-detect AI Provider:** Aplicația detectează automat dacă ai Google API key și îl folosește pe Gemini. Fără key → fallback la Ollama local prin Docker. Nu mai trebuie setat manual `AI_PROVIDER`.
- **Setup simplificat:** Un singur `bash setup.sh` face totul. Docker-ul descarcă modelele automat prin `docker-compose.yml` (serviciul `ollama-setup`).
- **UI Revamp (Dark Theme Premium):** Interfața a primit un redesign complet bazat pe paleta Catppuccin Macchiato. Colțuri rotunjite, butoane colorate vibrant și efecte subtile.
- **Visual Builder Funcțional:** Tab-ul "Rules" suportă acum șabloane stricte (Templates). A fost adăugată o paletă de butoane "Click-to-Insert" pentru a introduce automat variabile matematice (ex: `[An]`, `[Luna]`) fără a le tasta manual.
- **Simplificare Arhitectură Directoare (Flattened Output):** La cererea utilizatorilor, fișierele redenumite de AI nu mai sunt forțate în sub-foldere. Ele sunt exportate direct în root-ul folderului destinație ales de tine.
- **Reparare ExtractorAgent (Bug-ul "Strip"):** Rezolvată o problemă critică cauzată de noul SDK Google V2 care bloca parsarea imaginilor aruncând toate rezultatele direct în carantină.
- **Rate-Limiting Gemini V2:** Adăugat mecanism automat de sleep (15 secunde) atunci când API-ul gratuit Google atinge limitele HTTP 429.

*Note: Aplicația detectează automat provider-ul AI pe baza variabilei `GOOGLE_API_KEY` din `.env`. Dacă cheia există și e validă → Google Gemini. Dacă nu → Ollama local prin Docker.*

For more detailed DevOps and QA instructions, please refer to [README_ingineri.md](README_ingineri.md).
