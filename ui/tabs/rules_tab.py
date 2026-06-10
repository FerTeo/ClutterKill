from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QLineEdit,
    QMessageBox,
    QGridLayout,
)
import core.rules_db as rules_db


class RulesTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_rules()

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        # 1. Left Panel: Saved Templates
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Preseturi Salvate"))

        self.rules_list = QListWidget()
        self.rules_list.itemClicked.connect(self.on_rule_clicked)
        left_layout.addWidget(self.rules_list)

        self.btn_delete = QPushButton("Șterge Preset")
        self.btn_delete.clicked.connect(self.on_delete_clicked)
        left_layout.addWidget(self.btn_delete)

        main_layout.addLayout(left_layout, stretch=1)

        # 2. Right Panel: Create New Template
        right_layout = QVBoxLayout()

        # Title
        title_label = QLabel("Creează un Șablon Strict (Template)")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        right_layout.addWidget(title_label)

        # Name Input
        right_layout.addWidget(QLabel("Nume Preset:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ex: Facturi cu Data și Magazinul")
        right_layout.addWidget(self.name_input)

        # Query Input
        query_label = QLabel(
            "Regulă Selecție (Fișierele care nu se potrivesc se duc în Carantină):"
        )
        query_label.setStyleSheet("color: #f38ba8; font-weight: bold;")
        right_layout.addWidget(query_label)
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Ex: Toate facturile emise de eMAG")
        right_layout.addWidget(self.query_input)

        # Naming Template Input
        right_layout.addWidget(
            QLabel("Format Nume Fișier (Click pe butoane ca să inserezi!):")
        )

        self.naming_input = QLineEdit()
        self.naming_input.setPlaceholderText("Ex: [An]-[Luna]_[Emitent]_[SubiectAI]")
        right_layout.addWidget(self.naming_input)

        # Visual Builder Palette
        palette_layout = QGridLayout()
        variables = [
            "[An]",
            "[Luna]",
            "[TipDocument]",
            "[Emitent]",
            "[SubiectAI]",
            "_",
            "-",
        ]
        row, col = 0, 0
        for var in variables:
            btn = QPushButton(var)
            if var in ["_", "-"]:
                btn.setProperty("separatorButton", True)
            else:
                btn.setProperty("variableButton", True)

            btn.clicked.connect(lambda checked, v=var: self.insert_variable(v))
            palette_layout.addWidget(btn, row, col)
            col += 1
            if col > 3:
                col = 0
                row += 1

        right_layout.addLayout(palette_layout)

        right_layout.addStretch()

        # Save Button
        self.btn_save = QPushButton("Salvează Șablonul")
        self.btn_save.setObjectName("primaryButton")
        self.btn_save.clicked.connect(self.on_save_clicked)
        right_layout.addWidget(self.btn_save)

        main_layout.addLayout(right_layout, stretch=2)

    def load_rules(self):
        self.rules_list.clear()
        rules = rules_db.get_all_rules()
        for r in rules:
            self.rules_list.addItem(r["name"])

    def insert_variable(self, text: str):
        """Inserează variabila la cursor în căsuța de nume."""
        self.naming_input.insert(text)
        self.naming_input.setFocus()

    def on_rule_clicked(self, item):
        """Populează formularul cu datele regulii selectate pentru editare."""
        rule_name = item.text()
        rule_record = rules_db.get_rule_by_name(rule_name)
        if rule_record:
            self.name_input.setText(rule_record["name"])
            self.query_input.setText(rule_record["query"])
            self.naming_input.setText(rule_record["naming_template"])

    def on_delete_clicked(self):
        selected_items = self.rules_list.selectedItems()
        if not selected_items:
            return

        rule_name = selected_items[0].text()
        reply = QMessageBox.question(
            self, "Confirmare", f"Ești sigur că vrei să ștergi presetul '{rule_name}'?"
        )
        if reply == QMessageBox.StandardButton.Yes:
            if rules_db.delete_rule(rule_name):
                self.load_rules()
            else:
                QMessageBox.warning(self, "Eroare", "Nu am putut șterge presetul.")

    def on_save_clicked(self):
        name = self.name_input.text().strip()
        query = self.query_input.text().strip()
        naming = self.naming_input.text().strip()

        if not name or not query or not naming:
            QMessageBox.warning(
                self, "Avertisment", "Te rog să completezi toate cele 3 câmpuri."
            )
            return

        # Folder template is hardcoded to root (empty) since user wants it flattened
        if rules_db.save_rule(name, query, "", naming):
            QMessageBox.information(self, "Succes", f"Presetul '{name}' a fost salvat!")
            self.name_input.clear()
            self.query_input.clear()
            self.naming_input.clear()
            self.load_rules()
        else:
            QMessageBox.critical(
                self, "Eroare", "Nu am putut salva presetul în baza de date."
            )
