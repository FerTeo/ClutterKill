import logging

logger = logging.getLogger(__name__)

def validate_proposal(decision: dict) -> list[str]:
    """
    Validare deterministă (bazată pe reguli de cod) a propunerii LLM-ului.
    Returnează o listă de erori. Dacă lista e goală, totul e corect.
    
    În viitor, acest agent poate folosi la rândul său un apel LLM mai mic 
    pentru verificări semantice ("ai halucinat acest număr de factură?").
    """
    errors = []
    
    if "error" in decision:
        return [f"Formatul returnat nu a fost un JSON valid: {decision.get('raw_output')}"]
        
    required_keys = ["new_name", "category", "confidence", "reasoning"]
    for key in required_keys:
        if key not in decision:
            errors.append(f"Lipsește cheia obligatorie: '{key}'")
            
    if "new_name" in decision:
        name = decision["new_name"]
        if not name.endswith((".pdf", ".jpg", ".png", ".webp", ".docx", ".txt")):
            errors.append(f"Numele '{name}' nu are o extensie validă.")
        if " " in name:
            errors.append(f"Numele '{name}' conține spații. Folosește underscore '_'.")
            
    if "category" in decision:
        valid_categories = ["factura", "contract", "curs", "reteta", "imagine", "unknown"]
        if decision["category"] not in valid_categories:
            errors.append(f"Categoria '{decision['category']}' este invalidă. Trebuie să fie una din: {valid_categories}")
            
    if "confidence" in decision:
        try:
            conf = float(decision["confidence"])
            if not (0.0 <= conf <= 1.0):
                errors.append("Confidence trebuie să fie între 0.0 și 1.0.")
        except ValueError:
            errors.append("Confidence trebuie să fie un număr float.")
            
    return errors
