"""
tools/mock_generator.py
=======================
Generează o structură de fișiere de test în tests/mock_data/ pentru ClutterKill.

Categorii generate:
  - text_pdfs/    : ~200 PDF-uri cu text căutabil (facturi, contracte, cursuri, rețete)
  - scanned_pdfs/ : ~150 PDF-uri simulate scan (imagine JPEG fără strat de text)
  - images/       : ~100 imagini JPG/PNG/WEBP cu text suprapus
  - corrupted/    :  ~60 fișiere cu extensii valide dar conținut binar invalid

Total: 510 fișiere, estimat ~50-100 MB total.

Utilizare:
    python tools/mock_generator.py
    python tools/mock_generator.py --out-dir custom/path
"""

from __future__ import annotations

import argparse
import io
import json
import os
import random
import struct
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Dependențe opționale — instalate via: pip install fpdf2 Pillow faker
# ---------------------------------------------------------------------------
try:
    from fpdf import FPDF
except ImportError:
    sys.exit(
        "❌ Lipsește fpdf2. Rulează: pip install fpdf2\n"
        "   (sau: uv pip install fpdf2 din directorul ai/)"
    )

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit(
        "❌ Lipsește Pillow. Rulează: pip install Pillow\n"
        "   (sau: uv pip install Pillow din directorul ai/)"
    )

try:
    from faker import Faker
except ImportError:
    sys.exit(
        "❌ Lipsește faker. Rulează: pip install faker\n"
        "   (sau: uv pip install faker din directorul ai/)"
    )

# ---------------------------------------------------------------------------
# Configurare globală
# ---------------------------------------------------------------------------
SEED = 42
random.seed(SEED)

fake_ro = Faker("ro_RO")
fake_ro.seed_instance(SEED)

# Directorul implicit de output (relativ la rădăcina repo)
DEFAULT_OUT_DIR = Path(__file__).parent.parent / "tests" / "mock_data"


# ---------------------------------------------------------------------------
# Modele de metadate
# ---------------------------------------------------------------------------
@dataclass
class MockFileMetadata:
    filename: str
    relative_path: str          # relativ față de out_dir
    file_type: str              # "text_pdf" | "scanned_pdf" | "image" | "corrupted"
    category: str               # "factura" | "contract" | "curs" | "reteta" | "scan_document" | "photo" | "corrupted"
    expected_readable: bool     # True dacă un parser PDF/text ar trebui să extragă text
    size_bytes: int
    generated_at: str           # ISO 8601
    metadata: dict = field(default_factory=dict)  # câmpuri specifice categoriei


# ---------------------------------------------------------------------------
# Helpers comune
# ---------------------------------------------------------------------------
def _iso_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _random_date_str() -> str:
    """Dată aleatorie în ultimii 3 ani, format DD.MM.YYYY."""
    delta = timedelta(days=random.randint(0, 3 * 365))
    d = datetime(2022, 1, 1) + delta
    return d.strftime("%d.%m.%Y")


def _sanitize(name: str) -> str:
    """Elimină caractere invalide din numele de fișier."""
    for ch in r'\/:*?"<>|':
        name = name.replace(ch, "_")
    return name[:80]


# ---------------------------------------------------------------------------
# Generator 1 — Text PDFs
# ---------------------------------------------------------------------------
CATEGORIES_TEXT = ["factura", "contract", "curs_universitar", "reteta_medicala"]

_TEMPLATES: dict[str, callable] = {}


