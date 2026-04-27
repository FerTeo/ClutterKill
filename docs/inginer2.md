# Jurnal de Dezvoltare: Inginerul 2 (Lead AI & MLOps Architect)

## 🚀 Rezumatul Dezvoltării (Modulul AI & MLOps)

Pe parcursul acestui branch, am pus la punct inima sistemului inteligent de procesare a documentelor (100% offline). 

### 1. Ce am implementat:
* **The Critic Multi-Agent System**: Am implementat bucla decizională folosind LangGraph (`critic_system.py`). Sistemul folosește un agent `Decider` care emite propuneri de redenumire și un `Validator` determinist care verifică structura JSON-ului (forțând corectarea erorilor în maxim 3 iterații).
* **RAG (Retrieval-Augmented Generation)**: Am integrat `ChromaDB` și modelul `all-MiniLM-L6-v2` pentru a rula local. Sistemul memorează deciziile de redenumire anterioare și le folosește ca *few-shot examples* pentru a spori precizia (fără halucinații).
* **Explainable Quarantine (Cerința UI)**: 
  * Parserele (`pdfplumber` și `pytesseract`) au fost modificate să extragă coordonatele fizice (`x0, y0, x1, y1`) ale fiecărui cuvânt.
  * Modelul de decizie a fost instruit să extragă entitățile cheie (ex: CUI, Dată, Emitent).
  * Noul modul `bbox_matcher.py` combină decizia semantică a AI-ului cu coordonatele spațiale, generând exact structura de care are nevoie Frontend-ul pentru a desena casetele galbene.

### 2. Issue-uri / Epics rezolvate:
* **Issue #401 & #402 (Explainable Quarantine)**: Furnizarea coordonatelor Bounding Box către interfața grafică.
* **Epic: RAG Core**: Salvarea și regăsirea istorică a deciziilor în baza de date vectorială locală.
* **Story: Determinism & JSON Enforcement**: Prevenirea output-ului incorect (tip Markdown sau halucinat) din partea Llama 3.2.
* **Bug Fix**: Corectată eroarea de formatare `UnicodeEncodeError` pe mediile Windows (pentru diacritice) prin forțarea UTF-8 pe `stdout`.

---

## 💻 Cum pot rula ceilalți ingineri codul

Colegii tăi pot testa fluxul complet de la cap la coadă foarte simplu. Pașii pe care trebuie să îi urmeze sunt:

**1. Pornirea infrastructurii LLM**
Trebuie să aibă Docker instalat și să pornească containerul Ollama cu modelul `llama3.2`:
```bash
# Din rădăcina proiectului
docker-compose up -d
```
*(Notă: Containerul `ollama-init` va descărca automat modelul local la prima rulare)*.

**2. Instalarea dependențelor AI**
Sistemul folosește managerul `uv` (sau pip/poetry). Trebuie să se asigure că sunt în folderul `/ai`:
```bash
cd ai
uv sync
```

**3. Rularea testului End-to-End**
Pentru a vedea cu ochii lor cum funcționează întreg fluxul (creare Context -> RAG vector store -> Prompt LLM -> Validare Critic -> Matching Bounding Boxes), trebuie doar să ruleze scriptul de test:
```bash
uv run test_critic.py
```
Aici vor putea vedea în consolă exact JSON-ul validat final și formatul cu coordonate `x0, y0, x1, y1` gata să fie consumat de colegul de pe PyQt6!
