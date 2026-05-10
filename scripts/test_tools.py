import os
from PIL import Image, ImageDraw, ImageFont
from ai.tools import extract_text_from_pdf, extract_text_from_image

def create_test_image(path: str):
    """Creează o imagine simplă cu text pentru testarea OCR-ului."""
    img = Image.new('RGB', (400, 150), color = (255, 255, 255))
    d = ImageDraw.Draw(img)
    # Folosim fontul default deoarece Pillow îl are mereu la îndemână
    d.text((20, 50), "Testare extragere imagine OCR", fill=(0, 0, 0))
    d.text((20, 80), "Factura Nr: 12345", fill=(0, 0, 0))
    img.save(path)
    print(f"✅ Imagine de test creată: {path}")

def main():
    print("--- Testare Tool-uri Extracție ---")
    
    # 1. Testare PDF
    pdf_path = "Curs_MDS_Sem2.pdf"
    if not os.path.exists(pdf_path):
        print(f"Atenție: {pdf_path} nu a fost găsit. Te rog generează-l mai întâi cu create_test_pdf.py.")
    else:
        print(f"\nExtragere text din {pdf_path}:")
        pdf_text = extract_text_from_pdf(pdf_path)
        print(f"[{pdf_text}]")

    # 2. Testare Imagine
    img_path = "test_ocr.png"
    create_test_image(img_path)
    print(f"\nExtragere text din {img_path}:")
    img_text = extract_text_from_image(img_path)
    print(f"[{img_text}]")

if __name__ == "__main__":
    main()