def _make_invoice_content(f: Faker) -> tuple[str, dict]:
    emitent = f.company()
    client = f.company()
    nr = random.randint(1000, 9999)
    data = _random_date_str()
    total = round(random.uniform(50, 5000), 2)
    items = [
        (f.bs().capitalize(), random.randint(1, 10), round(random.uniform(10, 500), 2))
        for _ in range(random.randint(2, 6))
    ]
    lines = [
        f"FACTURĂ FISCALĂ NR. {nr}",
        f"Data: {data}",
        f"Emitent: {emitent}",
        f"Client: {client}",
        "",
        "Nr.  Descriere                        Cant.  Preț/u   Total",
        "-" * 60,
    ]
    for i, (desc, qty, price) in enumerate(items, 1):
        lines.append(f"{i:<4} {desc:<33} {qty:<6} {price:<8.2f} {qty*price:.2f} RON")
    lines += ["", f"TOTAL DE PLATĂ: {total:.2f} RON", f"TVA inclus (19%): {total*0.19/1.19:.2f} RON"]
    return "\n".join(lines), {"emitent": emitent, "client": client, "nr_factura": str(nr), "data": data, "total_ron": total}


def _make_contract_content(f: Faker) -> tuple[str, dict]:
    parte1 = f.company()
    parte2 = f.company()
    data = _random_date_str()
    durata = random.choice(["6 luni", "12 luni", "24 luni", "nedeterminat"])
    valoare = round(random.uniform(500, 50000), 2)
    lines = [
        "CONTRACT DE PRESTĂRI SERVICII",
        f"Încheiat la data de {data}",
        "",
        f"ÎNTRE: {parte1}, denumită în continuare PRESTATOR,",
        f"ȘI:    {parte2}, denumită în continuare BENEFICIAR.",
        "",
        "Art. 1 — OBIECTUL CONTRACTULUI",
        f.paragraph(nb_sentences=4),
        "",
        "Art. 2 — DURATA",
        f"Contractul se încheie pe o perioadă de {durata}.",
        "",
        "Art. 3 — VALOAREA CONTRACTULUI",
        f"Valoarea totală: {valoare:.2f} RON, exclusiv TVA.",
        "",
        "Art. 4 — OBLIGAȚIILE PRESTATORULUI",
        f.paragraph(nb_sentences=3),
        "",
        "Art. 5 — CONFIDENȚIALITATE",
        f.paragraph(nb_sentences=2),
        "",
        "Semnat astăzi, " + data,
        f"PRESTATOR: {parte1}          BENEFICIAR: {parte2}",
    ]
    return "\n".join(lines), {"parte1": parte1, "parte2": parte2, "durata": durata, "valoare_ron": valoare}


def _make_course_content(f: Faker) -> tuple[str, dict]:
    materie = random.choice(["Algoritmi și Structuri de Date", "Baze de Date", "Ingineria Software",
                              "Rețele de Calculatoare", "Inteligență Artificială", "Sisteme de Operare"])
    prof = f.name()
    an = random.choice(["I", "II", "III"])
    sem = random.choice([1, 2])
    lines = [
        f"CURS: {materie}",
        f"Profesor: prof. dr. {prof}",
        f"Anul {an}, Semestrul {sem}",
        "",
        "CAPITOLUL 1 — Introducere",
        f.paragraph(nb_sentences=5),
        "",
        "1.1 Concepte de bază",
        f.paragraph(nb_sentences=4),
        "",
        "1.2 Aplicații practice",
        f.paragraph(nb_sentences=3),
        "",
        "CAPITOLUL 2 — Fundamente teoretice",
        f.paragraph(nb_sentences=6),
        "",
        "Bibliografie:",
        f"  [1] {f.last_name()}, {f.first_name()} — {f.bs().capitalize()}, {random.randint(2010,2024)}",
        f"  [2] {f.last_name()}, {f.first_name()} — {f.bs().capitalize()}, {random.randint(2010,2024)}",
    ]
    return "\n".join(lines), {"materie": materie, "profesor": prof, "an": an, "semestru": sem}


