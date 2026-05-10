from pathlib import Path

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
from PyQt6.QtCore import QThread, pyqtSignal

from core.quarantine_db import quarantine_db

# Categorii de fișiere bazate pe extensie (placeholder până la integrarea AI)
EXTENSION_CATEGORIES = {
    ".pdf": "Documente/PDF",
    ".doc": "Documente/Word",
    ".docx": "Documente/Word",
    ".txt": "Documente/Text",
    ".rtf": "Documente/Text",
    ".xlsx": "Documente/Excel",
    ".xls": "Documente/Excel",
    ".csv": "Documente/CSV",
    ".pptx": "Documente/PowerPoint",
    ".ppt": "Documente/PowerPoint",
    ".jpg": "Imagini",
    ".jpeg": "Imagini",
    ".png": "Imagini",
    ".gif": "Imagini",
    ".bmp": "Imagini",
    ".svg": "Imagini",
    ".zip": "Arhive",
    ".rar": "Arhive",
    ".7z": "Arhive",
    ".tar": "Arhive",
    ".gz": "Arhive",
    ".py": "Cod",
    ".js": "Cod",
    ".html": "Cod",
    ".css": "Cod",
    ".java": "Cod",
    ".mp3": "Audio",
    ".wav": "Audio",
    ".mp4": "Video",
    ".avi": "Video",
    ".mkv": "Video",
}


class ScanThread(QThread):
    """
    Thread real de scanare care:
    1. Parcurge recursiv folderul sursă
    2. Categorizează fișierele după extensie (până la integrarea AI)
    3. Adaugă fiecare fișier în quarantine_db pentru review-ul utilizatorului
    """

    progress_updated = pyqtSignal(int)
    log_updated = pyqtSignal(str)
    scan_finished = pyqtSignal(int)  # emite numărul total de fișiere adăugate

    def __init__(self, source_dir: str, dest_dir: str):
        super().__init__()
        self.source_dir = Path(source_dir)
        self.dest_dir = Path(dest_dir)

    def run(self):
        # Colectăm toate fișierele din source (recursiv)
        files = [f for f in self.source_dir.rglob("*") if f.is_file()]
        total = len(files)

        if total == 0:
            self.log_updated.emit("⚠️ Niciun fișier găsit în folderul sursă.")
            self.scan_finished.emit(0)
            return

        self.log_updated.emit(f"🔍 {total} fișiere găsite. Se începe scanarea...")

        added_count = 0
        skipped_count = 0

        # Preluăm fișierele deja existente în carantină (pentru a evita duplicatele)
        existing_paths = {r["original_path"] for r in quarantine_db.get_all()}

        for i, file_path in enumerate(files):
            str_path = str(file_path)

            # Verificăm dacă fișierul e deja în carantină
            if str_path in existing_paths:
                skipped_count += 1
                self.log_updated.emit(
                    f"⏭️ {file_path.name} — deja în carantină, skip"
                )
            else:
                # Categorizare pe bază de extensie
                ext = file_path.suffix.lower()
                category = EXTENSION_CATEGORIES.get(ext, "Altele")
                proposed_folder = str(self.dest_dir / category)

                quarantine_db.add(
                    original_path=str_path,
                    ai_proposed_name=file_path.name,
                    ai_proposed_folder=proposed_folder,
                    reason=f"Categorizat automat după extensie: {ext or 'fără extensie'}",
                )
                added_count += 1

                self.log_updated.emit(
                    f"📄 {file_path.name} → 📂 {category}"
                )

            # Actualizăm progress bar-ul
            progress = int((i + 1) / total * 100)
            self.progress_updated.emit(progress)

        self.log_updated.emit(
            f"\n✅ Scanare completă! {added_count} fișiere adăugate, "
            f"{skipped_count} existente (skip)."
        )
        self.scan_finished.emit(added_count)


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
        if not self.source_input.text() or not self.dest_input.text():
            self.log_area.append(
                "⚠️ Selectează atât folderul sursă cât și cel destinație."
            )
            return

        self.start_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.log_area.clear()

        # Pornim thread-ul real de scanare
        self.scan_thread = ScanThread(
            source_dir=self.source_input.text(),
            dest_dir=self.dest_input.text(),
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
