import logging

logger = logging.getLogger(__name__)

def match_entities_to_bboxes(extracted_entities: list[dict], word_bboxes: list[list[dict]]) -> list[dict]:
    """
    Caută textul extras de LLM în coordonatele fizice returnate de parsere.
    
    extracted_entities: list de dicționare [{"label": "Dată", "text": "15.01.2024"}, ...]
    word_bboxes: listă paginată de dicționare [{"text": "foo", "x0": ..., "y0": ..., "x1": ..., "y1": ...}, ...]
    
    Returnează:
    Lista finală pentru interfața grafică, unde fiecărei entități i s-au adăugat coordonatele spațiale.
    """
    results = []
    
    # Aplatizăm lista pentru a putea căuta ușor secvențe de cuvinte
    flat_bboxes = []
    for page_bboxes in word_bboxes:
        flat_bboxes.extend(page_bboxes)
        
    for entity in extracted_entities:
        target_text = entity.get("text", "")
        if not target_text:
            continue
            
        # Despărțim textul căutat în cuvinte pentru a-l găsi în lista extrasă de pdfplumber/tesseract
        target_words = target_text.split()
        if not target_words:
            continue
            
        found_box = None
        n = len(target_words)
        
        # Căutăm o secvență continuă de cuvinte
        for i in range(len(flat_bboxes) - n + 1):
            match = True
            for j in range(n):
                # Comparație robustă (case-insensitive, fără semne de punctuație)
                bbox_word = flat_bboxes[i+j]["text"].lower().strip(".,:;-_")
                target_word = target_words[j].lower().strip(".,:;-_")
                if bbox_word != target_word:
                    match = False
                    break
            
            if match:
                # Calculăm bounding box-ul care cuprinde toate cuvintele secvenței
                x0 = min(flat_bboxes[i+j]["x0"] for j in range(n))
                y0 = min(flat_bboxes[i+j]["y0"] for j in range(n))
                x1 = max(flat_bboxes[i+j]["x1"] for j in range(n))
                y1 = max(flat_bboxes[i+j]["y1"] for j in range(n))
                
                found_box = {
                    "label": entity.get("label", "Unknown"),
                    "text": target_text,
                    "x0": round(float(x0), 2),
                    "y0": round(float(y0), 2),
                    "x1": round(float(x1), 2),
                    "y1": round(float(y1), 2)
                }
                break
                
        if found_box:
            results.append(found_box)
        else:
            logger.warning(f"Nu s-au găsit coordonate pentru entitatea: '{target_text}'")
            # Dacă LLM-ul a generat o entitate pe care nu o găsim (halucinație minoră / reformulare)
            # returnăm entitatea cu coordonate 0.
            results.append({
                "label": entity.get("label", "Unknown"),
                "text": target_text,
                "x0": 0.0,
                "y0": 0.0,
                "x1": 0.0,
                "y1": 0.0
            })
            
    return results
