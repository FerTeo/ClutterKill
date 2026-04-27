from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHeaderView,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class ActivityTab(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager

        layout = QVBoxLayout(self)

        # Tabelul de istoric
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Dată & Oră", "Acțiune", "Fișier Original", "Fișier Nou", "Opțiuni"]
        )

        # Facem coloanele să se redimensioneze inteligent
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.table)

        self.refresh_data()

    def refresh_data(self):
        """Reîncarcă istoricul din baza de date dummy."""
        logs = self.db_manager.get_activity_log()
        self.table.setRowCount(len(logs))

        for row, log in enumerate(logs):
            # Formatare dată
            date_str = log["recorded_at"].replace("T", " ").replace("Z", "")
            self.table.setItem(row, 0, QTableWidgetItem(date_str))

            # Acțiune
            action_item = QTableWidgetItem(log["action"].upper())
            if log["action"] == "undone":
                action_item.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row, 1, action_item)

            # Fișier Original
            orig = log["undo_original_path"].split("/")[-1]
            self.table.setItem(row, 2, QTableWidgetItem(orig))

            # Fișier Nou (dacă există din file_record)
            new_file = log["file_record"].get("new_name", "")
            self.table.setItem(row, 3, QTableWidgetItem(new_file))

            # Buton Undo
            if log["undo_available"]:
                undo_btn = QPushButton("↩️ Undo")
                undo_btn.clicked.connect(
                    lambda checked, a_id=log["id"], r=row: self.handle_undo(a_id, r)
                )
                self.table.setCellWidget(row, 4, undo_btn)
            else:
                lbl = QTableWidgetItem("N/A")
                lbl.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 4, lbl)

    def handle_undo(self, activity_id: str, row: int):
        reply = QMessageBox.question(
            self,
            "Confirmare Undo",
            "Ești sigur că vrei să anulezi această acțiune? Fișierul va fi mutat la locația inițială.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            result = self.db_manager.undo_action(activity_id)
            if result.get("status") == "undone":
                QMessageBox.information(
                    self,
                    "Undo Reușit",
                    f"Acțiunea a fost anulată.\nCalea restaurată: {result.get('restored_path')}",
                )
                # WORKAROUND UI: Schimbăm vizual starea direct în tabel
                action_item = self.table.item(row, 1)
                action_item.setText("UNDONE")
                action_item.setForeground(Qt.GlobalColor.red)

                # Înlocuim butonul cu textul N/A
                lbl = QTableWidgetItem("N/A")
                lbl.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.removeCellWidget(row, 4)
                self.table.setItem(row, 4, lbl)
            else:
                QMessageBox.warning(
                    self, "Eroare Undo", result.get("message", "Eroare necunoscută.")
                )
