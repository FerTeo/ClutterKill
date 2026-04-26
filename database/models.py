"""
database/models.py
==================
Definește contractul de date (schema) între backend și restul aplicației.

Aceste dataclass-uri reprezintă "limbajul comun" pe care:
  - Inginerul 3 îl va implementa cu SQLAlchemy/SQLite
  - Inginerul 4 îl va consuma în UI (PyQt6 table models)
  - Agenții AI îl vor folosi pentru a raporta rezultatele

⚠️  NU modifica câmpurile fără să anunți echipa — UI-ul și DB-ul
    depind de această schemă.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


# ---------------------------------------------------------------------------
# Enumerații — stările posibile ale unui fișier
# ---------------------------------------------------------------------------

class FileStatus(str, Enum):
    """Starea unui fișier în pipeline-ul ClutterKill."""
    PENDING     = "pending"       # în așteptarea procesării
    PROCESSING  = "processing"    # procesare în curs
    MOVED       = "moved"         # mutat cu succes
    QUARANTINED = "quarantined"   # trimis în Quarantine Zone
    UNDONE      = "undone"        # acțiunea a fost anulată (Undo)
    FAILED      = "failed"        # eroare la procesare


class FileCategory(str, Enum):
    """Categoriile pe care AI-ul le poate atribui unui document."""
    FACTURA          = "factura"
    CONTRACT         = "contract"
    CURS_UNIVERSITAR = "curs_universitar"
    RETETA_MEDICALA  = "reteta_medicala"
    CERTIFICAT       = "certificat"
    FOTO             = "foto"
    NECUNOSCUT       = "necunoscut"


# ---------------------------------------------------------------------------
# Schema principală — un fișier procesat
# ---------------------------------------------------------------------------

@dataclass
class FileRecord:
    """
    Reprezintă un fișier procesat de ClutterKill.

    JSON echivalent (folosit de DatabaseManager):
    {
        "id": "f001",
        "original_path": "/Users/demo/Downloads/scan_001.pdf",
        "original_name": "scan_001.pdf",
        "new_name": "factura_ACME_2024_01_15.pdf",
        "destination_path": "/Users/demo/Arhiva/Facturi/factura_ACME_2024_01_15.pdf",
        "category": "factura",
        "confidence": 0.92,
        "status": "moved",
        "timestamp": "2024-01-15T10:30:00Z",
        "page_count": 2,
        "size_bytes": 45312
    }
    """
    id: str
    original_path: str
    original_name: str
    new_name: str
    destination_path: str
    category: FileCategory | str
    confidence: float            # 0.0 – 1.0, scorul de certitudine al AI-ului
    status: FileStatus | str
    timestamp: str               # ISO 8601
    page_count: int = 0          # 0 pentru non-PDF
    size_bytes: int = 0


# ---------------------------------------------------------------------------
# Schema Quarantine — extinde FileRecord cu info despre ambiguitate
# ---------------------------------------------------------------------------

@dataclass
class QuarantineRecord:
    """
    Fișier trimis în Quarantine Zone — AI-ul nu a fost suficient de sigur.

    JSON echivalent:
    {
        "id": "q001",
        "file_record": { ...FileRecord... },
        "ai_suggestion": "factura_EMITENT_necunoscut_2024.pdf",
        "reason": "Confidence sub 0.70 — emitent neidentificat",
        "suggested_category": "factura",
        "quarantined_at": "2024-01-15T10:31:00Z",
        "user_decision": null    // null = nerezolvat, "approved" sau "rejected"
    }
    """
    id: str
    file_record: FileRecord
    ai_suggestion: str           # numele propus de AI
    reason: str                  # de ce a ajuns în carantină
    suggested_category: FileCategory | str
    quarantined_at: str          # ISO 8601
    user_decision: str | None = None   # None | "approved" | "rejected"


# ---------------------------------------------------------------------------
# Schema Activity History — log de acțiuni (pentru Undo)
# ---------------------------------------------------------------------------

@dataclass
class ActivityEntry:
    """
    O intrare în istoricul de activitate, folosită pentru funcția Undo.

    JSON echivalent:
    {
        "id": "a001",
        "file_record": { ...FileRecord... },
        "action": "moved",
        "undo_original_path": "/Users/demo/Downloads/scan_001.pdf",
        "undo_available": true,
        "recorded_at": "2024-01-15T10:30:00Z"
    }
    """
    id: str
    file_record: FileRecord
    action: str                  # "moved" | "renamed" | "quarantine_approved"
    undo_original_path: str      # path-ul original — necesar pentru Undo
    undo_available: bool         # False dacă fișierul sursă nu mai există
    recorded_at: str             # ISO 8601
