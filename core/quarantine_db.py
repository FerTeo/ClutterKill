import sqlite3
from pathlib import Path
from typing import Optional, Any

DEFAULT_DB_PATH = Path(__file__).parent.parent / "quarantine.db"


class QuarantineDB:
    """
    Gestionează baza de date SQLite pentru fișierele aflate în carantină.

    Când AI-ul nu este 100% sigur cum să clasifice un fișier, acesta este
    adăugat în carantină în loc să fie mutat automat. Utilizatorul poate
    apoi aproba, edita sau respinge sugestia din interfață.

    Tabelul `quarantine` stochează:
        - id: identificator unic auto-increment
        - original_path: calea originală a fișierului pe disc
        - ai_proposed_name: numele sugerat de AI (ex: "Factura_Enel_2026.pdf")
        - ai_proposed_folder: folderul destinație sugerat (ex: "Facturi/Enel")
        - reason: motivul / explicația AI-ului pentru decizia luată
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """
        Creează și returnează o conexiune la baza de date.
        row_factory = sqlite3.Row permite accesarea coloanelor pe nume (dict-like).
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """
        Creează tabelul `quarantine` dacă nu există deja.
        Se apelează automat la instanțierea clasei.
        """
        conn = self._get_connection()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS quarantine (
                    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_path      TEXT    NOT NULL,
                    ai_proposed_name   TEXT    NOT NULL,
                    ai_proposed_folder TEXT    NOT NULL,
                    reason             TEXT
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    # ─── CREATE ────────────────────────────────────────────────────────

    def add(
        self,
        original_path: str,
        ai_proposed_name: str,
        ai_proposed_folder: str,
        reason: str = "",
    ) -> int:
        """
        Adaugă un fișier în carantină.

        Args:
            original_path: Calea originală a fișierului.
            ai_proposed_name: Numele propus de AI.
            ai_proposed_folder: Folderul destinație propus de AI.
            reason: Motivul clasificării (opțional).

        Returns:
            ID-ul rândului nou inserat.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT INTO quarantine (original_path, ai_proposed_name, ai_proposed_folder, reason)
                VALUES (?, ?, ?, ?)
                """,
                (original_path, ai_proposed_name, ai_proposed_folder, reason),
            )
            conn.commit()
            return cursor.lastrowid or 0
        finally:
            conn.close()

    # ─── READ ──────────────────────────────────────────────────────────

    def get_all(self) -> list[dict]:
        """
        Returnează toate fișierele din carantină ca o listă de dicționare.
        """
        conn = self._get_connection()
        try:
            rows = conn.execute("SELECT * FROM quarantine").fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_by_id(self, record_id: int) -> Optional[dict]:
        """
        Returnează un singur fișier din carantină după ID.

        Returns:
            Un dicționar cu datele fișierului, sau None dacă nu există.
        """
        conn = self._get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM quarantine WHERE id = ?", (record_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    # ─── UPDATE ────────────────────────────────────────────────────────

    def update(
        self,
        record_id: int,
        ai_proposed_name: Optional[str] = None,
        ai_proposed_folder: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Actualizează câmpurile unui fișier din carantină.
        Doar câmpurile transmise (non-None) vor fi modificate.

        Returns:
            True dacă s-a actualizat cel puțin un rând, False dacă ID-ul nu există.
        """
        # Construim dinamic query-ul doar cu câmpurile care se schimbă
        fields = []
        values: list[Any] = []

        if ai_proposed_name is not None:
            fields.append("ai_proposed_name = ?")
            values.append(ai_proposed_name)
        if ai_proposed_folder is not None:
            fields.append("ai_proposed_folder = ?")
            values.append(ai_proposed_folder)
        if reason is not None:
            fields.append("reason = ?")
            values.append(reason)

        if not fields:
            return False

        values.append(record_id)

        conn = self._get_connection()
        try:
            cursor = conn.execute(
                f"UPDATE quarantine SET {', '.join(fields)} WHERE id = ?",
                values,
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    # ─── DELETE ────────────────────────────────────────────────────────

    def remove(self, record_id: int) -> bool:
        """
        Șterge un fișier din carantină după ID.

        Returns:
            True dacă s-a șters, False dacă ID-ul nu exista.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("DELETE FROM quarantine WHERE id = ?", (record_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def clear_all(self) -> int:
        """
        Golește complet tabelul de carantină.

        Returns:
            Numărul de rânduri șterse.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("DELETE FROM quarantine")
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()


# Instanță globală (la fel ca undo_manager) pentru utilizare directă în aplicație
quarantine_db = QuarantineDB()
