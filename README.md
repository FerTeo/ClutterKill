# 🔪 ClutterKill

> Un asistent desktop multi-agent care „citește" și înțelege conținutul fișierelor tale nestructurate, redenumindu-le și organizându-le automat prin modele AI care rulează **100% offline**.

---

## ⚠️ Problema

Haosul digital cauzat de acumularea zilnică a zeci de documente cu nume generice (ex: `scan_001.pdf` sau `final_v2.docx`), a căror deschidere, analiză și sortare manuală consumă timp și energie.

## 💡 Soluția

ClutterKill elimină dezordinea printr-o abordare inteligentă. Folosind un sistem de 2 agenți AI independenți, aplicația extrage contextul din fiecare document și aplică reguli vizuale stricte de redenumire stabilite de utilizator. Tot procesul are loc local, asigurând confidențialitatea totală a datelor.

---

## 🗂️ Structura proiectului

```
ClutterKill/
├── ai/                          # Agenții AI (LangGraph + Ollama)
│   ├── agents/                  # Orchestrator, DatabaseAgent, ReadmeAgent
│   ├── llm/                     # Factory LLM (OpenAI / Gemini / Local)
│   ├── mcp_server/              # Server MCP cu SQLite mock
│   ├── main.py                  # Entry point chat loop
│   └── pyproject.toml           # Dependențe Python (uv)
│
├── tools/
│   └── mock_generator.py        # Generează 510+ fișiere de test
│
├── tests/
│   └── mock_data/               # ⚠️ GENERAT LOCAL — nu este în Git
│       ├── text_pdfs/           # PDF-uri cu text căutabil
│       ├── scanned_pdfs/        # PDF-uri simulate scan (fără text)
│       ├── images/              # JPG / PNG / WEBP
│       ├── corrupted/           # Fișiere corupte simulate
│       └── metadata.json        # Ground-truth pentru fiecare fișier
│
├── database/
│   ├── models.py                # Schema contractului: FileRecord, QuarantineRecord, ActivityEntry
│   └── dummy_repository.py      # DatabaseManager cu date hardcodate (fără SQL real)
│
├── docker-compose.yml           # Ollama + llama3.2 (model AI local)
├── .ruff.toml                   # Configurație linting
└── .pre-commit-config.yaml      # Git hooks automate
```

---

## 🚀 Setup inițial (toți inginerii)

### 1. Clonează repo-ul și instalează dependențele

```bash
git clone <url-repo>
cd ClutterKill/ai

# Instalare cu uv (recomandat)
pip install uv
uv sync

# SAU cu pip clasic
pip install -e ".[dev]"
```

### 2. Instalează git hooks (o singură dată)

```bash
pip install pre-commit
pre-commit install
```

> De acum înainte, la fiecare `git commit`, codul este automat **lintat și formatat** cu Ruff. Dacă hook-ul modifică fișiere, adaugă-le din nou și reîncearcă commitul.

### 3. Pornește Ollama (model AI local)

```bash
docker compose up -d
```

> La **prima pornire**, se descarcă automat modelul `llama3.2` (~2 GB). Modelul este cached și nu se re-descarcă la restart. Ollama ascultă pe `localhost:11434`.

### 4. Generează datele de test

```bash
# Din rădăcina repo-ului
python tools/mock_generator.py
```

> Generează **510 fișiere** în `tests/mock_data/` (~50–100 MB). Directorul este în `.gitignore` — nu se commit-ează, se generează local de fiecare inginer.

---

## 🧱 Fundația pusă (Inginer 5 — Platform & DevEx)

Această secțiune documentează ce a fost livrat ca infrastructură de bază pentru restul echipei.

### ✅ Issue #501 — `tools/mock_generator.py`

Script Python care generează o structură completă de fișiere de test:

| Categorie | Nr. fișiere | Dimensiune/fișier | Descriere |
|---|---|---|---|
| Text PDFs | 200 | ~20–60 KB | Facturi, contracte, cursuri, rețete — text căutabil |
| Scanned PDFs | 150 | ~100–200 KB | Imagine JPEG în PDF, fără strat de text |
| Images | 100 | ~50–150 KB | JPG/PNG/WEBP cu conținut aleatoriu |
| Corrupted | 60 | ~10–50 KB | Extensie validă, conținut binar invalid |
| **Total** | **510** | **~50–100 MB** | |

