from core.file_manager import move_and_rename_file
from core.undo_manager import undo_manager


def test_undo_last_action(tmp_path):
    # Setup
    src_dir = tmp_path / "source"
    src_dir.mkdir()
    src_file = src_dir / "test.txt"
    src_file.write_text("Test content for undo")

    dest_dir = tmp_path / "destination"

    # Ensure undo manager history is empty before testing
    undo_manager.history.clear()

    # Execute Move
    new_name = "renamed_test.txt"
    target_path = move_and_rename_file(src_file, dest_dir, new_name)

    # Confirm it was moved
    assert target_path.exists()
    assert not src_file.exists()

    # Execute Undo (This is the verification step required by the task)
    success = undo_manager.undo_last_action()

    # Assert Undo was successful and file is back at original location
    assert success is True
    assert src_file.exists()
    assert src_file.read_text() == "Test content for undo"
    assert not target_path.exists()