def _make_prescription_content(f: Faker) -> tuple[str, dict]:
    doctor = f.name()
    pacient = f.name()
    data = _random_date_str()
    medicamente = [
        (random.choice(["Amoxicilină", "Ibuprofen", "Paracetamol", "Metformin", "Atorvastatin",
                        "Omeprazol", "Amlodipină", "Lisinopril"]),
         f"{random.randint(1,3)}x{random.randint(1,3)}/zi",
         f"{random.randint(3,14)} zile")
        for _ in range(random.randint(1, 4))
    ]
    lines = [
        "REȚETĂ MEDICALĂ",
        f"Dr. {doctor}",
        f"Data: {data}",
        f"Pacient: {pacient}",
        f"CNP: {f.ssn()}",
        "",
        "PRESCRIPȚIE:",
    ]
    for med, doza, durata in medicamente:
        lines.append(f"  Rp/ {med} — {doza} — {durata}")
    lines += ["", "Semnătura și parafa medicului: ___________"]
    return "\n".join(lines), {"doctor": doctor, "pacient": pacient, "data": data,
                               "medicamente": [m[0] for m in medicamente]}


_CONTENT_MAKERS = {
    "factura": _make_invoice_content,
    "contract": _make_contract_content,
    "curs_universitar": _make_course_content,
    "reteta_medicala": _make_prescription_content,
}


def generate_text_pdfs(out_dir: Path, count: int = 200) -> list[MockFileMetadata]:
    """Generează PDF-uri cu text căutabil folosind fpdf2."""
    target = out_dir / "text_pdfs"
    target.mkdir(parents=True, exist_ok=True)
    records = []

    for i in range(count):
        category = random.choice(CATEGORIES_TEXT)
        content_text, meta_fields = _CONTENT_MAKERS[category](fake_ro)

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Helvetica", size=10)

        for line in content_text.split("\n"):
            # fpdf2 tratează liniile goale
            if line.strip() == "":
                pdf.ln(4)
            else:
                try:
                    pdf.multi_cell(0, 5, txt=line)
                except Exception:
                    pdf.multi_cell(0, 5, txt=line.encode("latin-1", errors="replace").decode("latin-1"))

        # Nume fișier: categorie + index + dată
        filename = _sanitize(f"{category}_{i+1:03d}_{_random_date_str().replace('.','_')}.pdf")
        filepath = target / filename
        pdf.output(str(filepath))

        size = filepath.stat().st_size
        records.append(MockFileMetadata(
            filename=filename,
            relative_path=f"text_pdfs/{filename}",
            file_type="text_pdf",
            category=category,
            expected_readable=True,
            size_bytes=size,
            generated_at=_iso_now(),
            metadata=meta_fields,
        ))

    print(f"  ✅ text_pdfs:    {count} fișiere generate")
    return records


# ---------------------------------------------------------------------------
# Generator 2 — Scanned PDFs (imagine JPEG fără text)
# ---------------------------------------------------------------------------
_SCAN_LABELS = ["Document scanat", "Formular", "Chitanță scan", "Contract scan",
                 "Adeverință", "Certificat", "Aprobare", "Notă internă"]


def _make_scan_image(width: int = 794, height: int = 1123) -> bytes:
    """Creează o imagine care simulează o pagină scanată (hârtie + text blur)."""
    # Fundal hârtie ușor gălbuie
    bg_color = (random.randint(240, 252), random.randint(238, 250), random.randint(220, 240))
    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Linii simulate de text (dreptunghiuri gri)
    y = 80
    while y < height - 100:
        line_width = random.randint(width // 2, width - 120)
        line_height = random.randint(6, 10)
        gray = random.randint(140, 200)
        draw.rectangle([60, y, 60 + line_width, y + line_height], fill=(gray, gray, gray))
        y += random.randint(18, 28)

    # Zgomot ușor (simulează artefacte scan)
    for _ in range(3000):
        x = random.randint(0, width - 1)
        y_n = random.randint(0, height - 1)
        v = random.randint(0, 60)
        img.putpixel((x, y_n), (v, v, v))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=random.randint(70, 90))
    return buf.getvalue()