Fiecare rulare generează și `tests/mock_data/metadata.json` cu **ground-truth** complet (tip real, categorie, dacă e readable etc.) — util pentru evaluarea acurateței agenților.

```bash
# Parametri opționali
python tools/mock_generator.py --text-pdfs 200 --scanned-pdfs 150 --images 100 --corrupted 60
python tools/mock_generator.py --out-dir /alt/director
```

---

### ✅ Issue #502 — `database/` — API Contract

Definește **interfața exactă** între backend și UI, fără SQL real.

#### `database/models.py` — Schema de date

Trei dataclasse Python care reprezintă contractul:

| Clasă | Folosit de | Descriere |
|---|---|---|
| `FileRecord` | Ing. 3, Ing. 4 | Un fișier procesat (id, original_name, new_name, category, confidence, status…) |
| `QuarantineRecord` | Ing. 4 (Quarantine Zone) | Fișier ambiguu + propunerea AI + decizia utilizatorului |
| `ActivityEntry` | Ing. 4 (Activity History) | Acțiune + calea originală pentru Undo |

#### `database/dummy_repository.py` — DatabaseManager

Clasă cu **7 metode** care returnează date hardcodate realiste (12 fișiere, 2 în carantină, 6 activități):

```python
from database.dummy_repository import DatabaseManager

dm = DatabaseManager()
dm.get_file_history(limit=50)   # → list[dict]  — tab Activity History
dm.get_quarantine_items()        # → list[dict]  — tab Quarantine Zone
dm.get_stats()                   # → dict        # dashboard header
dm.add_file_record(record)       # → dict        # {"id": ..., "status": "ok"}
dm.approve_quarantine(id, name)  # → dict        # {"status": "approved", ...}
dm.undo_action(entry_id)         # → dict        # {"status": "undone", ...}
dm.get_activity_log(limit=50)    # → list[dict]  # log complet cu Undo
```

> Fiecare metodă conține comentarii `# TODO (Inginer 3)` cu **query-ul SQL exact** care trebuie scris și pe ce tabelă.

---

### ✅ Issue #503 — Docker Compose & Git Hooks

| Fișier | Ce face |
|---|---|
| `docker-compose.yml` | Pornește Ollama + descarcă `llama3.2` automat la prima rulare |
| `.ruff.toml` | Linting cu Ruff: reguli E/W/F/I/UP/B/SIM, line-length 88, target py3.10 |
| `.pre-commit-config.yaml` | Hook-uri: ruff fix, ruff format, trailing-whitespace, YAML/TOML check, blocare fișiere >5MB și mock_data |

---

## 🔧 Ce trebuie să facă fiecare inginer

### Inginer 1 — Citire masă de fișiere

**Deblochează**: datele de test din `tests/mock_data/` după ce rulezi `mock_generator.py`.

- Implementează scriptul care parcurge un folder și citește fișierele în masă
- Folosește `tests/mock_data/metadata.json` ca ground-truth pentru a valida că fișierele text sunt citite corect și cele scanate sunt detectate ca non-readable
- Testele tale merg în `tests/` — datele de test sunt deja pregătite

---

### Inginer 2 — Extracție text pentru prompturi AI

**Deblochează**: PDF-urile text din `tests/mock_data/text_pdfs/` și imaginile din `tests/mock_data/images/`.

- Implementează extracția de text din PDF-uri text (ex: `pdfplumber`, `pymupdf`)
- Implementează OCR pentru PDF-urile scanate din `tests/mock_data/scanned_pdfs/` (ex: `pytesseract`)
- `metadata.json` îți spune pentru fiecare fișier dacă `expected_readable` este `True` sau `False` — folosește asta pentru a-ți evalua extracția

---

### Inginer 3 — Baza de date reală (SQLite)

**Deblochează**: `database/dummy_repository.py` + `database/models.py`.

