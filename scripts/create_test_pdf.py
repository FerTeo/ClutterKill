from fpdf import FPDF
import os


def create_fake_pdf():
    # Ne asigurăm că există directorul (în caz că vrem să organizăm mai târziu)
    os.makedirs("test_data/source", exist_ok=True)

    pdf = FPDF()
    pdf.add_page()

    # FPDF default include doar câteva fonturi. Arial e un alias pentru Helvetica.
    pdf.set_font("Helvetica", size=12)

    pdf.cell(200, 10, txt="Universitatea X - Curs MDS", align="C")
    pdf.ln(10)
    pdf.cell(200, 10, txt="Semestrul 2 - Note de Curs", align="C")
    pdf.ln(10)
    pdf.cell(200, 10, txt="Acesta este un document generat automat pentru testare.")

    file_path = "Curs_MDS_Sem2.pdf"
    pdf.output(file_path)
    print(f"✅ Fișierul PDF de test a fost creat cu succes: {file_path}")


if __name__ == "__main__":
    create_fake_pdf()
