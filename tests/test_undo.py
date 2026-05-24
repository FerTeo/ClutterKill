"""
Teste pentru stiva de undo — core/undo_manager.py

Acoperire:
  - UndoManager direct (fără file_manager):
      record_action / undo_last_action / undo_action(index) / get_history
  - Comportament cu stivă goală
  - Undo când fișierul destinație lipseşte (mutare externă)
  - max_history: limitarea automată a deque-ului
  - undo_action(index) – anulare selectivă
  - get_history – formatul returnat
  - Integrare cu file_manager (end-to-end):
      undo după move, undo multiplu, undo în ordine inversă
"""

import pytest
from pathlib import Path

from core.undo_manager import UndoManager
from core.file_manager import move_and_rename_file
from core.undo_manager import undo_manager as global_undo


# ─── Fixture: instanță izolată + curăță global undo ───────────────────────────


@pytest.fixture()
def um():
    """Returnează un UndoManager proaspăt pentru fiecare test."""
    return UndoManager()


@pytest.fixture(autouse=True)
def clear_global_undo():
    """Curăță istoricul global înainte și după fiecare test."""
    global_undo.history.clear()
    yield
    global_undo.history.clear()


# ─── record_action ─────────────────────────────────────────────────────────────


def test_record_action_adds_to_history(um):
    """record_action trebuie să adauge exact o intrare în history."""
    um.record_action("/old/path.txt", "/new/path.txt")
    assert len(um.history) == 1


def test_record_action_stores_paths_as_path_objects(um):
    """Căile stocate trebuie să fie obiecte Path."""
    um.record_action("/old/file.txt", "/new/file.txt")
    action = um.history[0]
    assert isinstance(action["old_path"], Path)
    assert isinstance(action["new_path"], Path)


def test_record_multiple_actions(um):
    """Mai multe apeluri creează mai multe intrări, în ordine."""
    um.record_action("/a.txt", "/b.txt")
    um.record_action("/c.txt", "/d.txt")
    um.record_action("/e.txt", "/f.txt")
    assert len(um.history) == 3
    assert um.history[0]["old_path"] == Path("/a.txt")
    assert um.history[2]["old_path"] == Path("/e.txt")


# ─── undo_last_action ──────────────────────────────────────────────────────────


def test_undo_last_action_empty_history(um):
    """Undo pe stivă goală → False, fără excepție."""
    assert um.undo_last_action() is False


def test_undo_last_action_removes_entry(tmp_path, um):
    """După undo cu succes, intrarea trebuie eliminată din history."""
    src = tmp_path / "src.txt"
    dst = tmp_path / "dst.txt"
    src.write_text("data")
    src.rename(dst)  # mutăm manual
    um.record_action(src, dst)

    result = um.undo_last_action()

    assert result is True
    assert len(um.history) == 0


def test_undo_last_action_file_moved_back(tmp_path, um):
    """Fișierul trebuie readus fizic la calea originală."""
    src = tmp_path / "original.txt"
    dst = tmp_path / "moved" / "renamed.txt"
    src.write_text("restore me")
    dst.parent.mkdir()
    src.rename(dst)
    um.record_action(src, dst)

    um.undo_last_action()

    assert src.exists()
    assert src.read_text() == "restore me"
    assert not dst.exists()


def test_undo_last_action_returns_false_when_dest_missing(tmp_path, um):
    """Dacă fișierul mutat nu mai există la destinație → False (nu crașează)."""
    um.record_action(tmp_path / "old.txt", tmp_path / "new.txt")
    # new.txt nu există pe disc
    assert um.undo_last_action() is False


def test_undo_last_action_lifo_order(tmp_path, um):
    """Undo respectă ordinea LIFO (Last In, First Out)."""
    f1 = tmp_path / "f1.txt"
    f2 = tmp_path / "f2.txt"
    d1 = tmp_path / "d1.txt"
    d2 = tmp_path / "d2.txt"

    f1.write_text("first")
    f2.write_text("second")
    f1.rename(d1)
    f2.rename(d2)

    um.record_action(f1, d1)
    um.record_action(f2, d2)

    # Al doilea înregistrat → primul undo
    um.undo_last_action()
    assert f2.exists()
    assert not d2.exists()

    # Al primul înregistrat → al doilea undo
    um.undo_last_action()
    assert f1.exists()
    assert not d1.exists()


# ─── undo_action(index) ────────────────────────────────────────────────────────


