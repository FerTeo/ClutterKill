"""
Teste pentru QuarantineDB (core/quarantine_db.py).

Verifică operațiile CRUD și persistența datelor pe disc.
Fiecare test folosește o bază de date temporară (tmp_path) ca să nu
afecteze fișierul real quarantine.db din proiect.
"""

from core.quarantine_db import QuarantineDB


# ─── HELPER: creează o instanță cu DB temporar ────────────────────────


def _make_db(tmp_path):
    """Creează o instanță QuarantineDB cu fișierul .db într-un folder temporar."""
    return QuarantineDB(db_path=tmp_path / "test_quarantine.db")


# ─── TEST: Adăugare (CREATE) ──────────────────────────────────────────


def test_add_to_quarantine(tmp_path):
    db = _make_db(tmp_path)

    record_id = db.add(
        original_path="/Users/test/Downloads/factura.pdf",
        ai_proposed_name="Factura_Enel_2026.pdf",
        ai_proposed_folder="Facturi/Enel",
        reason="Factură utilități detectată",
    )

    assert record_id == 1  # Primul rând are ID-ul 1


def test_add_multiple(tmp_path):
    db = _make_db(tmp_path)

    id1 = db.add("/path/a.pdf", "A.pdf", "FolderA", "Reason A")
    id2 = db.add("/path/b.pdf", "B.pdf", "FolderB", "Reason B")
    id3 = db.add("/path/c.pdf", "C.pdf", "FolderC", "Reason C")

    assert id1 == 1
    assert id2 == 2
    assert id3 == 3


# ─── TEST: Citire (READ) ──────────────────────────────────────────────


def test_get_all(tmp_path):
    db = _make_db(tmp_path)

    db.add("/path/a.pdf", "A.pdf", "FolderA", "Reason A")
    db.add("/path/b.pdf", "B.pdf", "FolderB", "Reason B")

    results = db.get_all()

    assert len(results) == 2
    assert results[0]["original_path"] == "/path/a.pdf"
    assert results[1]["ai_proposed_name"] == "B.pdf"


def test_get_all_empty(tmp_path):
    db = _make_db(tmp_path)
    assert db.get_all() == []


def test_get_by_id(tmp_path):
    db = _make_db(tmp_path)

    record_id = db.add(
        "/Users/test/scan.pdf",
        "Diploma_Licenta.pdf",
        "Educatie/Diplome",
        "Document academic detectat",
    )

    result = db.get_by_id(record_id)

    assert result is not None
    assert result["id"] == record_id
    assert result["original_path"] == "/Users/test/scan.pdf"
    assert result["ai_proposed_name"] == "Diploma_Licenta.pdf"
    assert result["ai_proposed_folder"] == "Educatie/Diplome"
    assert result["reason"] == "Document academic detectat"


def test_get_by_id_not_found(tmp_path):
    db = _make_db(tmp_path)
    assert db.get_by_id(999) is None


# ─── TEST: Actualizare (UPDATE) ───────────────────────────────────────


def test_update_name(tmp_path):
    db = _make_db(tmp_path)

    record_id = db.add("/path/doc.pdf", "OldName.pdf", "OldFolder", "reason")
    success = db.update(record_id, ai_proposed_name="NewName.pdf")

    assert success is True

    updated = db.get_by_id(record_id)
    assert updated["ai_proposed_name"] == "NewName.pdf"
    # Celelalte câmpuri rămân neschimbate
    assert updated["ai_proposed_folder"] == "OldFolder"


def test_update_multiple_fields(tmp_path):
    db = _make_db(tmp_path)

    record_id = db.add("/path/doc.pdf", "Old.pdf", "OldFolder", "old reason")
    db.update(
        record_id,
        ai_proposed_name="New.pdf",
        ai_proposed_folder="NewFolder",
        reason="new reason",
    )

    updated = db.get_by_id(record_id)
    assert updated["ai_proposed_name"] == "New.pdf"
    assert updated["ai_proposed_folder"] == "NewFolder"
    assert updated["reason"] == "new reason"


def test_update_nonexistent(tmp_path):
    db = _make_db(tmp_path)
    assert db.update(999, ai_proposed_name="X.pdf") is False


def test_update_no_fields(tmp_path):
    db = _make_db(tmp_path)
    record_id = db.add("/path/doc.pdf", "Name.pdf", "Folder", "reason")
    # Dacă nu pasăm niciun câmp, returnează False
    assert db.update(record_id) is False


# ─── TEST: Ștergere (DELETE) ──────────────────────────────────────────


def test_remove(tmp_path):
    db = _make_db(tmp_path)

    record_id = db.add("/path/doc.pdf", "Name.pdf", "Folder", "reason")
    assert db.remove(record_id) is True
    assert db.get_by_id(record_id) is None


def test_remove_nonexistent(tmp_path):
    db = _make_db(tmp_path)
    assert db.remove(999) is False


def test_clear_all(tmp_path):
    db = _make_db(tmp_path)

    db.add("/path/a.pdf", "A.pdf", "FolderA", "")
    db.add("/path/b.pdf", "B.pdf", "FolderB", "")
    db.add("/path/c.pdf", "C.pdf", "FolderC", "")

    deleted_count = db.clear_all()

    assert deleted_count == 3
    assert db.get_all() == []


# ─── TEST: Persistență (datele rămân după reconectare) ────────────────


def test_data_persists_after_reopen(tmp_path):
    """
    Verificare critică: datele trebuie să existe și după ce
    închidem și redeschidem baza de date (simulează restart aplicație).
    """
    db_path = tmp_path / "persist_test.db"

    # Prima sesiune - adăugăm date
    db1 = QuarantineDB(db_path=db_path)
    db1.add(
        "/Users/test/Downloads/mystery.pdf",
        "Factura_Orange_2026.pdf",
        "Facturi/Telecom",
        "Factură telecom detectată",
    )

    # A doua sesiune - redeschidem baza de date (simulăm restart)
    db2 = QuarantineDB(db_path=db_path)
    results = db2.get_all()

    assert len(results) == 1
    assert results[0]["original_path"] == "/Users/test/Downloads/mystery.pdf"
    assert results[0]["ai_proposed_name"] == "Factura_Orange_2026.pdf"
    assert results[0]["ai_proposed_folder"] == "Facturi/Telecom"
    assert results[0]["reason"] == "Factură telecom detectată"
