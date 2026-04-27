from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class RulesTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        # Titlu
        title = QLabel("Reguli de Redenumire (Drag & Drop)")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        main_hlayout = QHBoxLayout()

        # 1. Panoul cu Blocurile Disponibile (Tokens)
        blocks_group = QGroupBox("Blocuri Logice")
        blocks_layout = QVBoxLayout(blocks_group)

        self.blocks_list = QListWidget()
        self.blocks_list.setDragEnabled(True)
        self.blocks_list.setAcceptDrops(False)
        self.blocks_list.setDefaultDropAction(Qt.DropAction.CopyAction)

        # Adăugăm blocurile disponibile
        tokens = [
            "[An]",
            "[Lună]",
            "[Zi]",
            "[Emitent]",
            "[Categorie]",
            "[Nume_Original]",
        ]
        for t in tokens:
            item = QListWidgetItem(t)
            self.blocks_list.addItem(item)

        blocks_layout.addWidget(self.blocks_list)
        main_hlayout.addWidget(blocks_group)

        # 2. Panoul Editorului de Regulă
        editor_group = QGroupBox("Construiește Regula")
        editor_layout = QVBoxLayout(editor_group)

        self.rule_builder = QListWidget()
        self.rule_builder.setAcceptDrops(True)
        self.rule_builder.setDragEnabled(True)
        self.rule_builder.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.rule_builder.setDefaultDropAction(Qt.DropAction.MoveAction)
        # Permitem și drop de la cealaltă listă
        self.rule_builder.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)

        editor_layout.addWidget(QLabel("Trage blocurile aici. Ordinea contează!"))
        editor_layout.addWidget(self.rule_builder)

        # Nume șablon și salvare
        save_layout = QHBoxLayout()
        self.template_name = QLineEdit()
        self.template_name.setPlaceholderText("Nume șablon (ex: Facturi Lunare)")
        self.save_btn = QPushButton("💾 Salvează Șablon")

        save_layout.addWidget(self.template_name)
        save_layout.addWidget(self.save_btn)

        editor_layout.addLayout(save_layout)
        main_hlayout.addWidget(editor_group)

        layout.addLayout(main_hlayout)

        # Info
        info_lbl = QLabel(
            "Regula curentă va dicta cum vor fi redenumite fișierele de către AI dacă se potrivesc categoriei setate."
        )
        info_lbl.setWordWrap(True)
        layout.addWidget(info_lbl)
