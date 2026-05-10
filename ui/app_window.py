from PyQt6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget
from ui.tabs.scan_tab import ScanTab
from ui.tabs.rules_tab import RulesTab
from ui.tabs.quarantine_tab import QuarantineTab


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

        # Add the RulesTab
        self.rules_tab = RulesTab()
        self.tabs.addTab(self.rules_tab, "Rules")

        # Add the QuarantineTab
        self.quarantine_tab = QuarantineTab()
        self.tabs.addTab(self.quarantine_tab, "Quarantine")

        # (Future tabs like History will go here later)