def test_undo_action_by_index(tmp_path, um):
    """undo_action(index) anulează acțiunea de la indexul dat."""
    src0 = tmp_path / "s0.txt"
    dst0 = tmp_path / "d0.txt"
    src1 = tmp_path / "s1.txt"
    dst1 = tmp_path / "d1.txt"

    src0.write_text("zero")
    src1.write_text("one")
    src0.rename(dst0)
    src1.rename(dst1)

    um.record_action(src0, dst0)  # index 0
    um.record_action(src1, dst1)  # index 1

    # Anulăm acțiunea de la index 0 (prima mutare)
    result = um.undo_action(0)

    assert result is True
    assert src0.exists()
    assert not dst0.exists()
    # Acțiunea de la index 1 rămâne
    assert len(um.history) == 1


def test_undo_action_invalid_index(um):
    """Index out of range → False, fără excepție."""
    um.record_action("/a.txt", "/b.txt")
    assert um.undo_action(5) is False
    assert um.undo_action(-1) is False


def test_undo_action_empty_history(um):
    """undo_action pe stivă goală → False."""
    assert um.undo_action(0) is False


# ─── max_history ───────────────────────────────────────────────────────────────


def test_max_history_limits_deque():
    """Depășirea max_history → cele mai vechi intrări sunt șterse automat."""
    um = UndoManager(max_history=3)
    for i in range(10):
        um.record_action(f"/old/{i}.txt", f"/new/{i}.txt")

    assert len(um.history) == 3
    # Ultimele 3 acțiuni (7, 8, 9) trebuie reținute
    assert um.history[-1]["old_path"] == Path("/old/9.txt")
    assert um.history[0]["old_path"] == Path("/old/7.txt")


# ─── get_history ───────────────────────────────────────────────────────────────


def test_get_history_returns_list_of_dicts(um):
    """get_history returnează o listă de dict-uri cu chei string."""
    um.record_action("/src/a.txt", "/dst/a.txt")
    um.record_action("/src/b.txt", "/dst/b.txt")

    history = um.get_history()

    assert isinstance(history, list)
    assert len(history) == 2
    assert isinstance(history[0], dict)
    assert "old_path" in history[0]
    assert "new_path" in history[0]


def test_get_history_paths_are_strings(um):
    """Căile din get_history trebuie să fie string-uri (nu Path), pentru UI."""
    um.record_action(Path("/src/x.txt"), Path("/dst/x.txt"))
    history = um.get_history()
    assert isinstance(history[0]["old_path"], str)
    assert isinstance(history[0]["new_path"], str)


def test_get_history_empty(um):
    """get_history pe stivă goală → listă goală."""
    assert um.get_history() == []


# ─── Integrare end-to-end cu file_manager ─────────────────────────────────────


def test_integration_move_then_undo(tmp_path):
    """End-to-end: move_and_rename_file + undo_last_action readuce fișierul."""
    src = tmp_path / "source" / "doc.txt"
    src.parent.mkdir()
    src.write_text("important content")

    target = move_and_rename_file(src, tmp_path / "dest", "doc_renamed.txt")
    assert target.exists()
    assert not src.exists()

    success = global_undo.undo_last_action()

    assert success is True
    assert src.exists()
    assert src.read_text() == "important content"
    assert not target.exists()


def test_integration_multiple_moves_undo_all(tmp_path):
    """Undo pe toate mutările în ordine inversă (LIFO)."""
    src_files = []
    dst_files = []

    for i in range(3):
        f = tmp_path / "src" / f"file_{i}.txt"
        f.parent.mkdir(exist_ok=True)
        f.write_text(f"content {i}")
        src_files.append(f)
        d = move_and_rename_file(f, tmp_path / "dst", f"moved_{i}.txt")
        dst_files.append(d)

    # Undo complet în ordine inversă
    for i in range(3):
        assert global_undo.undo_last_action() is True

    for i, src in enumerate(src_files):
        assert src.exists(), f"Fișierul {src} nu a fost restaurat"
        assert not dst_files[i].exists()


def test_integration_undo_restores_to_original_subdirectory(tmp_path):
    """Undo recreează directorul sursă dacă a fost șters între timp."""
    src_dir = tmp_path / "deep" / "nested" / "dir"
    src_dir.mkdir(parents=True)
    src = src_dir / "file.txt"
    src.write_text("nested content")

    move_and_rename_file(src, tmp_path / "flat", "file_flat.txt")

    # Simulăm că directorul sursă a fost șters manual
    import shutil

    shutil.rmtree(str(tmp_path / "deep"))
    assert not src_dir.exists()

    # Undo trebuie să recreeze directorul și să readucă fișierul
    success = global_undo.undo_last_action()

    assert success is True
    assert src.exists()
    assert src.read_text() == "nested content"
