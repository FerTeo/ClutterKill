import fitz  # PyMuPDF
import sys
import os
from ai.agent_extractor import ExtractorAgent


def test_extractor_with_pdf():
    pdf_path = "Curs_MDS_Sem2.pdf"

    # Verificăm dacă fișierul există
    if not os.path.exists(pdf_path):
        print(f"Eroare: Fișierul {pdf_path} nu a fost găsit!")
        print(
            "Rulează mai întâi: docker-compose run --rm app python scripts/create_test_pdf.py"
        )
        sys.exit(1)

    print(f"📄 Extragere text din {pdf_path} folosind PyMuPDF...")
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()

    print("---------- CONTINUT EXTRAS ----------")
    print(text.strip())
    print("-------------------------------------\n")

    print("🧠 Trimitere text extras către ExtractorAgent (Ollama: ck-extractor)...")
    try:
        agent = ExtractorAgent()
        result = agent.extract(text)

        print("\n🤖 Răspuns AI Extractor:\n")
        print(f"{'=' * 60}")
        print(f"Document type : {result.document_type}")
        print(f"Summary       : {result.summary}")
        print(f"Thinking      : {result.raw_thinking[:300]}…")
        print(f"{'=' * 60}")
        for ent in result.entities:
            print(
                f"  {ent.field_name:20s} = {ent.value:30s}  (conf: {ent.confidence:.1f})"
            )

    except Exception as e:
        print(f"\n❌ Eroare la comunicarea cu ExtractorAgent: {e}")
        print(
            "Asigură-te că containerul ollama rulează și că modelul ck-extractor a fost creat."
        )


if __name__ == "__main__":
    test_extractor_with_pdf()
