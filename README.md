# ClutterKill

ClutterKill is a multi-agent desktop application for automated file organization using local AI. 

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

ClutterKill/
├── 📄 main.py                  # Punctul de intrare: lansează interfața grafică PyQt6
├── 📄 requirements.txt         # Dependințele: PyQt6, langchain, pydantic, pymupdf, pytest etc.
├── 📄 docker-compose.yml       # Setup-ul pentru containerul Ollama local
├── 📄 .gitignore               # Fișiere de ignorat (venv, test_data/, __pycache__)
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
│   ├── 📄 Modelfile            # Definiția modelului Gemma 2:2b (temperature 0.1)
│   ├── 📄 llm_config.py        # Conexiunea LangChain cu localhost:11434
│   ├── 📄 tools.py             # Funcții: extract_text_from_pdf, extract_text_from_image
│   ├── 📄 agent_compiler.py    # AGENT 0: Traduce promptul natural în JSON (Reguli)
│   ├── 📄 agent_extractor.py   # AGENT 1: Rezumă fișierul fizic
│   └── 📄 agent_decider.py     # AGENT 2: Combină Agent 0 cu Agent 1 și ia decizia finală
│
├── 📂 core/                    # LOGICA BACKEND (Sistemul de operare)
│   ├── 📄 __init__.py
│   ├── 📄 file_manager.py      # Mutare, redenumire (cross-platform cu pathlib)
│   ├── 📄 undo_manager.py      # Logica pentru stiva de Undo (ultimele 50 acțiuni)
│   └── 📄 quarantine_db.py     # Baza de date SQLite pentru fișierele nesigure
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
