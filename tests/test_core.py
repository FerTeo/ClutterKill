from core.file_manager import move_and_rename_file


def test_move_and_rename_file(tmp_path):
    # Setup
    src_dir = tmp_path / "source"
    src_dir.mkdir()
    src_file = src_dir / "test.txt"
    src_file.write_text("hello world")

    dest_dir = tmp_path / "destination" / "subfolder"

    # Execute
    new_name = "renamed_test.txt"
    result_path = move_and_rename_file(src_file, dest_dir, new_name)

    # Assert
    assert result_path.exists()
    assert result_path.name == new_name
    assert result_path.parent == dest_dir
    assert result_path.read_text() == "hello world"
    assert not src_file.exists()
