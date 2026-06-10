from PyQt6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget
from ui.tabs.scan_tab import ScanTab
from ui.tabs.rules_tab import RulesTab
from ui.tabs.quarantine_tab import QuarantineTab
from ui.tabs.history_tab import HistoryTab


class AppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ClutterKill - AI File Organizer")
        self.resize(900, 650)

        # Set up the central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)  # a bit of padding

        # Initialize the Tab Widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Add the ScanTab
        self.scan_tab = ScanTab()
        self.tabs.addTab(self.scan_tab, "Scan")

        self.rules_tab = RulesTab()
        self.tabs.addTab(self.rules_tab, "Rules")

        # Add the QuarantineTab
        self.quarantine_tab = QuarantineTab()
        self.tabs.addTab(self.quarantine_tab, "Quarantine")

        # Add the HistoryTab (US 10)
        self.history_tab = HistoryTab()
        self.tabs.addTab(self.history_tab, "History")

        # Refresh tab-urile cu date din DB/undo_manager la schimbare
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index):
        """Refresh datele când utilizatorul schimbă tab-ul."""
        current_widget = self.tabs.widget(index)
        if hasattr(current_widget, "refresh"):
            current_widget.refresh()
