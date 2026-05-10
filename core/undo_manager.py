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

    def undo_action(self, index: int) -> bool:
        """
        Anulează o acțiune specifică din istoric (după index).
        Necesar pentru butoanele de Undo pe fiecare rând din Activity History (US 10).

        Returns:
            True dacă s-a făcut undo cu succes, False altfel.
        """
        if index < 0 or index >= len(self.history):
            return False

        action = self.history[index]
        old_path = action["old_path"]
        new_path = action["new_path"]

        if new_path.exists():
            old_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(new_path), str(old_path))
            del self.history[index]
            return True

        return False

    def get_history(self) -> list[dict]:
        """
        Returnează istoricul acțiunilor ca o listă de dicționare (pentru UI).
        """
        return [
            {"old_path": str(a["old_path"]), "new_path": str(a["new_path"])}
            for a in self.history
        ]


# O instanță globală pe care o vom folosi în restul aplicației (pentru integrare ușoară)
undo_manager = UndoManager()
