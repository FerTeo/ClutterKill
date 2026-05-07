import shutil
from pathlib import Path
from typing import Union


def move_and_rename_file(
    src: Union[str, Path], dest: Union[str, Path], new_name: str
) -> Path:
    """
    Moves a file from `src` to `dest` directory and renames it to `new_name`.

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

    # Move the file physically
    shutil.move(src_path, target_path)

    return target_path
