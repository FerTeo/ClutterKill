from PyQt6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget
from ui.tabs.scan_tab import ScanTab


class AppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ClutterKill - AI File Organizer")
        self.resize(800, 600)

        # Set up the central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)  # a bit of padding

        # Initialize the Tab Widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Add the ScanTab we just created
        self.scan_tab = ScanTab()
        self.tabs.addTab(self.scan_tab, "Scan")

        # (Future tabs like Rules, History, Quarantine will go here later)
