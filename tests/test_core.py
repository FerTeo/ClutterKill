"""
Teste pentru mutarea fișierelor — core/file_manager.py

Acoperire:
  - Mutare și redenumire de bază (happy path)
  - Crearea automată a subdirectoarelor destinație
  - Conținut păstrat după mutare
  - Eroare la sursă inexistentă
  - Mutare cu același nume (fără redenumire)
  - Mutare fișier binar
  - Mutare mai multor fișiere succesiv
  - Înregistrarea acțiunii în undo_manager după mutare
"""

import pytest

from core.file_manager import move_and_rename_file
from core.undo_manager import undo_manager


# ─── Fixture: resetăm undo_manager înaintea fiecărui test ─────────────────────


@pytest.fixture(autouse=True)
def clear_undo_history():
    """Curăță istoricul global undo_manager înainte și după fiecare test."""
    undo_manager.history.clear()
    yield
    undo_manager.history.clear()


# ─── Happy path ────────────────────────────────────────────────────────────────


def test_move_basic(tmp_path):
    """Mutarea unui fișier simplu cu redenumire."""
    src = tmp_path / "source" / "original.txt"
    src.parent.mkdir()
    src.write_text("hello world")

    dest_dir = tmp_path / "destination"
    result = move_and_rename_file(src, dest_dir, "renamed.txt")

    assert result.exists()
    assert result.name == "renamed.txt"
    assert result.parent == dest_dir
    assert not src.exists()


def test_move_preserves_content(tmp_path):
    """Conținutul fișierului trebuie să fie identic după mutare."""
    content = "Linie 1\nLinie 2\nLinie 3\n"
    src = tmp_path / "in" / "data.txt"
    src.parent.mkdir()
    src.write_text(content)

    result = move_and_rename_file(src, tmp_path / "out", "data_moved.txt")

    assert result.read_text() == content


def test_move_creates_nested_destination(tmp_path):
    """Directorul destinație (inclusiv subdirectoare) se creează automat."""
    src = tmp_path / "src.txt"
    src.write_text("content")

    deep_dest = tmp_path / "a" / "b" / "c"
    result = move_and_rename_file(src, deep_dest, "file.txt")

    assert result.exists()
    assert result.parent == deep_dest


def test_move_same_name(tmp_path):
    """Mutare fără redenumire efectivă (același nume)."""
    src = tmp_path / "source" / "doc.pdf"
    src.parent.mkdir()
    src.write_bytes(b"%PDF-1.4 dummy")

    result = move_and_rename_file(src, tmp_path / "dest", "doc.pdf")

    assert result.name == "doc.pdf"
    assert result.read_bytes() == b"%PDF-1.4 dummy"
    assert not src.exists()


def test_move_binary_file(tmp_path):
    """Fișierele binare (ex: PNG) trebuie mutate corect fără corupere."""
    binary_data = bytes(range(256)) * 4
    src = tmp_path / "image.png"
    src.write_bytes(binary_data)

    result = move_and_rename_file(src, tmp_path / "images", "image_moved.png")

    assert result.read_bytes() == binary_data


def test_move_multiple_files_sequentially(tmp_path):
    """Mutarea mai multor fișiere una după alta — toate ajung la destinație."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    dest_dir = tmp_path / "dest"

    files = []
    for i in range(5):
        f = src_dir / f"file_{i}.txt"
        f.write_text(f"content {i}")
        files.append(f)

    results = [
        move_and_rename_file(f, dest_dir, f"moved_{i}.txt") for i, f in enumerate(files)
    ]

    for i, r in enumerate(results):
        assert r.exists(), f"Fișierul {r} nu există"
        assert r.read_text() == f"content {i}"

    # Sursele nu mai există
    for f in files:
        assert not f.exists()


# ─── Error cases ───────────────────────────────────────────────────────────────


def test_move_source_not_found_raises(tmp_path):
    """Dacă sursa nu există, trebuie ridicată FileNotFoundError."""
    nonexistent = tmp_path / "ghost.txt"
    with pytest.raises(FileNotFoundError):
        move_and_rename_file(nonexistent, tmp_path / "dest", "out.txt")


def test_move_source_is_directory_raises(tmp_path):
    """Dacă sursa este un director (nu fișier), trebuie ridicată FileNotFoundError."""
    a_dir = tmp_path / "adir"
    a_dir.mkdir()
    with pytest.raises(FileNotFoundError):
        move_and_rename_file(a_dir, tmp_path / "dest", "out.txt")


# ─── Integrare cu undo_manager ─────────────────────────────────────────────────


def test_move_records_action_in_undo(tmp_path):
    """Fiecare mutare trebuie înregistrată în undo_manager.history."""
    src = tmp_path / "file.txt"
    src.write_text("data")

    assert len(undo_manager.history) == 0

    result = move_and_rename_file(src, tmp_path / "dest", "file_new.txt")

    assert len(undo_manager.history) == 1
    action = undo_manager.history[-1]
    assert action["old_path"] == src
    assert action["new_path"] == result


def test_multiple_moves_record_multiple_actions(tmp_path):
    """N mutări → N intrări în undo_manager.history."""
    n = 4
    results = []
    for i in range(n):
        f = tmp_path / f"src_{i}.txt"
        f.write_text(f"data {i}")
        r = move_and_rename_file(f, tmp_path / "dest", f"dst_{i}.txt")
        results.append(r)

    assert len(undo_manager.history) == n
