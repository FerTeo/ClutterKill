import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path("rules.db")


def init_db():
    """Inițializează baza de date pentru șabloanele AI."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS saved_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                query TEXT NOT NULL,
                folder_template TEXT NOT NULL,
                naming_template TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insert a default rule only if the table is empty
        cursor.execute("SELECT COUNT(*) FROM saved_rules")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                """
                INSERT INTO saved_rules (name, query, folder_template, naming_template)
                VALUES (?, ?, ?, ?)
            """,
                (
                    "Smart Auto-Sort (Default)",
                    "Toate fișierele",
                    "",
                    "[An]_[Emitent]_[SubiectAI]",
                ),
            )
        conn.commit()


def save_rule(
    name: str, query: str, folder_template: str, naming_template: str
) -> bool:
    """Salvează sau suprascrie un șablon de regulă."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO saved_rules (name, query, folder_template, naming_template)
                VALUES (?, ?, ?, ?)
            """,
                (name, query, folder_template, naming_template),
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Eroare la salvarea regulii în DB: {e}")
        return False


def get_all_rules() -> list[dict]:
    """Returnează toate regulile salvate."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM saved_rules ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Eroare la citirea regulilor: {e}")
        return []


def get_rule_by_name(name: str) -> dict | None:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM saved_rules WHERE name = ?", (name,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Eroare la obținerea regulii {name}: {e}")
        return None


def delete_rule(name: str) -> bool:
    """Șterge o regulă."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM saved_rules WHERE name = ?", (name,))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Eroare la ștergerea regulii: {e}")
        return False


# Asigură-te că tabela e creată la primul import
init_db()
