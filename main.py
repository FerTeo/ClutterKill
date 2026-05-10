import sys
import os
from PyQt6.QtWidgets import QApplication
from ui.app_window import AppWindow


def load_stylesheet():
    qss_path = os.path.join(os.path.dirname(__file__), "ui", "styles.qss")
    try:
        if os.path.exists(qss_path):
            with open(qss_path, "r", encoding="utf-8") as f:
                return f.read()
    except Exception as e:
        print(f"Failed to load stylesheet: {e}")
    return ""


def main():
    app = QApplication(sys.argv)

    # Apply the Dark Mode QSS we created earlier
    stylesheet = load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)

    # Start the Main Window
    window = AppWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
