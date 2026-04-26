from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

# Importăm DatabaseManager-ul dummy pentru a prelua statisticile
from database.dummy_repository import DatabaseManager
from ui.tabs.activity_tab import ActivityTab

# Importăm tab-urile (le vom crea imediat)
from ui.tabs.dashboard_tab import DashboardTab
from ui.tabs.quarantine_tab import QuarantineTab
from ui.tabs.rules_tab import RulesTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ClutterKill - AI Desktop Assistant")
        self.resize(1000, 700)

        # Instanțiem managerul bazei de date (dummy)
        self.db_manager = DatabaseManager()

        # Widget-ul principal
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 1. Header (Statistici)
        self.header_frame = self._create_header()
        main_layout.addWidget(self.header_frame)

        # 2. QTabWidget pentru navigare principală
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(
            QTabWidget.TabPosition.West
        )  # Tab-uri pe stânga ca un sidebar
        main_layout.addWidget(self.tabs)

        # Inițializăm și adăugăm tab-urile
        self.dashboard_tab = DashboardTab(self.db_manager)
        self.rules_tab = RulesTab()
        self.quarantine_tab = QuarantineTab(self.db_manager)
        self.activity_tab = ActivityTab(self.db_manager)

        self.tabs.addTab(self.dashboard_tab, "🚀 Dashboard")
        self.tabs.addTab(self.rules_tab, "⚙️ Rules Builder")
        self.tabs.addTab(self.quarantine_tab, "⚠️ Quarantine Zone")
        self.tabs.addTab(self.activity_tab, "🕒 Activity History")

        # Refresh UI când se schimbă tab-ul
        self.tabs.currentChanged.connect(self.on_tab_changed)

    def _create_header(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QHBoxLayout(frame)

        title_label = QLabel("🔪 ClutterKill")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)

        self.stats_label = QLabel()
        self._update_stats()

        layout.addWidget(title_label)
        layout.addStretch()
        layout.addWidget(self.stats_label)

        return frame

    def _update_stats(self):
        stats = self.db_manager.get_stats()
        success_rate_pct = stats["success_rate"] * 100
        stats_text = (
            f"Total: {stats['total_processed']} | "
            f"Azi: {stats['moved_today']} | "
            f"Carantină: {stats['in_quarantine']} | "
            f"Erori: {stats['failed']} | "
            f"Succes: {success_rate_pct:.1f}%"
        )
        self.stats_label.setText(stats_text)

    def on_tab_changed(self, index):
        # Facem refresh la date când intrăm pe tab-uri
        self._update_stats()
        current_widget = self.tabs.widget(index)
        if hasattr(current_widget, "refresh_data"):
            current_widget.refresh_data()
