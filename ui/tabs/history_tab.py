from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
)
from PyQt6.QtCore import Qt, QTimer

from core.undo_manager import undo_manager


class HistoryTab(QWidget):
    """
    Tab-ul Activity History (US 10):
    Afișează ultimele 50 de fișiere mutate și un buton „Undo" pe fiecare rând,
    astfel încât utilizatorul să readucă instantaneu un fișier la locația originală.
    """

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.refresh()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("Activity History")
        header_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #0078d4;"
        )
        header_layout.addWidget(header_label)
        header_layout.addStretch()

        # Buton refresh
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh)
        header_layout.addWidget(self.btn_refresh)

        layout.addLayout(header_layout)

        # Tabel cu istoricul acțiunilor
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ["#", "Fisier Original", "Mutat La", "Actiune"]
        )
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)

        # Configuram coloanele
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(3, 100)

        layout.addWidget(self.table)

        # Status label
        self.status_label = QLabel("")
        self.status_label.hide()
        layout.addWidget(self.status_label)

        # Mesaj cand nu sunt actiuni
        self.empty_label = QLabel(
            "Nicio actiune inregistrata.\n"
            "Muta fisiere din Quarantine pentru a le vedea aici."
        )
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #7d7d7d; font-size: 14px;")
        self.empty_label.hide()
        layout.addWidget(self.empty_label)

    def refresh(self):
        """Reincarca tabelul cu datele din undo_manager."""
        history = undo_manager.get_history()
        self.table.setRowCount(0)

        if not history:
            self.table.hide()
            self.empty_label.show()
            return

        self.table.show()
        self.empty_label.hide()
        self.table.setRowCount(len(history))

        for i, action in enumerate(history):
            # Coloana #
            idx_item = QTableWidgetItem(str(i + 1))
            idx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 0, idx_item)

            # Coloana Fisier Original (doar numele)
            old_name = Path(action["old_path"]).name
            old_item = QTableWidgetItem(old_name)
            old_item.setToolTip(action["old_path"])  # Path complet in tooltip
            self.table.setItem(i, 1, old_item)

            # Coloana Mutat La (doar numele)
            new_name = Path(action["new_path"]).name
            new_item = QTableWidgetItem(new_name)
            new_item.setToolTip(action["new_path"])
            self.table.setItem(i, 2, new_item)

            # Coloana Undo (buton)
            btn_undo = QPushButton("Undo")
            btn_undo.setObjectName("rejectButton")
            btn_undo.clicked.connect(self._make_undo_handler(i))
            self.table.setCellWidget(i, 3, btn_undo)

    def _make_undo_handler(self, index):
        """Creeaza un handler pentru butonul Undo (captura index-ul prin closure)."""

        def handler():
            self._undo_action(index)

        return handler

    def _undo_action(self, index):
        """Anuleaza actiunea de la index-ul specificat."""
        success = undo_manager.undo_action(index)

        if success:
            self.show_status("Undo reusit! Fisierul a fost readus.", "#4caf50")
        else:
            self.show_status(
                "Nu s-a putut face undo (fisierul nu mai exista?).", "#ff5c5c"
            )

        self.refresh()

    def show_status(self, text, color):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.status_label.show()
        QTimer.singleShot(3000, self.status_label.hide)
