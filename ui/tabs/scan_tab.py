from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QTextEdit,
    QFileDialog,
)


from core.scan_worker import ScanWorker


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
        self.rule_label = QLabel("AI Organizing Rule:")
        self.rule_input = QLineEdit()
        self.rule_input.setPlaceholderText(
            "e.g., Pune facturile in folderul FacturiNou"
        )
        rule_layout.addWidget(self.rule_label)
        rule_layout.addWidget(self.rule_input)

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

        # Add all to main layout
        layout.addLayout(source_layout)
        layout.addLayout(dest_layout)
        layout.addLayout(rule_layout)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.progress_bar)
        layout.addWidget(QLabel("Logs:"))
        layout.addWidget(self.log_area)

        self.setLayout(layout)

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
            or not self.rule_input.text()
        ):
            self.log_area.append(
                "⚠️ Selectează folderele și introdu o regulă de organizare AI."
            )
            return

        self.start_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.log_area.clear()

        # Pornim worker-ul AI de scanare
        self.scan_thread = ScanWorker(
            source_dir=self.source_input.text(),
            dest_dir=self.dest_input.text(),
            user_rule=self.rule_input.text(),
        )
        self.scan_thread.progress_updated.connect(self.update_progress)
        self.scan_thread.log_updated.connect(self.append_log)
        self.scan_thread.scan_finished.connect(self.scan_complete)
        self.scan_thread.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def append_log(self, message):
        self.log_area.append(message)

    def scan_complete(self, added_count):
        self.start_btn.setEnabled(True)
        if added_count > 0:
            self.log_area.append(
                "\n💡 Mergi la tab-ul 'Quarantine' pentru a aproba sau respinge fișierele."
            )