def generate_scanned_pdfs(out_dir: Path, count: int = 150) -> list[MockFileMetadata]:
    """Generează PDF-uri simulate scan (fără text căutabil)."""
    target = out_dir / "scanned_pdfs"
    target.mkdir(parents=True, exist_ok=True)
    records = []

    for i in range(count):
        label = random.choice(_SCAN_LABELS)
        jpeg_bytes = _make_scan_image()

        pdf = FPDF(unit="pt", format="A4")
        pdf.add_page()
        # Inserează imaginea JPEG direct — fără text
        with io.BytesIO(jpeg_bytes) as buf:
            pdf.image(buf, x=0, y=0, w=595, h=842, type="JPEG")

        filename = _sanitize(f"scan_{label.lower().replace(' ','_')}_{i+1:03d}.pdf")
        filepath = target / filename
        pdf.output(str(filepath))

        size = filepath.stat().st_size
        records.append(MockFileMetadata(
            filename=filename,
            relative_path=f"scanned_pdfs/{filename}",
            file_type="scanned_pdf",
            category="scan_document",
            expected_readable=False,   # OCR necesar
            size_bytes=size,
            generated_at=_iso_now(),
            metadata={"label": label},
        ))

    print(f"  ✅ scanned_pdfs: {count} fișiere generate")
    return records


# ---------------------------------------------------------------------------
# Generator 3 — Images
# ---------------------------------------------------------------------------
_IMAGE_SUBJECTS = ["screenshot", "poza_document", "diagrama", "tabel", "grafic", "fotografie"]
_IMAGE_FORMATS = [("JPEG", ".jpg"), ("PNG", ".png"), ("WEBP", ".webp")]


def _make_image(width: int = 800, height: int = 600, label: str = "") -> tuple[bytes, str]:
    fmt_name, ext = random.choice(_IMAGE_FORMATS)
    # Fundal culoare aleatorie
    r, g, b = random.randint(30, 220), random.randint(30, 220), random.randint(30, 220)
    img = Image.new("RGB", (width, height), color=(r, g, b))
    draw = ImageDraw.Draw(img)

    # Forme geometrice decorative
    for _ in range(random.randint(3, 8)):
        x0, y0 = random.randint(0, width), random.randint(0, height)
        x1, y1 = random.randint(0, width), random.randint(0, height)
        cr, cg, cb = random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
        draw.rectangle([min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)],
                        outline=(cr, cg, cb), width=2)

    # Text suprapus
    try:
        draw.text((20, 20), label, fill=(255, 255, 255))
        draw.text((20, 50), fake_ro.sentence(nb_words=5), fill=(200, 200, 200))
    except Exception:
        pass

    buf = io.BytesIO()
    save_kwargs = {"quality": random.randint(75, 95)} if fmt_name in ("JPEG", "WEBP") else {}
    img.save(buf, format=fmt_name, **save_kwargs)
    return buf.getvalue(), ext


def generate_images(out_dir: Path, count: int = 100) -> list[MockFileMetadata]:
    """Generează imagini JPG/PNG/WEBP cu conținut aleatoriu."""
    target = out_dir / "images"
    target.mkdir(parents=True, exist_ok=True)
    records = []

    for i in range(count):
        subject = random.choice(_IMAGE_SUBJECTS)
        img_bytes, ext = _make_image(label=subject)

        filename = f"{subject}_{i+1:03d}{ext}"
        filepath = target / filename
        filepath.write_bytes(img_bytes)

        size = filepath.stat().st_size
        records.append(MockFileMetadata(
            filename=filename,
            relative_path=f"images/{filename}",
            file_type="image",
            category="photo",
            expected_readable=False,
            size_bytes=size,
            generated_at=_iso_now(),
            metadata={"subject": subject, "format": ext.lstrip(".")},
        ))

    print(f"  ✅ images:       {count} fișiere generate")
    return records


# ---------------------------------------------------------------------------
# Generator 4 — Corrupted files
# ---------------------------------------------------------------------------
_CORRUPT_EXTENSIONS = [".pdf", ".docx", ".xlsx", ".pptx", ".pdf", ".pdf"]  # PDF mai frecvent


