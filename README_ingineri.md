# ClutterKill - Ghid pentru Ingineri (DevOps & QA)

Acest document descrie modul de configurare și utilizare a infrastructurii Docker și a modelului AI local (Ollama).

## 1. Setup Infrastructură cu Docker

Aplicația folosește `docker-compose` pentru a gestiona instanța locală de Ollama într-un mod eficient și cross-platform.

### Pornirea instanței Ollama
Asigurați-vă că aveți Docker instalat și pornit. În rădăcina proiectului, rulați:
```bash
docker-compose up -d
```
Această comandă va descărca imaginea oficială `ollama/ollama`, va expune portul `11434` pe localhost și va monta un volum permanent pentru stocarea modelelor, astfel încât să nu fie nevoie să le re-descărcați la fiecare pornire. De asemenea, folderul `./ai` este montat la `/app/ai` pentru acces direct la `Modelfile`.

### Configurarea mediului (Fișierul .env)
Proiectul folosește un fișier `.env` pentru a injecta direct variabilele de mediu în containerul Docker la rulare (cum ar fi comutarea între Ollama și Google API).

**Setup Inițial:**
1. Copiați fișierul șablon `.env.example` într-un nou fișier `.env`:
   ```bash
   cp .env.example .env
   ```
2. Editați fișierul `.env` și completați valorile dorite (ex: `AI_PROVIDER`, `GOOGLE_API_KEY`).
*Notă: Fișierul `.env` este adăugat în `.gitignore` și nu va fi comitat în repository pentru a proteja cheile secrete.*

**Aplicarea Modificărilor:**
Dacă editați fișierul `.env` în timp ce containerele rulează, trebuie să le reporniți pentru ca Docker să preia noile variabile:
```bash
docker-compose down
docker-compose up -d
```
*Dacă doriți să faceți un hard reset (ștergând și volumele asociate, precum baza de date a modelelor Ollama), rulați:*
```bash
docker-compose down -v
docker-compose up -d
```

## 2. Configurarea Modelelor Locale

ClutterKill folosește **3 modele AI personalizate** + 2 modele de bază:

### 2.1 Modelul de Clasificare — `ck-model` (Agent 0 & 2)

Bazat pe `gemma2:2b`. Fișierul `ai/Modelfile` setează:
- **`temperature 0.1`**: Răspunsuri precise, deterministe.
- **`SYSTEM prompt`**: Forțează AI-ul să returneze doar JSON structurat.

```bash
docker exec -it clutterkill_ollama ollama create ck-model -f /app/ai/Modelfile
```

### 2.2 Modelul de Extragere — `ck-extractor` (Agent 1)

Bazat pe `gemma2:2b`. Fișierul `ai/Modelfile.extractor` setează un prompt specializat pentru extragerea de entități din documente (Emitent, Dată, Sumă, Tip).

```bash
docker exec -it clutterkill_ollama ollama create ck-extractor -f /app/ai/Modelfile.extractor
```

### 2.3 Modelul Vision — `ck-vision` (Identificare Imagini)

Bazat pe **`llava:7b`** (~4.5GB). Acesta este un model **multimodal** capabil să "vadă" imagini și să identifice subiectul principal.

**Ce face:**
- Primește o imagine (JPEG/PNG/BMP) codificată în base64
- Returnează **un singur cuvânt** care descrie subiectul principal (ex: `dog`, `cat`, `sign`, `car`)
- Folosit doar pentru fișiere imagine, nu pentru PDF/DOCX

**Fișier configurare:** `ai/Modelfile.vision`
```
FROM llava:7b
PARAMETER temperature 0.1
SYSTEM "You identify images. Reply with ONE word only..."
```

**Setup:**
```bash
# 1. Pull modelul de bază llava:7b (~4.5GB, durează câteva minute)
docker exec -it clutterkill_ollama ollama pull llava:7b

# 2. Creează modelul personalizat ck-vision
docker exec -it clutterkill_ollama ollama create ck-vision -f /app/ai/Modelfile.vision
```

**Modul Python:** `ai/vision_tools.py` — funcția `describe_image(path)` gestionează:
- Codificarea imaginii în base64
- Detectarea MIME type (jpeg, png, bmp)
- Trimiterea către Ollama (local) sau Google Gemini (cloud) în funcție de `AI_PROVIDER`
- Returnarea descrierii ca string

