from ai.agent_extractor import ExtractorAgent

def test_emag_invoice():
    emag_text = """
    Factura Fiscala
    Seria eMAG Nr. 123456789
    Data: 15.10.2023
    
    Furnizor: Dante International SA (eMAG)
    CUI: RO1111111
    
    Cumparator: Popescu Ion
    Adresa: Bucuresti, Sector 1
    
    Produse:
    1. Laptop Lenovo ThinkPad - 1 buc - 3500.00 RON
    2. Mouse Wireless Logitech - 1 buc - 150.00 RON
    
    Total de plata: 3650.00 RON
    """

    print("📄 Procesare conținut factură eMAG...")
    
    try:
        agent = ExtractorAgent()
        result = agent.extract(emag_text)

        print("\n🤖 Rezultat complet JSON (Pydantic):")
        print(f"Tip Document: {result.document_type}")
        print(f"Summary Brut: {result.summary}")
        
        print("\n🎯 Verificare Task 9 (Strict 200 caractere):")
        technical_summary = result.get_technical_summary()
        print(f"Length: {len(technical_summary)} chars")
        print(f"Output: {technical_summary}")

    except Exception as e:
        print(f"\n❌ Eroare la comunicarea cu ExtractorAgent: {e}")

if __name__ == "__main__":
    test_emag_invoice()