def generate_corrupted(out_dir: Path, count: int = 60) -> list[MockFileMetadata]:
    """Generează fișiere cu extensie validă dar conținut binar random."""
    target = out_dir / "corrupted"
    target.mkdir(parents=True, exist_ok=True)
    records = []

    for i in range(count):
        ext = random.choice(_CORRUPT_EXTENSIONS)
        # Conținut: header parțial valid + junk
        size = random.randint(512, 50 * 1024)
        junk = random.randbytes(size)

        # Unele fișiere au header-ul corect dar body corupt
        if ext == ".pdf" and random.random() < 0.5:
            # Header PDF valid, dar EOF lipsă
            junk = b"%PDF-1.4\n" + junk[:size - 9]
        elif ext == ".docx" and random.random() < 0.5:
            # Signatură ZIP parțial validă
            junk = b"PK\x03\x04" + junk[:size - 4]

        filename = f"corupt_{i+1:03d}{ext}"
        filepath = target / filename
        filepath.write_bytes(junk)

        actual_size = filepath.stat().st_size
        records.append(MockFileMetadata(
            filename=filename,
            relative_path=f"corrupted/{filename}",
            file_type="corrupted",
            category="corrupted",
            expected_readable=False,
            size_bytes=actual_size,
            generated_at=_iso_now(),
            metadata={"intended_extension": ext, "corruption_type": "random_binary"},
        ))

    print(f"  ✅ corrupted:    {count} fișiere generate")
    return records


# ---------------------------------------------------------------------------
# Scriere metadata.json
# ---------------------------------------------------------------------------
def write_metadata(out_dir: Path, all_records: list[MockFileMetadata]) -> None:
    meta_path = out_dir / "metadata.json"
    payload = {
        "generated_at": _iso_now(),
        "seed": SEED,
        "total_files": len(all_records),
        "summary": {
            "text_pdf": sum(1 for r in all_records if r.file_type == "text_pdf"),
            "scanned_pdf": sum(1 for r in all_records if r.file_type == "scanned_pdf"),
            "image": sum(1 for r in all_records if r.file_type == "image"),
            "corrupted": sum(1 for r in all_records if r.file_type == "corrupted"),
        },
        "total_size_bytes": sum(r.size_bytes for r in all_records),
        "files": [asdict(r) for r in all_records],
    }
    meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    total_mb = payload["total_size_bytes"] / (1024 * 1024)
    print(f"\n  📄 metadata.json scris: {len(all_records)} intrări, {total_mb:.1f} MB total")


# ---------------------------------------------------------------------------
# Intrare principală
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generează fișiere de test pentru ClutterKill",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--out-dir", type=Path, default=DEFAULT_OUT_DIR,
        help=f"Director de output (implicit: {DEFAULT_OUT_DIR})"
    )
    parser.add_argument("--text-pdfs",    type=int, default=200)
    parser.add_argument("--scanned-pdfs", type=int, default=150)
    parser.add_argument("--images",       type=int, default=100)
    parser.add_argument("--corrupted",    type=int, default=60)
    args = parser.parse_args()

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🔪 ClutterKill Mock Generator")
    print(f"   Output: {out_dir.resolve()}\n")

    all_records: list[MockFileMetadata] = []
    all_records += generate_text_pdfs(out_dir, args.text_pdfs)
    all_records += generate_scanned_pdfs(out_dir, args.scanned_pdfs)
    all_records += generate_images(out_dir, args.images)
    all_records += generate_corrupted(out_dir, args.corrupted)

    write_metadata(out_dir, all_records)

    total = len(all_records)
    print(f"\n✅ Done! {total} fișiere generate în {out_dir.resolve()}")
    if total < 500:
        print(f"⚠️  Atenție: {total} < 500 fișiere. Crește parametrii --text-pdfs / --scanned-pdfs.")


if __name__ == "__main__":
    main()
