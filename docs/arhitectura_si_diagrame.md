# Arhitectura și Fluxul de Lucru - ClutterKill v4

Acest document detaliază arhitectura de nivel înalt a aplicației ClutterKill și modul de funcționare la runtime. Arhitectura este concepută respectând principiul *Separation of Concerns*, delegând sarcinile de rețea, de disc și de procesare AI pe thread-uri asincrone pentru o experiență de utilizare fluidă.

## 1. Arhitectura Componentelor

Sistemul este împărțit în trei straturi logice majore (Layere) care comunică între ele printr-un thread manager central:

![Arhitectura Componentelor ClutterKill](arhitectura_componentelor.png)

### Detalierea Straturilor (Layere):
* **Layer-ul de Prezentare (UI):** Dezvoltat nativ în **PyQt6**, acest strat expune elementele vizuale (tab-urile pentru Reguli, Carantină, Progres) și preia input-ul utilizatorului.
* **Layer-ul Inteligenței Artificiale (AI):** Inima aplicației. Este format dintr-un ecosistem de agenți mici și specializați (arhitectură de tip *Multi-Agent*):
  * `Agent 0 (Compiler)`: Preia textul natural scris de utilizator și generează o structură clară de reguli (șablon JSON).
  * `Agent 1 (Extractor)`: Folosește PyMuPDF și OCR pentru a analiza fișierele și a returna un rezumat concis.
  * `Agent 2 (Decider)`: Motorul de logică, având rolul de a evalua rezumatul față de regulă și de a dicta acțiunea finală.
* **Layer-ul Core / Backend:** Gestionează persistența și interacțiunea cu sistemul de operare. Implementează mutarea fizică a fișierelor pe disc, salvarea log-urilor de carantină într-o bază de date **SQLite** și gestionarea unei stive de memorie (*Deque*) pentru anularea acțiunilor (Undo).

---

## 2. Fluxul de Lucru al Aplicației (App Workflow)

Diagrama de mai jos ilustrează ciclul de viață complet al unei operațiuni de scanare. Modelul evidențiază traseul logic pe care îl parcurge un fișier de la selectarea lui din sursă și până la destinația finală (sau carantină).

![Fluxul de Lucru ClutterKill](app_workflow.png)

### Procesul pas cu pas:
1. **Configurarea Inițială:** Utilizatorul scrie logica dorită într-un limbaj natural. `Agent 0` validează instant cerința și o stochează sub formă de regulă mașină.
2. **Dezlegarea Interfeței (Asincronism):** La apăsarea butonului "Start", aplicația instanțiază un `ScanWorker` (un *QThread* secundar). Astfel, interfața nu se blochează, iar utilizatorul poate vedea în timp real log-urile.
3. **Extragerea Datelor:** Documentul trece prin `Agent 1`, care reduce dimensiunea textului extras (prevenind astfel blocajele de memorie în LLM).
4. **Decizia Algoritmică:** `Agent 2` combină inputul extras cu regula curentă și emite o acțiune. Această bifurcație inteligentă previne erorile:
   * Documentele cu status cert (`Move`) sunt predate FileManager-ului.
   * Documentele cu grad de incertitudine (`Quarantine`) sunt izolate în siguranță în baza de date.
5. **Feedback Loop:** La finalizarea ciclului pentru fiecare fișier, semnalele emise actualizează vizual bara de progres și log-ul utilizatorului, restabilind starea "Idle" la final.
