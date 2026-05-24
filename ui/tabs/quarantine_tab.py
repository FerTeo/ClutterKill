import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QLineEdit,
    QFormLayout,
    QScrollArea,
    QListWidget,
    QFileDialog,
)
from PyQt6.QtCore import Qt, QTimer

from core.quarantine_db import quarantine_db
from core.file_manager import move_and_rename_file


class QuarantineTab(QWidget):
    def __init__(self):
        super().__init__()
        self.records = []  # Lista de fișiere din carantină (din DB)
        self.current_record = None  # Fișierul selectat curent
        self.init_ui()
        self.refresh()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # Main Splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- LEFT PANEL: File List + Document Preview ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)

        # Lista fișierelor din carantină
        list_label = QLabel("Fișiere în carantină:")
        list_label.setStyleSheet("font-weight: bold; margin-bottom: 4px;")
        left_layout.addWidget(list_label)

        self.file_list = QListWidget()
        self.file_list.currentRowChanged.connect(self.on_file_selected)
        left_layout.addWidget(self.file_list, stretch=1)

        # Scroll area for the preview
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none; background-color: transparent;")

        # Placeholder for the document preview
        self.preview_label = QLabel(
            "Document Preview\n(Selectează un fișier din listă)"
        )
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setObjectName("previewPlaceholder")

        self.scroll_area.setWidget(self.preview_label)
        left_layout.addWidget(self.scroll_area, stretch=1)

        # --- RIGHT PANEL: Form & Actions ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)

        header_label = QLabel("Quarantine / AI Suggestion")
        header_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; margin-bottom: 10px; color: #0078d4;"
        )
        right_layout.addWidget(header_label)

        form_layout = QFormLayout()

        # Calea originală (read-only label)
        self.original_path_lbl = QLabel("—")
        self.original_path_lbl.setStyleSheet("color: #a0a0a0; font-style: italic;")
        self.original_path_lbl.setWordWrap(True)
        form_layout.addRow("Calea Originală:", self.original_path_lbl)

        # Numele propus de AI (editabil - US 9)
        self.proposed_name_input = QLineEdit()
        self.proposed_name_input.setPlaceholderText("Numele propus de AI...")
        form_layout.addRow("Nume Propus:", self.proposed_name_input)

        # Folder destinație (editabil) + buton Modify
        folder_layout = QHBoxLayout()
        self.proposed_folder_input = QLineEdit()
        self.proposed_folder_input.setPlaceholderText("Folderul destinație...")

        self.btn_save_as = QPushButton("Modify")
        self.btn_save_as.clicked.connect(self.on_save_as_clicked)

        folder_layout.addWidget(self.proposed_folder_input)
        folder_layout.addWidget(self.btn_save_as)

        form_layout.addRow("Folder Destinație:", folder_layout)

        # Motivul AI (read-only)
        self.reason_lbl = QLabel("—")
        self.reason_lbl.setStyleSheet("color: #a0a0a0;")
        self.reason_lbl.setWordWrap(True)
        form_layout.addRow("Motiv AI:", self.reason_lbl)

        right_layout.addLayout(form_layout)
        right_layout.addStretch()

        # Mesaj când nu sunt fișiere
        self.empty_label = QLabel(
            "✅ Niciun fișier în carantină!\nRulează un Scan pentru a adăuga fișiere."
        )
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #7d7d7d; font-size: 14px;")
        self.empty_label.hide()
        right_layout.addWidget(self.empty_label)

        # Action Buttons & Status Label
        btn_layout = QHBoxLayout()

        self.status_label = QLabel("")
        self.status_label.hide()

        self.btn_reject = QPushButton("Reject / Șterge")
        self.btn_reject.setObjectName("rejectButton")
        self.btn_reject.clicked.connect(self.on_reject_clicked)

        self.btn_approve = QPushButton("Approve & Move")
        self.btn_approve.setObjectName("primaryButton")
        self.btn_approve.clicked.connect(self.on_approve_clicked)

        btn_layout.addWidget(self.status_label)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_reject)
        btn_layout.addWidget(self.btn_approve)

        right_layout.addLayout(btn_layout)

        # Add widgets to splitter
        self.splitter.addWidget(left_widget)
        self.splitter.addWidget(right_widget)

        # Set initial sizes
        self.splitter.setSizes([350, 450])

        main_layout.addWidget(self.splitter)

    # ─── Refresh & Data Loading ────────────────────────────────────────

    def refresh(self):
        """Reîncarcă lista de fișiere din quarantine_db."""
        self.file_list.clear()
        self.records = quarantine_db.get_all()

        if not self.records:
            self.current_record = None
            self._clear_form()
            self.empty_label.show()
            self.btn_approve.setEnabled(False)
            self.btn_reject.setEnabled(False)
            return

        self.empty_label.hide()
        self.btn_approve.setEnabled(True)
        self.btn_reject.setEnabled(True)

        for record in self.records:
            original_name = Path(record["original_path"]).name
            self.file_list.addItem(f"📄 {original_name}")

        # Selectăm primul fișier automat
        self.file_list.setCurrentRow(0)

    # ─── File Selection ────────────────────────────────────────────────

    def on_file_selected(self, row):
        """Când utilizatorul selectează un fișier din listă, afișăm detaliile."""
        if 0 <= row < len(self.records):
            self.current_record = self.records[row]
            self._populate_form(self.current_record)
        else:
            self.current_record = None
            self._clear_form()

    def _populate_form(self, record):
        """Completează formularul cu datele din DB."""
        self.original_path_lbl.setText(record["original_path"])
        self.proposed_name_input.setText(record["ai_proposed_name"])
        self.proposed_folder_input.setText(record["ai_proposed_folder"])
        self.reason_lbl.setText(record.get("reason", "—") or "—")

    def _clear_form(self):
        """Golește formularul."""
        self.original_path_lbl.setText("—")
        self.proposed_name_input.clear()
        self.proposed_folder_input.clear()
        self.reason_lbl.setText("—")

    # ─── Actions ───────────────────────────────────────────────────────

    def on_approve_clicked(self):
        """
        Approve & Move: Mută fișierul folosind file_manager (care înregistrează
        automat în undo_manager), apoi îl șterge din carantină.
        """
        if not self.current_record:
            return

        original_path = self.current_record["original_path"]
        new_name = self.proposed_name_input.text().strip()
        dest_folder = self.proposed_folder_input.text().strip()

        if not new_name or not dest_folder:
            self.show_status("⚠️ Completează numele și folderul!", "#ffa500")
            return

        try:
            # file_manager.move_and_rename_file mută fizic fișierul
            # și înregistrează acțiunea în undo_manager automat
            move_and_rename_file(original_path, dest_folder, new_name)

            # Salvăm eventualele editări ale utilizatorului înapoi în DB
            # și apoi ștergem din carantină
            quarantine_db.remove(self.current_record["id"])

            self.show_status("✔️ Fișier mutat cu succes!", "#4caf50")
            self.refresh()

        except FileNotFoundError:
            self.show_status("❌ Fișierul sursă nu mai există!", "#ff5c5c")
            # Ștergem din carantină dacă fișierul nu mai există
            quarantine_db.remove(self.current_record["id"])
            self.refresh()
        except Exception as e:
            self.show_status(f"❌ Eroare: {e}", "#ff5c5c")

    def on_reject_clicked(self):
        """Reject: Șterge fișierul din carantină (fișierul rămâne unde era)."""
        if not self.current_record:
            return

        quarantine_db.remove(self.current_record["id"])
        self.show_status("❌ Fișier scos din carantină.", "#ff5c5c")
        self.refresh()

    def on_save_as_clicked(self):
        """Deschide dialog pentru a modifica destinația."""
        initial_path = os.path.join(
            self.proposed_folder_input.text(), self.proposed_name_input.text()
        )
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Modify Path...",
            initial_path,
            "Toate Fisierele (*);;PDF (*.pdf);;Imagini (*.png *.jpg *.jpeg)",
        )

        if file_path:
            folder = os.path.dirname(file_path)
            name = os.path.basename(file_path)
            self.proposed_folder_input.setText(folder)
            self.proposed_name_input.setText(name)

    # ─── UI Helpers ────────────────────────────────────────────────────

    def show_status(self, text, color):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.status_label.show()
        QTimer.singleShot(3000, self.status_label.hide)
