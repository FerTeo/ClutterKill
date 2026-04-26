# 🧱 Platform & DevEx — Fundația Proiectului ClutterKill

> **Autor**: Inginer 5 — Platform & DevEx  
> **Issue-uri acoperite**: #501, #502, #503

---

## ⚡ Quick Start — Generează datele de test în 2 comenzi

> [!IMPORTANT]
> Începe de AICI. Înainte de orice altceva, rulează aceste comenzi ca să ai fișierele de test disponibile local.

**Condiție prealabilă**: Docker instalat și pornit ([docker.com/get-started](https://www.docker.com/get-started/))

### Pasul 1 — Construiește imaginea Docker (o singură dată)

```bash
docker compose build mock-generator
```

Ce face: descarcă Python 3.11-slim și instalează automat `fpdf2`, `Pillow` și `faker` într-un container izolat. Nu instalezi nimic pe mașina ta.

Durată: ~30–60 secunde la prima rulare, instant ulterior (imagine cached).

---

### Pasul 2 — Generează cele 510 fișiere de test

```bash
docker compose run --rm mock-generator
```

Ce face: rulează `tools/mock_generator.py` în container și salvează fișierele direct în `tests/mock_data/` pe mașina ta (prin volume mount). Containerul se șterge automat după rulare (`--rm`).

Durată: ~20–40 secunde.

---

### Verifică rezultatul

```
tests/mock_data/
├── text_pdfs/       ← 200 PDF-uri cu text căutabil (facturi, contracte, cursuri, rețete)
├── scanned_pdfs/    ← 150 PDF-uri simulate scan (imagine fără text)
├── images/          ← 100 imagini JPG / PNG / WEBP
├── corrupted/       ←  60 fișiere corupte simulate
└── metadata.json    ← ground-truth: tip, categorie, expected_readable pentru fiecare fișier
```

---

### Variante utile

```bash
# Regenerează (șterge și recreează datele)
docker compose run --rm mock-generator

# Generează mai puține fișiere (test rapid)
docker compose run --rm mock-generator python tools/mock_generator.py --text-pdfs 20 --scanned-pdfs 10 --images 10 --corrupted 5

# Salvează într-un alt director
docker compose run --rm mock-generator python tools/mock_generator.py --out-dir tests/mock_data_small

# Vizualizează log-ul în timp real (dacă vrei să urmărești progresul)
docker compose run mock-generator
```

> [!NOTE]
> `tests/mock_data/` este în `.gitignore` — nu se commit-ează în Git. Fiecare inginer generează datele local cu comanda de mai sus.

---

## 🤖 Pornește modelul AI local (Ollama)

Dacă lucrezi cu agenții AI din `ai/`, ai nevoie și de Ollama:

```bash
# Pornește Ollama în background (prima dată descarcă llama3.2 ~2 GB)
docker compose up -d ollama

# Verifică că rulează
curl http://localhost:11434/api/tags

# Oprește când ai terminat
docker compose down
```

---

## 🛠️ Setup complet (toate serviciile)

```bash
# 1. Instalează git hooks (o singură dată per developer)
pip install pre-commit && pre-commit install

# 2. Pornește Ollama
docker compose up -d ollama

# 3. Generează datele de test
docker compose run --rm mock-generator

# 4. Verifică API-ul bazei de date dummy
python -c "from database.dummy_repository import DatabaseManager; print(DatabaseManager().get_stats())"
# Output așteptat: {'total_processed': 12, 'moved_today': 1, 'in_quarantine': 2, 'failed': 1, 'success_rate': 0.917}
```

---

## 📋 Referință rapidă comenzi Docker

| Comandă | Ce face |
|---|---|
| `docker compose build mock-generator` | Construiește imaginea (prima dată) |
| `docker compose run --rm mock-generator` | Generează 510 fișiere de test |
| `docker compose up -d ollama` | Pornește Ollama în background |
| `docker compose logs -f ollama` | Urmărește log-urile Ollama |
| `docker compose down` | Oprește toate serviciile |
| `docker compose ps` | Vezi statusul serviciilor |

---

## 🔍 Detalii tehnice (citește mai jos pentru context complet)

---

# Documentație detaliată — Cele 3 Issue-uri

---

## De ce a fost nevoie de această fundație?

Înainte de a scrie orice logică de business — extracție de text, UI, baze de date, agenți AI — echipa s-a confruntat cu o problemă clasică în proiectele paralele:

> *„Nu pot testa scriptul de citire dacă nu am fișiere de test."*  
> *„Nu pot construi UI-ul dacă nu știu formatul exact al datelor din DB."*  
> *„Nu știu pe ce model AI rulăm — fiecare are altul instalat local."*

Cele 3 issue-uri rezolvă exact aceste blocaje, în ordine de prioritate.

---

## Issue #501 — `tools/mock_generator.py`

### Ce este

Un script Python standalone care generează o structură completă de fișiere false, dar realiste, în directorul `tests/mock_data/`.

### De ce a fost necesar

Fără fișiere de test, Inginerii 1 și 2 nu aveau pe ce să lucreze. Nu poți testa un parser de PDF dacă nu ai PDF-uri. Nu poți antrena sau evalua un agent de clasificare dacă nu ai documente cu categorii cunoscute.

### Ce generează concret

```
tests/mock_data/
├── text_pdfs/      # 200 PDF-uri cu text căutabil
├── scanned_pdfs/   # 150 PDF-uri cu imagine JPEG (fără text)
├── images/         # 100 imagini JPG / PNG / WEBP
├── corrupted/      #  60 fișiere cu extensie validă, conținut binar invalid
└── metadata.json   # ground-truth pentru fiecare fișier generat
```

**Total: 510 fișiere, ~50–100 MB** — bine sub orice limită de spațiu.

Fiecare PDF text conține conținut fals dar realist în română: facturi cu număr, emitent și total, contracte cu articole și clauze, cursuri universitare cu capitole, rețete medicale cu medicamente. Acestea sunt generate cu `faker` (localizat `ro_RO`) și scrise în PDF cu `fpdf2`.

PDF-urile scanate sunt imagini JPEG cu linii simulate de text și zgomot vizual (artefacte de scan), inserate într-un PDF fără strat de text — exact cum arată un document scanat real.

### Fișierul `metadata.json` — piesa cheie

La fiecare rulare se generează și un fișier de ground-truth:

```json
{
  "total_files": 510,
  "files": [
    {
      "filename": "factura_001_15_01_2024.pdf",
      "relative_path": "text_pdfs/factura_001_15_01_2024.pdf",
      "file_type": "text_pdf",
      "category": "factura",
      "expected_readable": true,
      "size_bytes": 42301,
      "metadata": {
        "emitent": "SC Construct SRL",
        "nr_factura": "3847",
        "total_ron": 1250.0
      }
    }
  ]
}
```

Câmpul `expected_readable` spune dacă un parser PDF ar trebui să extragă text din acel fișier (`true`) sau nu (`false` — pentru scanate și corupte). Aceasta este baza pentru evaluarea acurateței.

### Cum se rulează

```bash
# Din rădăcina repo-ului
python tools/mock_generator.py

# Cu parametri personalizați
python tools/mock_generator.py --text-pdfs 200 --scanned-pdfs 150 --images 100 --corrupted 60 --out-dir tests/mock_data
```

> ⚠️ `tests/mock_data/` este în `.gitignore`. Fiecare inginer generează datele local — nu se commit-ează în Git.

### Dependențe necesare

Adăugate deja în `ai/pyproject.toml`:

```toml
"fpdf2>=2.7.0"     # creare PDF-uri
"Pillow>=10.0.0"   # generare imagini și inserare JPEG în PDF
"faker>=25.0.0"    # date false realiste în română
```

```bash
cd ai && uv sync   # sau: pip install fpdf2 Pillow faker
```

---

## Issue #502 — `database/` — API Contract & Dummy Repository

### Ce este

Un set de fișiere Python în directorul `database/` care definesc **contractul de date** al aplicației: ce format au datele schimbate între backend, UI și agenți AI.

### De ce a fost necesar

Problema: Inginerul 3 (baza de date) și Inginerul 4 (UI) nu pot lucra în paralel dacă nu știu exact ce format au datele. Dacă Inginerul 3 nu a terminat SQL-ul, Inginerul 4 nu poate construi tabelele.

Soluția: separăm **interfața** (contractul) de **implementare** (SQL). Inginerul 4 primește date hardcodate cu structura exactă finală, construiește UI-ul pe ele, iar când Inginerul 3 termină SQL-ul — schimbă un singur fișier, restul rămâne intact.

### Fișierul 1: `database/models.py` — Schema

Trei dataclasse Python care definesc tipurile de date principale:

**`FileRecord`** — un fișier procesat de ClutterKill:
```python
@dataclass
class FileRecord:
    id: str                  # "f001"
    original_name: str       # "scan_001.pdf"
    new_name: str            # "factura_ACME_2024.pdf"
    category: FileCategory   # FileCategory.FACTURA
    confidence: float        # 0.94 — scorul AI
    status: FileStatus       # FileStatus.MOVED
    timestamp: str           # "2024-01-15T10:30:00Z"
    # ... și alte câmpuri
```

**`QuarantineRecord`** — un fișier pe care AI-ul nu a fost sigur:
```python
@dataclass
class QuarantineRecord:
    file_record: FileRecord   # fișierul asociat
    ai_suggestion: str        # ce nume a propus AI-ul
    reason: str               # de ce a ajuns în carantină
    user_decision: str | None # None | "approved" | "rejected"
```

**`ActivityEntry`** — o intrare în log (pentru funcția Undo):
```python
@dataclass
class ActivityEntry:
    file_record: FileRecord
    action: str               # "moved" | "quarantine_approved"
    undo_original_path: str   # path-ul original — necesar pentru Undo
    undo_available: bool      # False dacă fișierul sursă nu mai există
```

### Fișierul 2: `database/dummy_repository.py` — DatabaseManager

Clasa principală cu 7 metode. **Toate returnează date hardcodate acum** (12 fișiere, 2 în carantină, 6 activități), dar **semnăturile rămân identice și după migrarea la SQL**:

| Metodă | Returnează | Folosit în UI |
|---|---|---|
| `get_file_history(limit=50)` | `list[dict]` | Tab Activity History |
| `get_quarantine_items()` | `list[dict]` | Tab Quarantine Zone |
| `get_activity_log(limit=50)` | `list[dict]` | Log cu Undo disponibil |
| `get_stats()` | `dict` | Header dashboard |
| `add_file_record(record)` | `dict` | Apelat de agenți după procesare |
| `approve_quarantine(id, name)` | `dict` | Butonul „Approve" din UI |
| `undo_action(entry_id)` | `dict` | Butonul „Undo" din UI |

**Exemplu de utilizare imediată (fără nicio bază de date):**

```python
from database.dummy_repository import DatabaseManager

dm = DatabaseManager()

# Populează tabelul Activity History
history = dm.get_file_history(limit=50)
# → [{"id": "f001", "original_name": "scan_001.pdf", "new_name": "factura_ACME_2024.pdf", ...}, ...]

# Afișează statistici în header
stats = dm.get_stats()
# → {"total_processed": 12, "moved_today": 1, "in_quarantine": 2, "failed": 1, "success_rate": 0.917}

# Aprobă un fișier din carantină cu un nume editat manual
result = dm.approve_quarantine("q001", "factura_ACME_SRL_ian_2024.pdf")
# → {"status": "approved", "file_id": "q001", "final_name": "factura_ACME_SRL_ian_2024.pdf"}
```

### Ghid pentru Inginerul 3 — migrarea la SQL real

**Regula de aur: nu schimba semnăturile metodelor.** Inginerul 4 deja le apelează.

Pași concreți:

1. Caută toate comentariile `# TODO (Inginer 3)` în `dummy_repository.py` — fiecare metodă are query-ul SQL exact gata de copiat, de exemplu:

```python
# TODO (Inginer 3): Înlocuiește cu:
#   cursor = self._conn.execute(
#       "SELECT * FROM files ORDER BY timestamp DESC LIMIT ?", (limit,)
#   )
#   return [dict(row) for row in cursor.fetchall()]
```

2. Schema completă a tabelelor (`files`, `quarantine`, `activity`) este documentată în header-ul `dummy_repository.py`.

3. Înlocuiește `__init__` cu inițializarea conexiunii SQLite:

```python
def __init__(self, db_path: str | None = None) -> None:
    import sqlite3
    self.db_path = db_path or "clutterkill.db"
    self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
    self._conn.row_factory = sqlite3.Row
    self._create_tables()
```

4. Verificare rapidă după fiecare metodă migrată:

```bash
python -c "from database.dummy_repository import DatabaseManager; print(DatabaseManager('test.db').get_stats())"
```

---

## Issue #503 — Docker Compose & Git Hooks

### Ce este

Trei fișiere de configurare la rădăcina repo-ului care standardizează mediul de lucru al întregii echipe.

### De ce a fost necesar

Fără standardizare apar rapid trei categorii de probleme:
- **Conflicte de formatare**: un inginer folosește `'`, altul `"`, unul 2 spații, altul 4 — Git history poluat cu diff-uri de stil, nu de logică.
- **Modele AI diferite**: fiecare rulează alt model Ollama local — comportamentul agenților diferă între mașini.
- **„Merge, la mine"**: codul trece pe o mașină, pică pe alta din cauza dependențelor de sistem.

### Fișierul 1: `docker-compose.yml`

Pornește un server Ollama cu modelul `llama3.2` pre-descărcat:

```bash
# Pornire (prima dată durează ~5 min pentru descărcarea modelului)
docker compose up -d

# Verificare că Ollama rulează
curl http://localhost:11434/api/tags
```

Ce se întâmplă în spatele comenzii:
1. Containerul `ollama` pornește și expune API-ul pe portul `11434`
2. Containerul `ollama-init` așteaptă ca `ollama` să fie healthy, apoi rulează `ollama pull llama3.2` o singură dată
3. Modelul este salvat în volumul `ollama_data` — persistă între restart-uri

Toată echipa rulează **exact același model** (`llama3.2`), ceea ce elimină discrepanțele de comportament AI între mașini.

### Fișierul 2: `.ruff.toml`

Configurația linter-ului Ruff — înlocuitor modern și ultra-rapid pentru flake8 + isort + black:

```toml
line-length = 88
target-version = "py310"

[lint]
select = ["E", "W", "F", "I", "UP", "B", "SIM", "C4"]
```

Regulile active:
- **E/W** — erori și warning-uri de stil (pycodestyle)
- **F** — variabile nefolosite, import-uri lipsă (pyflakes)
- **I** — ordonare automată import-uri (isort)
- **UP** — sintaxă modernă Python (ex: `list[str]` în loc de `List[str]`)
- **B** — bug-uri comune și anti-patternuri
- **SIM/C4** — simplificări și comprehensions optime

```bash
# Verificare manuală
ruff check .

# Autofix (rezolvă automat ~80% din erori)
ruff check . --fix

# Formatare cod (similar black)
ruff format .
```

### Fișierul 3: `.pre-commit-config.yaml`

Hook-uri care rulează automat la fiecare `git commit`:

```
git commit -m "feat: adaug extracție text"
         ↓
[ruff lint + autofix]     → corectează automat erorile de stil
[ruff format]             → formatează codul uniform
[trailing-whitespace]     → elimină spații la finalul liniilor
[end-of-file-fixer]       → adaugă newline la finalul fișierelor
[check-yaml / check-toml] → validează fișierele de configurare
[check-added-large-files] → blochează fișiere > 5 MB accidentale
[no-mock-data]            → blochează commit-ul de tests/mock_data/
         ↓
commit acceptat ✅ (sau respins cu mesaj clar ❌)
```

**Instalare (o singură dată per developer):**

```bash
pip install pre-commit
pre-commit install
```

**Dacă un commit este respins** din cauza unui hook:
```bash
# Hook-ul a modificat fișiere automat → adaugă-le și reîncearcă
git add -A
git commit -m "feat: adaug extracție text"
```

---

## Rezumat — Ce deblochează fiecare livrabil

```
tools/mock_generator.py
  └─► Inginer 1: are fișiere pe care să testeze citirea în masă
  └─► Inginer 2: are PDF-uri și imagini din care să extragă text
  └─► Inginer 4: are PDF-uri vizuale pentru previzualizare în UI

database/dummy_repository.py + models.py
  └─► Inginer 4: construiește tabelele și UI-ul pe date reale acum
  └─► Inginer 3: are schema SQL + query-urile gata de implementat

docker-compose.yml + .ruff.toml + .pre-commit-config.yaml
  └─► Toată echipa: același model AI, același stil de cod, zero conflicte de formatare
```

---

## Checklist setup pentru un inginer nou

```bash
# 1. Clonează și instalează dependențele
git clone <url>
cd ClutterKill/ai
pip install uv && uv sync

# 2. Instalează git hooks
pip install pre-commit && pre-commit install

# 3. Pornește Ollama (prima rulare descarcă ~2 GB)
cd .. && docker compose up -d

# 4. Generează datele de test locale
python tools/mock_generator.py

# 5. Verifică că API-ul dummy funcționează
python -c "from database.dummy_repository import DatabaseManager; print(DatabaseManager().get_stats())"
# Așteptat: {'total_processed': 12, 'moved_today': 1, 'in_quarantine': 2, ...}
```
