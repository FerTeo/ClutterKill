import asyncio
import logging
import json
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv

# Configurăm logging pentru a vedea detaliile
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Încărcăm variabilele de mediu pentru a lua LLM-ul curent
load_dotenv()

from llm.config import get_llm
from agents.critic_system import run_critic_system
from llm.vector_store import vector_store
from agents.bbox_matcher import match_entities_to_bboxes

async def main():
    print("="*60)
    print("Testing Critic System & RAG")
    print("="*60)
    
    # 1. Obținem LLM-ul conform setărilor din .env
    llm = get_llm()
    
    # 2. Injectăm manual un exemplu anterior în VectorDB (ca să testăm RAG-ul)
    print("\n[1] Injecting previous decision into ChromaDB for Few-Shot...")
    vector_store.save_decision(
        document_text="S.C. EMAG IT RESEARCH S.R.L., Factura Fiscală Seria eMAG Număr 123456 din 15/05/2024. Total plată: 1500 RON.",
        decision_json={
            "new_name": "factura_EMAG_IT_RESEARCH_2024.pdf",
            "category": "factura",
            "entities": [{"label": "Nume Emitent", "text": "EMAG IT RESEARCH S.R.L."}, {"label": "Dată", "text": "15/05/2024"}],
            "confidence": 0.95,
            "reasoning": "Documentul este o factură fiscală de la EMAG. Am extras numele emitentului și anul."
        }
    )
    
    # 3. Definim un text nou care este un pic prea lung (pentru a testa și trunchierea, teoretic)
    # Dar aici trimitem un text scurt pentru test
    print("\n[2] Processing new document text...")
    new_document = """
    Spitalul Clinic Județean de Urgență.
    REȚETĂ MEDICALĂ
    Pacient: Ion Popescu
    Data: 20-08-2024
    Diagnostic: Răceală comună
    Medicamente: 
    1. Paracetamol 500mg, 1 cp la 8 ore.
    2. Vitamina C 1000mg, 1 cp pe zi.
    Semnătura și parafa medicului: Dr. Vasile Ionescu.
    """
    
    fake_word_bboxes = [[
        {"text": "Spitalul", "x0": 10, "y0": 10, "x1": 50, "y1": 20},
        {"text": "Clinic", "x0": 55, "y0": 10, "x1": 80, "y1": 20},
        {"text": "Județean", "x0": 85, "y0": 10, "x1": 130, "y1": 20},
        {"text": "de", "x0": 135, "y0": 10, "x1": 145, "y1": 20},
        {"text": "Urgență.", "x0": 150, "y0": 10, "x1": 200, "y1": 20},
        {"text": "REȚETĂ", "x0": 10, "y0": 30, "x1": 60, "y1": 40},
        {"text": "MEDICALĂ", "x0": 65, "y0": 30, "x1": 120, "y1": 40},
        {"text": "Pacient:", "x0": 10, "y0": 50, "x1": 50, "y1": 60},
        {"text": "Ion", "x0": 55, "y0": 50, "x1": 75, "y1": 60},
        {"text": "Popescu", "x0": 80, "y0": 50, "x1": 130, "y1": 60},
        {"text": "Data:", "x0": 10, "y0": 70, "x1": 40, "y1": 80},
        {"text": "20-08-2024", "x0": 45, "y0": 70, "x1": 110, "y1": 80},
    ]]

    try:
        # Aici apelăm tot lanțul: Context -> RAG -> Decider -> Validator -> Output
        final_decision = await run_critic_system(llm, new_document)
        
        print("\n" + "="*60)
        print("REZULTAT FINAL VALIDAT (De la LLM):")
        print(json.dumps(final_decision, indent=2, ensure_ascii=False))
        print("="*60)
        
        # Simulăm partea de matching cu coordonatele fizice
        print("\n[3] Matching Bounding Boxes (UI Output)...")
        if "entities" in final_decision:
            ui_output = match_entities_to_bboxes(final_decision["entities"], fake_word_bboxes)
            print("\n" + "="*60)
            print("REZULTAT FINAL PENTRU INTERFAȚĂ (BBoxes):")
            print(json.dumps(ui_output, indent=2, ensure_ascii=False))
            print("="*60)
            
    except Exception as e:
        print(f"\n Eroare în timpul testării: {e}")

if __name__ == "__main__":
    asyncio.run(main())
