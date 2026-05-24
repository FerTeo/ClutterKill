import os

from fpdf import FPDF


def create_fake_pdf():
    os.makedirs("test_data/source", exist_ok=True)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)

    pdf.cell(200, 10, text="Universitatea X - Curs MDS", align="C")
    pdf.ln(10)
    pdf.cell(200, 10, text="Semestrul 2 - Note de Curs", align="C")
    pdf.ln(10)
    pdf.cell(200, 10, text="Acesta este un document generat automat pentru testare.")

    file_path = os.path.join("test_data", "source", "Curs_MDS_Sem2.pdf")
    pdf.output(file_path)
    print(f"Fisierul PDF de test a fost creat cu succes: {file_path}")


if __name__ == "__main__":
    create_fake_pdf()
