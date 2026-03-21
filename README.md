# 🔪 ClutterKill

> Un asistent desktop multi-agent care "citește" și înțelege conținutul fișierelor tale nestructurate, redenumindu-le și organizându-le automat prin modele AI care rulează 100% offline.

---

## ⚠️ Problema
Haosul digital cauzat de acumularea zilnică a zeci de documente cu nume generice (ex: `scan_001.pdf` sau `final_v2.docx`), a căror deschidere, analiză și sortare manuală consumă timp și energie.

## 💡 Soluția
ClutterKill elimină dezordinea printr-o abordare inteligentă. Folosind un sistem de 2 agenți AI independenți, aplicația extrage contextul din fiecare document și aplică reguli vizuale stricte de redenumire stabilite de utilizator. Tot procesul are loc local, asigurând confidențialitatea totală a datelor.

---

## 👤 User Stories

1. **Ca utilizator**, vreau să pot selecta printr-un buton de „Browse” un folder sursă (ex: *Downloads*) și un folder destinație (ex: *Arhiva_ClutterKill*), astfel încât aplicația să știe de unde preia haosul și unde livrează documentele organizate.
2. **Ca utilizator**, vreau să folosesc un panou de tip „Drag and Drop” pentru a trage blocuri logice (ex: `[An]`, `[Emitent]`, `[Tip]`) și a forma șabloane vizuale de redenumire, astfel încât să nu fiu nevoit să scriu expresii regulate (Regex) complicate.
3. **Ca utilizator**, vreau să pot salva aceste șabloane sub un nume personalizat (ex: „Regulă Facturi” sau „Regulă Cursuri”), astfel încât să le pot refolosi rapid la următoarele scanări, printr-un simplu click.
4. **Ca utilizator**, vreau să pot seta o limită de citire pentru documentele PDF foarte mari, extrăgând textul doar până la pagina 10, astfel încât să optimizez drastic timpul de procesare și memoria consumată de asistentul AI, obținând totuși datele esențiale pentru clasificare.
5. **Ca utilizator**, vreau să pot apăsa un buton principal de „Start Kill” și să văd imediat o bară de progres animată și numărul de fișiere rămase, astfel încât să știu în timp real cât mai durează procesarea folderului.
6. **Ca utilizator**, vreau ca în timpul scanării, interfața să îmi afișeze un log vizual (un terminal minimalist integrat) cu deciziile luate în timp real (ex: *„📄 doc_1.pdf -> 🧠 Factură identificată -> ✅ Mutat”*), astfel încât să am transparență asupra deciziilor AI-ului.
7. **Ca utilizator**, vreau să accesez un tab separat numit „Quarantine Zone”, unde să văd o listă cu toate fișierele pe care AI-ul nu a fost 100% sigur cum să le clasifice, astfel încât deciziile ambigue să nu fie luate fără acordul meu.
8. **Ca utilizator**, vreau ca atunci când dau click pe un fișier aflat în Carantină, interfața să se împartă în două (Split-Screen): în stânga să văd o previzualizare a documentului, iar în dreapta propunerea AI-ului, astfel încât să pot lua o decizie rapidă de validare.
9. **Ca utilizator**, vreau să pot edita manual, într-un câmp de text, numele propus de AI în Carantină și apoi să apăs „Approve”, astfel încât să corectez micile erori de clasificare înainte ca fișierul să fie mutat definitiv.
10. **Ca utilizator**, vreau să am un tab de „Activity History” unde să văd ultimele 50 de fișiere redenumite/mutate și să am un buton de „Undo” în dreptul fiecăruia, astfel încât să pot readuce instantaneu un fișier la locația și numele original dacă m-am răzgândit.