1. **Nu schimba semnăturile metodelor** din `DatabaseManager` — UI-ul (Inginer 4) depinde de ele
2. Caută toate comentariile `# TODO (Inginer 3)` din `dummy_repository.py` — fiecare metodă are query-ul SQL exact gata de copiat
3. Schema tabelelor recomandată este documentată în header-ul `dummy_repository.py`
4. Pași de implementare:
   - Adaugă `sqlalchemy` sau `sqlite3` la dependențe
   - Înlocuiește `__init__` cu inițializarea conexiunii
   - Înlocuiește fiecare bloc de date hardcodate cu query-ul SQL corespunzător
   - Rulează smoke test-ul după fiecare metodă migrată:
     ```bash
     python -c "from database.dummy_repository import DatabaseManager; print(DatabaseManager('test.db').get_stats())"
     ```

---

### Inginer 4 — UI PyQt6

**Deblochează**: `database/dummy_repository.py` (date hardcodate imediat disponibile) + fișierele din `tests/mock_data/` pentru previzualizare.

- Importă `DatabaseManager` și construiește tabelele/listele pe datele reale returnate
- Structura JSON a fiecărei metode e documentată în docstring-ul metodei respective
- Pentru previzualizarea documentelor în Quarantine Zone, folosește fișierele din `tests/mock_data/`
- Când Inginer 3 termină implementarea SQL, înlocuiești doar import-ul — interfața rămâne identică

---

## 👤 User Stories

1. **Ca utilizator**, vreau să pot selecta printr-un buton de „Browse" un folder sursă (ex: *Downloads*) și un folder destinație (ex: *Arhiva_ClutterKill*), astfel încât aplicația să știe de unde preia haosul și unde livrează documentele organizate.
2. **Ca utilizator**, vreau să folosesc un panou de tip „Drag and Drop" pentru a trage blocuri logice (ex: `[An]`, `[Emitent]`, `[Tip]`) și a forma șabloane vizuale de redenumire, astfel încât să nu fiu nevoit să scriu expresii regulate (Regex) complicate.
3. **Ca utilizator**, vreau să pot salva aceste șabloane sub un nume personalizat (ex: „Regulă Facturi" sau „Regulă Cursuri"), astfel încât să le pot refolosi rapid la următoarele scanări, printr-un simplu click.
4. **Ca utilizator**, vreau să pot seta o limită de citire pentru documentele PDF foarte mari, extrăgând textul doar până la pagina 10, astfel încât să optimizez drastic timpul de procesare și memoria consumată de asistentul AI, obținând totuși datele esențiale pentru clasificare.
5. **Ca utilizator**, vreau să pot apăsa un buton principal de „Start Kill" și să văd imediat o bară de progres animată și numărul de fișiere rămase, astfel încât să știu în timp real cât mai durează procesarea folderului.
6. **Ca utilizator**, vreau ca în timpul scanării, interfața să îmi afișeze un log vizual (un terminal minimalist integrat) cu deciziile luate în timp real (ex: *„📄 doc_1.pdf → 🧠 Factură identificată → ✅ Mutat"*), astfel încât să am transparență asupra deciziilor AI-ului.
7. **Ca utilizator**, vreau să accesez un tab separat numit „Quarantine Zone", unde să văd o listă cu toate fișierele pe care AI-ul nu a fost 100% sigur cum să le clasifice, astfel încât deciziile ambigue să nu fie luate fără acordul meu.
8. **Ca utilizator**, vreau ca atunci când dau click pe un fișier aflat în Carantină, interfața să se împartă în două (Split-Screen): în stânga să văd o previzualizare a documentului, iar în dreapta propunerea AI-ului, astfel încât să pot lua o decizie rapidă de validare.
9. **Ca utilizator**, vreau să pot edita manual, într-un câmp de text, numele propus de AI în Carantină și apoi să apăs „Approve", astfel încât să corectez micile erori de clasificare înainte ca fișierul să fie mutat definitiv.
10. **Ca utilizator**, vreau să am un tab de „Activity History" unde să văd ultimele 50 de fișiere redenumite/mutate și să am un buton de „Undo" în dreptul fiecăruia, astfel încât să pot readuce instantaneu un fișier la locația și numele original dacă m-am răzgândit.