from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class QuarantineTab(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager

        layout = QVBoxLayout(self)

        # Splitter principal
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- PARTEA STÂNGĂ: Lista de fișiere în carantină ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_layout.addWidget(QLabel("Fișiere în Carantină (Necesită Review):"))
        self.q_list = QListWidget()
        self.q_list.itemSelectionChanged.connect(self.on_item_selected)
        left_layout.addWidget(self.q_list)

        splitter.addWidget(left_widget)

        # --- PARTEA DREAPTĂ: Preview și Aprobare ---
        right_widget = QWidget()
        self.right_layout = QVBoxLayout(right_widget)
        self.right_layout.setContentsMargins(0, 0, 0, 0)

        # 1. Preview
        preview_group = QGroupBox("Preview Document (Prima pagină)")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_label = QLabel("Selectează un document pentru previzualizare.")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet(
            "background-color: #333; color: white; min-height: 200px;"
        )
        preview_layout.addWidget(self.preview_label)
        self.right_layout.addWidget(preview_group)

        # 2. Formular Aprobare
        form_group = QGroupBox("Propunere AI")
        form_layout = QFormLayout(form_group)

        self.reason_text = QTextEdit()
        self.reason_text.setReadOnly(True)
        self.reason_text.setMaximumHeight(60)
        form_layout.addRow("Motiv Carantină:", self.reason_text)

        self.suggested_name_edit = QLineEdit()
        form_layout.addRow("Nume Propus:", self.suggested_name_edit)

        self.approve_btn = QPushButton("✅ Aprobă Numele")
        self.approve_btn.setStyleSheet(
            "background-color: #388e3c; color: white; font-weight: bold; padding: 8px;"
        )
        self.approve_btn.clicked.connect(self.approve_current)
        form_layout.addRow("", self.approve_btn)

        self.right_layout.addWidget(form_group)

        splitter.addWidget(right_widget)
        splitter.setSizes([300, 500])

        layout.addWidget(splitter)

        self.current_q_item = None
        self.refresh_data()

    def refresh_data(self):
        """Reîncarcă datele din DB dummy."""
        self.q_list.clear()
        items = self.db_manager.get_quarantine_items()
        for item in items:
            display_text = f"{item['file_record']['original_name']}\n(Categoria propusă: {item['suggested_category']})"

            # Adăugăm item-ul normal în lista PyQt
            self.q_list.addItem(display_text)

            # Ne folosim de UserRole pentru a stoca dicționarul complet
            last_item = self.q_list.item(self.q_list.count() - 1)
            last_item.setData(Qt.ItemDataRole.UserRole, item)

    def on_item_selected(self):
        selected = self.q_list.selectedItems()
        if not selected:
            self.current_q_item = None
            self.suggested_name_edit.clear()
            self.reason_text.clear()
            self.preview_label.setText("Selectează un document.")
            return

        item_data = selected[0].data(Qt.ItemDataRole.UserRole)
        self.current_q_item = item_data

        self.suggested_name_edit.setText(item_data["ai_suggestion"])
        self.reason_text.setText(item_data["reason"])

        # Simulare Preview (În mod real s-ar folosi PyMuPDF)
        file_path = item_data["file_record"]["original_path"]
        self.preview_label.setText(f"[Preview Simulat]\nImaginea pentru:\n{file_path}")

    def approve_current(self):
        if not self.current_q_item:
            return

        new_name = self.suggested_name_edit.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Eroare", "Numele nu poate fi gol!")
            return

        q_id = self.current_q_item["id"]
        result = self.db_manager.approve_quarantine(q_id, new_name)

        if result.get("status") == "approved":
            QMessageBox.information(
                self, "Succes", f"Fișierul a fost aprobat cu numele: {new_name}"
            )
            # WORKAROUND UI: Ștergem vizual elementul din listă pentru că datele din dummy DB nu se mută real
            row = self.q_list.currentRow()
            if row != -1:
                self.q_list.takeItem(row)
            self.current_q_item = None
            self.suggested_name_edit.clear()
            self.reason_text.clear()
            self.preview_label.setText("Selectează un document.")
