"""
database/dummy_repository.py
============================
API Contract — DatabaseManager cu date HARDCODATE (fără SQL real).

Acest fișier definește INTERFAȚA exactă pe care:
  • Inginerul 4 (UI/PyQt6) o va apela pentru a popula tabelele și listele.
  • Inginerul 3 (DB) o va reimplementa cu SQLAlchemy + SQLite.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ATENȚIE INGINER 3 — Ghid de migrare la SQL real
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. NU schimba semnăturile metodelor (nume, parametri, tip returnat).
   UI-ul (Inginer 4) depinde de exact aceste semnături.

2. Toate metodele returnează dict/list[dict] — păstrează structura
   JSON identică. Dacă adaugi câmpuri noi, adaugă-le ȘI în models.py.

3. Înlocuiește _HARDCODED_* cu query-uri SQLAlchemy / sqlite3.
   Fiecare metodă are un comentariu TODO exact cu query-ul SQL necesar.

4. Înlocuiește __init__ cu inițializarea conexiunii la DB:
      self.db_path = db_path  (sau engine SQLAlchemy)
      self._conn = sqlite3.connect(self.db_path)

5. Schema tabelelor recomandată:
      CREATE TABLE files (
          id TEXT PRIMARY KEY,
          original_path TEXT,
          original_name TEXT,
          new_name TEXT,
          destination_path TEXT,
          category TEXT,
          confidence REAL,
          status TEXT,
          timestamp TEXT,
          page_count INTEGER DEFAULT 0,
          size_bytes INTEGER DEFAULT 0
      );
      CREATE TABLE quarantine (
          id TEXT PRIMARY KEY,
          file_id TEXT REFERENCES files(id),
          ai_suggestion TEXT,
          reason TEXT,
          suggested_category TEXT,
          quarantined_at TEXT,
          user_decision TEXT
      );
      CREATE TABLE activity (
          id TEXT PRIMARY KEY,
          file_id TEXT REFERENCES files(id),
          action TEXT,
          undo_original_path TEXT,
          undo_available INTEGER,
          recorded_at TEXT
      );
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from database.models import ActivityEntry, FileCategory, FileRecord, FileStatus, QuarantineRecord


# ---------------------------------------------------------------------------
# Date hardcodate — folosite de metodele dummy
# (Inginer 3: șterge tot blocul _HARDCODED_* și înlocuiește cu query-uri SQL)
# ---------------------------------------------------------------------------

def _ts(days_ago: int = 0, hours_ago: int = 0) -> str:
    """Generează un timestamp ISO 8601 în trecut."""
    dt = datetime.utcnow() - timedelta(days=days_ago, hours=hours_ago)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


_HARDCODED_FILES: list[dict[str, Any]] = [
    {
        "id": "f001", "original_name": "scan_001.pdf",
        "original_path": "C:/Users/demo/Downloads/scan_001.pdf",
        "new_name": "factura_ACME_SRL_2024_01_15.pdf",
        "destination_path": "C:/Users/demo/Arhiva/Facturi/factura_ACME_SRL_2024_01_15.pdf",
        "category": "factura", "confidence": 0.94, "status": "moved",
        "timestamp": _ts(days_ago=0, hours_ago=2), "page_count": 2, "size_bytes": 45312,
    },
    {
        "id": "f002", "original_name": "document_final_v2.pdf",
        "original_path": "C:/Users/demo/Downloads/document_final_v2.pdf",
        "new_name": "contract_TechCorp_SRL_2024_01_14.pdf",
        "destination_path": "C:/Users/demo/Arhiva/Contracte/contract_TechCorp_SRL_2024_01_14.pdf",
        "category": "contract", "confidence": 0.88, "status": "moved",
        "timestamp": _ts(days_ago=1), "page_count": 8, "size_bytes": 132048,
    },
    {
        "id": "f003", "original_name": "curs_alg_sem2.pdf",
        "original_path": "C:/Users/demo/Downloads/curs_alg_sem2.pdf",
        "new_name": "curs_universitar_Algoritmi_An2_Sem2.pdf",
        "destination_path": "C:/Users/demo/Arhiva/Cursuri/curs_universitar_Algoritmi_An2_Sem2.pdf",
        "category": "curs_universitar", "confidence": 0.91, "status": "moved",
        "timestamp": _ts(days_ago=1, hours_ago=3), "page_count": 45, "size_bytes": 2097152,
    },
    {
        "id": "f004", "original_name": "reteta_dr_ionescu.jpg",
        "original_path": "C:/Users/demo/Downloads/reteta_dr_ionescu.jpg",
        "new_name": "reteta_medicala_Ionescu_2024_01_13.jpg",
        "destination_path": "C:/Users/demo/Arhiva/Sanatate/reteta_medicala_Ionescu_2024_01_13.jpg",
        "category": "reteta_medicala", "confidence": 0.79, "status": "moved",
        "timestamp": _ts(days_ago=2), "page_count": 0, "size_bytes": 874400,
    },
    {
        "id": "f005", "original_name": "IMG_20240112_085432.jpg",
        "original_path": "C:/Users/demo/Downloads/IMG_20240112_085432.jpg",
        "new_name": "foto_document_2024_01_12.jpg",
        "destination_path": "C:/Users/demo/Arhiva/Altele/foto_document_2024_01_12.jpg",
        "category": "foto", "confidence": 0.71, "status": "moved",
        "timestamp": _ts(days_ago=3), "page_count": 0, "size_bytes": 3145728,
    },
    {
        "id": "f006", "original_name": "nota_interna_feb.docx",
        "original_path": "C:/Users/demo/Downloads/nota_interna_feb.docx",
        "new_name": "necunoscut_nota_interna_feb.docx",
        "destination_path": "C:/Users/demo/Arhiva/Altele/necunoscut_nota_interna_feb.docx",
        "category": "necunoscut", "confidence": 0.45, "status": "quarantined",
        "timestamp": _ts(days_ago=3, hours_ago=5), "page_count": 3, "size_bytes": 28672,
    },
    {
        "id": "f007", "original_name": "factura_emag_2023.pdf",
        "original_path": "C:/Users/demo/Downloads/factura_emag_2023.pdf",
        "new_name": "factura_eMAG_2023_12_20.pdf",
        "destination_path": "C:/Users/demo/Arhiva/Facturi/factura_eMAG_2023_12_20.pdf",
        "category": "factura", "confidence": 0.97, "status": "moved",
        "timestamp": _ts(days_ago=4), "page_count": 1, "size_bytes": 38912,
    },
    {
        "id": "f008", "original_name": "contract_chirie_2024.pdf",
        "original_path": "C:/Users/demo/Downloads/contract_chirie_2024.pdf",
        "new_name": "contract_chirie_Popescu_2024_01_01.pdf",
        "destination_path": "C:/Users/demo/Arhiva/Contracte/contract_chirie_Popescu_2024_01_01.pdf",
        "category": "contract", "confidence": 0.86, "status": "undone",
        "timestamp": _ts(days_ago=5), "page_count": 12, "size_bytes": 524288,
    },
    {
        "id": "f009", "original_name": "scan_chitanta.pdf",
        "original_path": "C:/Users/demo/Downloads/scan_chitanta.pdf",
        "new_name": "factura_chitanta_2024_01_08.pdf",
        "destination_path": "C:/Users/demo/Arhiva/Facturi/factura_chitanta_2024_01_08.pdf",
        "category": "factura", "confidence": 0.83, "status": "moved",
        "timestamp": _ts(days_ago=6), "page_count": 1, "size_bytes": 102400,
    },
    {
        "id": "f010", "original_name": "adeverinta_student.pdf",
        "original_path": "C:/Users/demo/Downloads/adeverinta_student.pdf",
        "new_name": "certificat_adeverinta_student_2024.pdf",
        "destination_path": "C:/Users/demo/Arhiva/Documente/certificat_adeverinta_student_2024.pdf",
        "category": "certificat", "confidence": 0.89, "status": "moved",
        "timestamp": _ts(days_ago=7), "page_count": 1, "size_bytes": 67584,
    },
    {
        "id": "f011", "original_name": "final_FINAL_v3_ok.pdf",
        "original_path": "C:/Users/demo/Downloads/final_FINAL_v3_ok.pdf",
        "new_name": None,
        "destination_path": None,
        "category": "necunoscut", "confidence": 0.31, "status": "failed",
        "timestamp": _ts(days_ago=7, hours_ago=2), "page_count": 0, "size_bytes": 2048,
    },
    {
        "id": "f012", "original_name": "rp_antibiotice.jpg",
        "original_path": "C:/Users/demo/Downloads/rp_antibiotice.jpg",
        "new_name": "reteta_medicala_2024_01_05.jpg",
        "destination_path": "C:/Users/demo/Arhiva/Sanatate/reteta_medicala_2024_01_05.jpg",
        "category": "reteta_medicala", "confidence": 0.76, "status": "quarantined",
        "timestamp": _ts(days_ago=8), "page_count": 0, "size_bytes": 1048576,
    },
]

_HARDCODED_QUARANTINE: list[dict[str, Any]] = [
    {
        "id": "q001",
        "file_record": next(f for f in _HARDCODED_FILES if f["id"] == "f006"),
        "ai_suggestion": "necunoscut_nota_interna_feb.docx",
        "reason": "Confidence 0.45 — categoria nu a putut fi determinată cu certitudine. "
                  "Conținut mixt: elemente de contract și notă internă.",
        "suggested_category": "necunoscut",
        "quarantined_at": _ts(days_ago=3, hours_ago=5),
        "user_decision": None,
    },
    {
        "id": "q002",
        "file_record": next(f for f in _HARDCODED_FILES if f["id"] == "f012"),
        "ai_suggestion": "reteta_medicala_antibiotice_2024_01_05.jpg",
        "reason": "Confidence 0.76 — sub pragul de 0.80 setat de utilizator. "
                  "Text parțial lizibil (imagine slab scanată).",
        "suggested_category": "reteta_medicala",
        "quarantined_at": _ts(days_ago=8),
        "user_decision": None,
    },
]

_HARDCODED_ACTIVITY: list[dict[str, Any]] = [
    {
        "id": "a001",
        "file_record": _HARDCODED_FILES[0],
        "action": "moved",
        "undo_original_path": "C:/Users/demo/Downloads/scan_001.pdf",
        "undo_available": True,
        "recorded_at": _ts(days_ago=0, hours_ago=2),
    },
    {
        "id": "a002",
        "file_record": _HARDCODED_FILES[1],
        "action": "moved",
        "undo_original_path": "C:/Users/demo/Downloads/document_final_v2.pdf",
        "undo_available": True,
        "recorded_at": _ts(days_ago=1),
    },
    {
        "id": "a003",
        "file_record": _HARDCODED_FILES[2],
        "action": "moved",
        "undo_original_path": "C:/Users/demo/Downloads/curs_alg_sem2.pdf",
        "undo_available": True,
        "recorded_at": _ts(days_ago=1, hours_ago=3),
    },
    {
        "id": "a004",
        "file_record": _HARDCODED_FILES[3],
        "action": "moved",
        "undo_original_path": "C:/Users/demo/Downloads/reteta_dr_ionescu.jpg",
        "undo_available": True,
        "recorded_at": _ts(days_ago=2),
    },
    {
        "id": "a005",
        "file_record": _HARDCODED_FILES[6],
        "action": "moved",
        "undo_original_path": "C:/Users/demo/Downloads/factura_emag_2023.pdf",
        "undo_available": True,
        "recorded_at": _ts(days_ago=4),
    },
    {
        "id": "a006",
        "file_record": _HARDCODED_FILES[7],
        "action": "undone",
        "undo_original_path": "C:/Users/demo/Downloads/contract_chirie_2024.pdf",
        "undo_available": False,  # deja anulat
        "recorded_at": _ts(days_ago=5),
    },
]


# ---------------------------------------------------------------------------
# DatabaseManager — interfața publică
# ---------------------------------------------------------------------------

class DatabaseManager:
    """
    Manager de bază de date pentru ClutterKill.

    În prezent returnează date HARDCODATE pentru a permite Inginerului 4
    să construiască UI-ul fără o bază de date reală.

    ─────────────────────────────────────────────────
    INGINER 3 — Pași de înlocuire cu SQL real:
    1. Înlocuiește `__init__` cu inițializarea SQLite/SQLAlchemy.
    2. Urmărește comentariile # TODO (Inginer 3) din fiecare metodă.
    3. Păstrează tipurile de returnare identice (list[dict] / dict).
    ─────────────────────────────────────────────────
    """

    def __init__(self, db_path: str | None = None) -> None:
        """
        Inițializează managerul.

        Args:
            db_path: Calea către fișierul SQLite (ignorat în varianta dummy).

        TODO (Inginer 3): Înlocuiește cu:
            import sqlite3
            self.db_path = db_path or "clutterkill.db"
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._create_tables()
        """
        self.db_path = db_path  # rezervat pentru Inginer 3
        # (în varianta dummy nu deschidem niciun fișier)

    # ------------------------------------------------------------------
    # Metoda 1 — Istoricul fișierelor (tab Activity History)
    # ------------------------------------------------------------------

    def get_file_history(self, limit: int = 50) -> list[dict]:
        """
        Returnează ultimele `limit` fișiere procesate, ordonate descendent după timestamp.

        Returns:
            list[dict] cu structura FileRecord (câmpuri: id, original_name, new_name,
            original_path, destination_path, category, confidence, status,
            timestamp, page_count, size_bytes).

        TODO (Inginer 3): Înlocuiește cu:
            cursor = self._conn.execute(
                "SELECT * FROM files ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
        """
        return _HARDCODED_FILES[:limit]

    # ------------------------------------------------------------------
    # Metoda 2 — Fișierele din carantină (tab Quarantine Zone)
    # ------------------------------------------------------------------

    def get_quarantine_items(self) -> list[dict]:
        """
        Returnează toate fișierele din Quarantine Zone nerezolvate.

        Returns:
            list[dict] cu structura QuarantineRecord (câmpuri: id, file_record,
            ai_suggestion, reason, suggested_category, quarantined_at, user_decision).
            Returnează doar înregistrările cu user_decision = null.

        TODO (Inginer 3): Înlocuiește cu:
            cursor = self._conn.execute(
                '''SELECT q.*, f.*
                   FROM quarantine q
                   JOIN files f ON q.file_id = f.id
                   WHERE q.user_decision IS NULL
                   ORDER BY q.quarantined_at DESC'''
            )
            return [dict(row) for row in cursor.fetchall()]
        """
        return [q for q in _HARDCODED_QUARANTINE if q["user_decision"] is None]

    # ------------------------------------------------------------------
    # Metoda 3 — Adaugă un fișier procesat
    # ------------------------------------------------------------------

    def add_file_record(self, record: FileRecord) -> dict:
        """
        Salvează un fișier procesat de AI în baza de date.

        Args:
            record: Obiect FileRecord populat de agentul AI.

        Returns:
            dict cu câmpul "id" nou generat și "status": "ok".
            Exemplu: {"id": "f013", "status": "ok"}

        TODO (Inginer 3): Înlocuiește cu:
            self._conn.execute(
                '''INSERT INTO files
                   (id, original_path, original_name, new_name, destination_path,
                    category, confidence, status, timestamp, page_count, size_bytes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (record.id, record.original_path, record.original_name,
                 record.new_name, record.destination_path, record.category,
                 record.confidence, record.status, record.timestamp,
                 record.page_count, record.size_bytes)
            )
            self._conn.commit()
            return {"id": record.id, "status": "ok"}
        """
        # Dummy: simulăm un insert generat cu succes
        new_id = f"f{len(_HARDCODED_FILES) + 1:03d}"
        return {"id": new_id, "status": "ok"}

    # ------------------------------------------------------------------
    # Metoda 4 — Aprobă un fișier din carantină
    # ------------------------------------------------------------------

    def approve_quarantine(self, file_id: str, final_name: str) -> dict:
        """
        Aprobă propunerea AI pentru un fișier din carantină (sau un nume manual).

        Args:
            file_id: ID-ul înregistrării din quarantine (ex: "q001").
            final_name: Numele final ales de utilizator (poate diferi de ai_suggestion).

        Returns:
            dict cu: {"status": "approved", "file_id": str, "final_name": str}

        TODO (Inginer 3): Înlocuiește cu:
            self._conn.execute(
                "UPDATE quarantine SET user_decision = 'approved' WHERE id = ?",
                (file_id,)
            )
            # Actualizează și fișierul cu noul nume
            self._conn.execute(
                "UPDATE files SET new_name = ?, status = 'moved' "
                "WHERE id = (SELECT file_id FROM quarantine WHERE id = ?)",
                (final_name, file_id)
            )
            self._conn.commit()
            return {"status": "approved", "file_id": file_id, "final_name": final_name}
        """
        return {"status": "approved", "file_id": file_id, "final_name": final_name}

    # ------------------------------------------------------------------
    # Metoda 5 — Undo acțiune
    # ------------------------------------------------------------------

    def undo_action(self, entry_id: str) -> dict:
        """
        Anulează o acțiune din istoricul de activitate.

        Args:
            entry_id: ID-ul înregistrării din activity (ex: "a001").

        Returns:
            dict cu: {"status": "undone", "entry_id": str, "restored_path": str}
            sau {"status": "error", "message": str} dacă Undo nu e disponibil.

        TODO (Inginer 3): Înlocuiește cu:
            row = self._conn.execute(
                "SELECT * FROM activity WHERE id = ?", (entry_id,)
            ).fetchone()
            if not row or not row["undo_available"]:
                return {"status": "error", "message": "Undo nu este disponibil."}
            # Marchează ca anulat în DB
            self._conn.execute(
                "UPDATE activity SET undo_available = 0 WHERE id = ?", (entry_id,)
            )
            self._conn.execute(
                "UPDATE files SET status = 'undone' "
                "WHERE id = (SELECT file_id FROM activity WHERE id = ?)",
                (entry_id,)
            )
            self._conn.commit()
            return {"status": "undone", "entry_id": entry_id,
                    "restored_path": row["undo_original_path"]}
        """
        entry = next((a for a in _HARDCODED_ACTIVITY if a["id"] == entry_id), None)
        if not entry or not entry["undo_available"]:
            return {"status": "error", "message": "Undo nu este disponibil pentru această acțiune."}
        return {
            "status": "undone",
            "entry_id": entry_id,
            "restored_path": entry["undo_original_path"],
        }

    # ------------------------------------------------------------------
    # Metoda 6 — Statistici generale (dashboard header)
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """
        Returnează statistici globale pentru header-ul aplicației.

        Returns:
            dict cu:
            {
                "total_processed": int,      # total fișiere procesate vreodată
                "moved_today": int,          # fișiere mutate azi
                "in_quarantine": int,        # fișiere în carantină nerezolvate
                "failed": int,               # fișiere cu eroare
                "success_rate": float        # procent 0.0-1.0
            }

        TODO (Inginer 3): Înlocuiește cu:
            today = datetime.utcnow().strftime("%Y-%m-%d")
            total = self._conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
            moved_today = self._conn.execute(
                "SELECT COUNT(*) FROM files WHERE status='moved' AND timestamp LIKE ?",
                (today + "%",)
            ).fetchone()[0]
            in_q = self._conn.execute(
                "SELECT COUNT(*) FROM quarantine WHERE user_decision IS NULL"
            ).fetchone()[0]
            failed = self._conn.execute(
                "SELECT COUNT(*) FROM files WHERE status='failed'"
            ).fetchone()[0]
            success_rate = (total - failed) / total if total > 0 else 0.0
            return {"total_processed": total, "moved_today": moved_today,
                    "in_quarantine": in_q, "failed": failed, "success_rate": success_rate}
        """
        total = len(_HARDCODED_FILES)
        failed = sum(1 for f in _HARDCODED_FILES if f["status"] == "failed")
        in_q = len(self.get_quarantine_items())
        moved_today = sum(
            1 for f in _HARDCODED_FILES
            if f["status"] == "moved" and f["timestamp"].startswith(
                datetime.utcnow().strftime("%Y-%m-%d")
            )
        )
        success_rate = (total - failed) / total if total > 0 else 0.0
        return {
            "total_processed": total,
            "moved_today": moved_today,
            "in_quarantine": in_q,
            "failed": failed,
            "success_rate": round(success_rate, 3),
        }

    # ------------------------------------------------------------------
    # Metoda 7 — Istoricul complet al activității (pentru tab Activity)
    # ------------------------------------------------------------------

    def get_activity_log(self, limit: int = 50) -> list[dict]:
        """
        Returnează log-ul de activitate cu suport pentru Undo.

        Returns:
            list[dict] cu structura ActivityEntry (câmpuri: id, file_record,
            action, undo_original_path, undo_available, recorded_at).
            Ordonate descendent după recorded_at.

        TODO (Inginer 3): Înlocuiește cu:
            cursor = self._conn.execute(
                '''SELECT a.*, f.*
                   FROM activity a
                   JOIN files f ON a.file_id = f.id
                   ORDER BY a.recorded_at DESC
                   LIMIT ?''',
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
        """
        return _HARDCODED_ACTIVITY[:limit]
