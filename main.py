import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from ui.app_window import AppWindow


def main():
    app = QApplication(sys.argv)

    # Apply global stylesheet
    style_path = Path(__file__).parent / "ui" / "style.qss"
    if style_path.exists():
        app.setStyleSheet(style_path.read_text())
    else:
        print("Warning: style.qss not found!")

    # Start the Main Window
    window = AppWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
