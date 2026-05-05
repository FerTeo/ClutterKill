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

## 2. Configurarea Modelului Local (Gemma 2:2b)

Am creat fișierul `ai/Modelfile` bazat pe modelul `gemma2:2b`.
Acest fișier setează:
- **`temperature 0.1`**: Garantează răspunsuri precise, deterministe și lipsite de halucinații, ideale pentru clasificarea exactă a fișierelor.
- **`SYSTEM prompt`**: Forțează AI-ul să dea doar rezultate scurte și la obiect, fără conversații introductive inutile.

### Crearea și încărcarea modelului personalizat:
Odată ce containerul de Ollama rulează (pasul 1), executați următoarea comandă pentru a crea modelul `ck-model`:

```bash
docker exec -it clutterkill_ollama ollama create ck-model -f /app/ai/Modelfile
```

## 3. Verificarea Modelului

Pentru a verifica dacă modelul a fost compilat cu succes și este recunoscut de API-ul Ollama, executați:
```bash
curl http://localhost:11434/api/tags
```
Rezultatul (în format JSON) trebuie să includă modelul `ck-model` și modelul de bază `gemma2:2b`.

## 4. Testarea/Apelarea Modelului

Pentru a testa capacitățile modelului direct din terminal, fără a rula interfața grafică a aplicației, aveți două variante:

### Varianta A: Apel prin REST API
```bash
curl -X POST http://localhost:11434/api/generate -d '{
  "model": "ck-model",
  "prompt": "Clasifică documentul: Curs_MDS_Sem2.pdf"
}'
```

### Varianta B: Apel direct prin CLI (Ollama Run)
```bash
docker exec -it clutterkill_ollama ollama run ck-model "Clasifică documentul: Curs_MDS_Sem2.pdf"
```

## 5. Oprirea și curățarea
Când ați terminat sesiunea de dev/QA, puteți opri containerul folosind:
```bash
docker-compose down
```
Modelele vor fi păstrate în volumul Docker `ollama_data`. Dacă doriți să ștergeți și volumul (hard reset), folosiți `docker-compose down -v`.
