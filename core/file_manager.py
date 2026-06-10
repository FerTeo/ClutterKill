import shutil
from pathlib import Path
from typing import Union

from core.undo_manager import undo_manager


def move_and_rename_file(
    src: Union[str, Path], dest: Union[str, Path], new_name: str
) -> Path:
    """
    Moves a file from `src` to `dest` directory and renames it to `new_name`.
    Records the action in the undo_manager.

    Args:
        src: The source file path.
        dest: The destination directory path.
        new_name: The new name for the file.

    Returns:
        The new Path object of the moved file.
    """
    src_path = Path(src)
    dest_path = Path(dest)

    if not src_path.is_file():
        raise FileNotFoundError(f"Source file does not exist: {src_path}")

    # Ensure the parent folders for the destination exist
    dest_path.mkdir(parents=True, exist_ok=True)

    # The final target path
    target_path = dest_path / new_name

    # Prevent overwriting existing files with the same name (e.g. Dog.jpeg, Dog_1.jpeg)
    if target_path.exists():
        base_name = target_path.stem
        ext = target_path.suffix
        counter = 1
        while target_path.exists():
            target_path = dest_path / f"{base_name}_{counter}{ext}"
            counter += 1

    # Move the file physically
    shutil.move(str(src_path), str(target_path))

    # Record the action so we can undo it later!
    undo_manager.record_action(src_path, target_path)

    return target_path
