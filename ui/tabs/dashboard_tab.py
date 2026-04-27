from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class DashboardTab(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # 1. Configurare Sursă și Destinație
        config_group = QGroupBox("Configurare Scanare")
        config_layout = QFormLayout(config_group)

        # Folder Sursă
        self.src_layout = QHBoxLayout()
        self.src_path = QLineEdit()
        self.src_path.setPlaceholderText("Selectează folderul sursă (ex. Downloads)")
        self.src_btn = QPushButton("Browse...")
        self.src_btn.clicked.connect(self.browse_source)
        self.src_layout.addWidget(self.src_path)
        self.src_layout.addWidget(self.src_btn)
        config_layout.addRow("Folder Sursă:", self.src_layout)

        # Folder Destinație
        self.dst_layout = QHBoxLayout()
        self.dst_path = QLineEdit()
        self.dst_path.setPlaceholderText("Selectează folderul destinație (Arhivă)")
        self.dst_btn = QPushButton("Browse...")
        self.dst_btn.clicked.connect(self.browse_dest)
        self.dst_layout.addWidget(self.dst_path)
        self.dst_layout.addWidget(self.dst_btn)
        config_layout.addRow("Folder Destinație:", self.dst_layout)

        # Limita de citire PDF
        self.page_limit_spin = QSpinBox()
        self.page_limit_spin.setRange(1, 100)
        self.page_limit_spin.setValue(10)
        self.page_limit_spin.setToolTip(
            "Citește maxim X pagini din fiecare PDF pentru a salva timp/memorie."
        )
        config_layout.addRow("Limită pagini PDF:", self.page_limit_spin)

        layout.addWidget(config_group)

        # 2. Buton Start Masiv
        self.start_btn = QPushButton("🚀 START KILL")
        start_font = QFont()
        start_font.setPointSize(18)
        start_font.setBold(True)
        self.start_btn.setFont(start_font)
        self.start_btn.setMinimumHeight(60)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
        """)
        self.start_btn.clicked.connect(self.start_scan)
        layout.addWidget(self.start_btn)

        # 3. Progres
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Progres: %p% (Fișiere rămase: 0)")
        layout.addWidget(self.progress_bar)

        # 4. Minimalist Terminal Log
        log_label = QLabel("Real-time Log:")
        layout.addWidget(log_label)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet(
            "background-color: #1e1e1e; color: #00ff00; font-family: monospace;"
        )
        layout.addWidget(self.log_output)

        self.log_message(
            "Aplicația a fost inițializată. Aștept configurarea folderelor."
        )

        # Timer pentru simulare progres
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.simulate_progress)

    def browse_source(self):
        folder = QFileDialog.getExistingDirectory(self, "Selectează Folder Sursă")
        if folder:
            self.src_path.setText(folder)

    def browse_dest(self):
        folder = QFileDialog.getExistingDirectory(self, "Selectează Folder Destinație")
        if folder:
            self.dst_path.setText(folder)

    def log_message(self, message: str):
        self.log_output.append(message)
        # Scroll down
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def start_scan(self):
        if not self.src_path.text() or not self.dst_path.text():
            self.log_message(
                "⚠️ Eroare: Te rog să selectezi ambele foldere (Sursă și Destinație) înainte de a porni!"
            )
            return

        self.log_message(f"🚀 Pornire scanare folder: {self.src_path.text()} ...")
        self.log_message(f"⚙️ Limita de pagini PDF: {self.page_limit_spin.value()}")
        self.progress_bar.setValue(0)
        self.start_btn.setEnabled(False)
        self.log_message("Simulare: AI-ul analizează fișierele...")
        self.progress_timer.start(100)  # Rulează simularea la fiecare 100ms

    def simulate_progress(self):
        val = self.progress_bar.value()
        if val < 100:
            self.progress_bar.setValue(val + 2)
            if val % 20 == 0:
                self.log_message(f"Se procesează pachetul {val//20 + 1}...")
        else:
            self.progress_timer.stop()
            self.start_btn.setEnabled(True)
            self.log_message("✅ Scanare finalizată! (Test simulat completat)")
