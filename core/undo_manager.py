import shutil
from collections import deque
from pathlib import Path
from typing import TypedDict, Union


class FileAction(TypedDict):
    old_path: Path
    new_path: Path


class UndoManager:
    """
    Gestionează un istoric al operațiilor de mutare/redenumire fișiere
    pentru a permite anularea acestora (undo).
    """

    def __init__(self, max_history: int = 50):
        # deque cu maxlen va șterge automat cele mai vechi elemente când se depășește limita
        self.history: deque[FileAction] = deque(maxlen=max_history)

    def record_action(
        self, old_path: Union[str, Path], new_path: Union[str, Path]
    ) -> None:
        """
        Înregistrează o acțiune în stivă.
        """
        self.history.append({"old_path": Path(old_path), "new_path": Path(new_path)})

    def undo_last_action(self) -> bool:
        """
        Anulează ultima operațiune înregistrată, readucând fișierul la vechea locație.
        Returnează True dacă s-a făcut undo cu succes, False dacă nu e nimic de anulat.
        """
        if not self.history:
            return False

        last_action = self.history.pop()
        old_path = last_action["old_path"]
        new_path = last_action["new_path"]

        # Dacă fișierul nou există la locația mutată, îl aducem înapoi
        if new_path.exists():
            # Ne asigurăm că folderul părinte original există
            old_path.parent.mkdir(parents=True, exist_ok=True)
            # Mutăm înapoi fizic
            shutil.move(str(new_path), str(old_path))
            return True

        return False


# O instanță globală pe care o vom folosi în restul aplicației (pentru integrare ușoară)
undo_manager = UndoManager()
