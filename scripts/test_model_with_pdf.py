import fitz  # PyMuPDF
from langchain_community.llms import Ollama
import sys
import os


def test_model_with_pdf():
    pdf_path = "test_data/source/Curs_MDS_Sem2.pdf"

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

    print("🧠 Trimitere text extras către modelul local Ollama (ck-model)...")
    try:
        llm = Ollama(model="ck-model", base_url="http://ollama:11434")
        prompt = f"Pe baza acestui conținut, clasifică documentul și sugerează un folder potrivit. Fii extrem de scurt:\n\n{text}"

        response = llm.invoke(prompt)
        print("\n🤖 Răspuns AI:\n")
        print(response)
    except Exception as e:
        print(f"\n❌ Eroare la comunicarea cu Ollama: {e}")
        print(
            "Asigură-te că containerul ollama rulează și că modelul ck-model a fost creat."
        )


if __name__ == "__main__":
    test_model_with_pdf()