**Note de performanță:**
- Prima inferență durează ~30-60s (încărcare model în RAM)
- Inferențele următoare: ~5-15s per imagine
- Necesită minim 8GB RAM disponibil

## 3. Verificarea Modelelor

Pentru a verifica dacă toate modelele au fost create cu succes:
```bash
curl http://localhost:11434/api/tags
```
Rezultatul (JSON) trebuie să includă: `ck-model`, `ck-extractor`, `ck-vision`, `gemma2:2b`, `llava:7b`.

## 4. Testarea/Apelarea Modelelor

Pentru a testa capacitățile modelelor direct din terminal:

### Varianta A: Test clasificare (ck-model)
```bash
docker exec -it clutterkill_ollama ollama run ck-model "Clasifică documentul: Curs_MDS_Sem2.pdf"
```

### Varianta B: Test Vision (ck-vision) - direct din CLI
```bash
# ck-vision nu poate fi testat direct din CLI fără imagine.
# Folosiți scriptul Python pentru test complet (Varianta C).
```

### Varianta C: Apel prin Python (citind PDF-ul fals generat)
Aceasta este metoda recomandată pentru a testa ecosistemul real (PyMuPDF extrage textul -> LangChain îl trimite către Ollama).

**Pasul 1:** Generați PDF-ul de test fals (dacă nu l-ați generat deja):
```bash
docker-compose run --rm app python scripts/create_test_pdf.py
```

**Pasul 2:** Rulați scriptul de test care citește fizic PDF-ul și întreabă AI-ul:
```bash
docker-compose run --rm app python scripts/test_model_with_pdf.py
```
*(Acest script validează că rețeaua internă Docker funcționează, librăria PyMuPDF poate extrage text, iar containerul comunică perfect cu instanța Ollama pentru a procesa informația extrasă).*

## 5. Testarea Cross-Platform (Backend / Teste Automate)

Pentru ca dezvoltatorii de pe macOS, Windows și Linux să aibă un mediu absolut identic, proiectul folosește un `Dockerfile` pentru serviciul `app`. Acesta instalează la nivel de sistem dependențele necesare precum `tesseract-ocr` (pentru OCR) și `poppler-utils` (pentru procesare PDF).

**ATENȚIE**: Containerul Docker **NU** este folosit pentru a rula interfața grafică (`main.py`). UI-ul se rulează exclusiv nativ. Containerul se folosește doar pentru teste automate și scripturi de dezvoltare!

**OBS:** momentan NU exista teste automate, dar Dockerfile este pregatit pentru ele.
### Rularea testelor automate (pytest):
```bash
docker-compose run --rm app pytest
```
Această comandă garantează că toți dezvoltatorii rulează testele în același mediu controlat.

### Rularea scripturilor utilitare (Ex: Generare PDF de test):
Pentru a testa fluxul de lucru rapid, am pregătit un script minimal care creează un PDF fals denumit "Curs_MDS_Sem2.pdf" în `test_data/source`. Rulați-l din mediul containerizat astfel:
```bash
docker-compose run --rm app python scripts/create_test_pdf.py
```
*(Asigurați-vă că folosiți containerul `app`, deoarece are librăria `fpdf` deja instalată din `requirements.txt`)*

**De reținut despre Ollama**:
Când ați testat comanda `ollama run ck-model ...` și ați primit eroarea *`manifest: file does not exist`*, aceasta **NU** s-a referit la fișierul PDF de pe disc, ci la faptul că **modelul AI `ck-model` nu fusese încă instalat/creat** pe instanța voastră de Ollama! 
Textul "Clasifică documentul: Curs_MDS_Sem2.pdf" este doar un text pe care i-l trimiteți agentului (el nu știe să caute fișiere pe disc, asta face scriptul Python). Asigurați-vă că rulați `docker exec -it clutterkill_ollama ollama create ck-model -f /app/ai/Modelfile` (Pasul 2) înainte de a-l apela!

## 6. Oprirea și curățarea
Când ați terminat sesiunea de dev/QA, puteți opri containerul folosind:
```bash
docker-compose down
```
Modelele vor fi păstrate în volumul Docker `ollama_data`. Dacă doriți să ștergeți și volumul (hard reset), folosiți `docker-compose down -v`.
