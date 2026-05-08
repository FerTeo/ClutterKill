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
)
from PyQt6.QtCore import Qt


class QuarantineTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # Main Splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- LEFT PANEL: Document Preview ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(
            0, 0, 10, 0
        )  # Add a bit of margin near the splitter

        # Scroll area for the preview (useful when actual images/PDFs are added)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none; background-color: transparent;")

        # Placeholder for the document
        self.preview_label = QLabel(
            "Document Preview\n(Prima pagină din PDF/Imagine va fi randată aici)"
        )
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setObjectName("previewPlaceholder")

        self.scroll_area.setWidget(self.preview_label)
        left_layout.addWidget(self.scroll_area)

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

        # Mock data for demonstration
        self.original_path_lbl = QLabel("C:/Downloads/Factura_Curent_Necunoscuta.pdf")
        self.original_path_lbl.setStyleSheet("color: #a0a0a0; font-style: italic;")
        self.original_path_lbl.setWordWrap(True)
        form_layout.addRow("Calea Originală:", self.original_path_lbl)

        self.proposed_name_input = QLineEdit()
        self.proposed_name_input.setText("Factura_Enel_AI_Fix.pdf")
        form_layout.addRow("Nume Propus:", self.proposed_name_input)

        folder_layout = QHBoxLayout()
        self.proposed_folder_input = QLineEdit()
        self.proposed_folder_input.setText("Facturi/Necesită_Atenție")

        self.btn_save_as = QPushButton("Modify")
        self.btn_save_as.clicked.connect(self.on_save_as_clicked)

        folder_layout.addWidget(self.proposed_folder_input)
        folder_layout.addWidget(self.btn_save_as)

        form_layout.addRow("Folder Destinație:", folder_layout)

        right_layout.addLayout(form_layout)
        right_layout.addStretch()

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

        # Set initial sizes: smaller preview, more room for the form (paths can be long)
        self.splitter.setSizes([350, 450])

        main_layout.addWidget(self.splitter)

    def on_save_as_clicked(self):
        from PyQt6.QtWidgets import QFileDialog
        import os

        # Deschide un dialog nativ de Salvare (permite alegerea unui folder și schimbarea numelui în același timp)
        initial_path = os.path.join(
            self.proposed_folder_input.text(), self.proposed_name_input.text()
        )
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Modify Path...",
            initial_path,
            "Toate Fisierele (*);;PDF (*.pdf);;Imagini (*.png *.jpg *.jpeg)",
        )

        # Dacă utilizatorul a selectat o destinație și nu a dat Cancel
        if file_path:
            # Separăm calea în folder și nume fișier
            folder = os.path.dirname(file_path)
            name = os.path.basename(file_path)

            # Actualizăm căsuțele de text vizual
            self.proposed_folder_input.setText(folder)
            self.proposed_name_input.setText(name)

    def on_approve_clicked(self):
        self.show_status("✔️ Approval processed!", "#4caf50")

    def on_reject_clicked(self):
        self.show_status("❌ File rejected!", "#ff5c5c")

    def show_status(self, text, color):
        from PyQt6.QtCore import QTimer

        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.status_label.show()
        # Ascundem notificarea dupa 2.5 secunde
        QTimer.singleShot(2500, self.status_label.hide)
