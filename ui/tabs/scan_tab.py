from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QTextEdit,
    QFileDialog,
)


from core.scan_worker import ScanWorker
import core.rules_db as rules_db


class ScanTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Source layout
        source_layout = QHBoxLayout()
        self.source_label = QLabel("Source:")
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("Select source directory...")
        self.source_browse_btn = QPushButton("Browse")
        self.source_browse_btn.clicked.connect(self.browse_source)
        source_layout.addWidget(self.source_label)
        source_layout.addWidget(self.source_input)
        source_layout.addWidget(self.source_browse_btn)

        # Destination layout
        dest_layout = QHBoxLayout()
        self.dest_label = QLabel("Destination:")
        self.dest_input = QLineEdit()
        self.dest_input.setPlaceholderText("Select destination directory...")
        self.dest_browse_btn = QPushButton("Browse")
        self.dest_browse_btn.clicked.connect(self.browse_dest)
        dest_layout.addWidget(self.dest_label)
        dest_layout.addWidget(self.dest_input)
        dest_layout.addWidget(self.dest_browse_btn)

        # Rule layout
        rule_layout = QHBoxLayout()
        self.rule_label = QLabel("Preset Formatare:")
        self.rule_combo = QComboBox()
        self.refresh_rules_btn = QPushButton("Refresh Preseturi")
        self.refresh_rules_btn.clicked.connect(self.load_saved_rules)
        
        rule_layout.addWidget(self.rule_label)
        rule_layout.addWidget(self.rule_combo, stretch=1)
        rule_layout.addWidget(self.refresh_rules_btn)

        # Start button
        self.start_btn = QPushButton("Start Scan")
        self.start_btn.setObjectName(
            "primaryButton"
        )  # Apply primary button style from QSS
        self.start_btn.clicked.connect(self.start_scan)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)

        # Log area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)

        layout.addLayout(source_layout)
        layout.addLayout(dest_layout)
        layout.addLayout(rule_layout)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.progress_bar)
        layout.addWidget(QLabel("Logs:"))
        layout.addWidget(self.log_area)

        self.setLayout(layout)
        self.load_saved_rules()

    def load_saved_rules(self):
        self.rule_combo.clear()
        rules = rules_db.get_all_rules()
        if not rules:
            self.rule_combo.addItem("Niciun preset salvat! Mergi în tab-ul Rules.")
            self.rule_combo.setEnabled(False)
        else:
            self.rule_combo.setEnabled(True)
            for r in rules:
                self.rule_combo.addItem(r['name'])

    def browse_source(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Source Directory")
        if directory:
            self.source_input.setText(directory)

    def browse_dest(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select Destination Directory"
        )
        if directory:
            self.dest_input.setText(directory)

    def start_scan(self):
        if (
            not self.source_input.text()
            or not self.dest_input.text()
            or not self.rule_combo.isEnabled()
            or self.rule_combo.count() == 0
        ):
            self.log_area.append("Selectează folderele și un preset valid.")
            return

        source = self.source_input.text()
        dest = self.dest_input.text()
        rule_name = self.rule_combo.currentText()

        # Disable UI
        self.start_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.log_area.clear()
        self.log_area.append("Se încarcă agenții AI...")

        # Start worker
        self.scan_thread = ScanWorker(
            source_dir=source,
            dest_dir=dest,
            user_rule=rule_name,
        )
        self.scan_thread.progress_updated.connect(self.update_progress)
        self.scan_thread.log_updated.connect(self.append_log)
        self.scan_thread.scan_finished.connect(self.scan_complete)
        self.scan_thread.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def append_log(self, message):
        # Scoatem spațiile de padding făcute pentru vechiul CMD
        msg = message.strip()
        if not msg:
            return

        # Stabilim o culoare de accent pe baza contextului
        color = "#89b4fa"  # Albastru default
        if "succes" in msg.lower() or "complet" in msg.lower():
            color = "#a6e3a1"  # Verde
        elif "eroare" in msg.lower() or "lipsă" in msg.lower():
            color = "#f38ba8"  # Roșu
        elif "carantină" in msg.lower() or "quarantine" in msg.lower() or "skip" in msg.lower():
            color = "#f9e2af"  # Galben
        elif "procesare" in msg.lower() or "vision" in msg.lower():
            color = "#cba6f7"  # Mov
            
        html = f"""
        <div style="background-color: #313244; border-left: 4px solid {color}; border-radius: 6px; padding: 10px; margin-bottom: 5px;">
            <span style="color: #cdd6f4; font-size: 13px;">{msg.replace('\\n', '<br>')}</span>
        </div>
        """
        self.log_area.append(html)

    def scan_complete(self, added_count):
        self.start_btn.setEnabled(True)
        if added_count > 0:
            self.append_log(
                "Mergi la tab-ul 'Quarantine' pentru a aproba sau respinge fișierele."
            )
