from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QButtonGroup,
    QStackedWidget,
    QListWidget,
    QAbstractItemView,
    QTextEdit,
    QGraphicsOpacityEffect,
)
from PyQt6.QtCore import (
    Qt,
    QPropertyAnimation,
    QEasingCurve,
    QSequentialAnimationGroup,
    QTimer,
)


class RulesTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # 1. Header / Segmented Control
        toggle_layout = QHBoxLayout()
        toggle_layout.setSpacing(0)  # Keep buttons attached like a pill
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)

        self.btn_visual = QPushButton("Visual Builder (Drag & Drop)")
        self.btn_visual.setCheckable(True)
        self.btn_visual.setChecked(True)
        self.btn_visual.setProperty("class", "segmentToggle")
        self.btn_visual.setObjectName("leftToggle")

        self.btn_ai = QPushButton("Advanced AI Mode")
        self.btn_ai.setCheckable(True)
        self.btn_ai.setProperty("class", "segmentToggle")
        self.btn_ai.setObjectName("rightToggle")

        self.mode_group.addButton(self.btn_visual, 0)
        self.mode_group.addButton(self.btn_ai, 1)

        toggle_layout.addWidget(self.btn_visual)
        toggle_layout.addWidget(self.btn_ai)
        toggle_layout.addStretch()

        main_layout.addLayout(toggle_layout)

        # 2. Stacked Widget
        self.stacked_widget = QStackedWidget()

        # --- Page 1: Visual Mode ---
        self.page_visual = QWidget()
        visual_layout = QHBoxLayout(self.page_visual)

        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Blocuri Disponibile:"))
        self.available_list = QListWidget()
        self.available_list.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.available_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.available_list.addItems(
            ["An", "Lună", "Emitent", "Tip Document", "Extensie"]
        )
        left_layout.addWidget(self.available_list)

        # Pulsating Arrow / Guidance Animation
        middle_layout = QVBoxLayout()
        middle_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.guide_label = QLabel("Trage Aici\n➔")
        self.guide_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.guide_label.setStyleSheet(
            "color: #0078d4; font-weight: bold; font-size: 16px;"
        )

        # Opacity Animation for the guide label to make it pulse
        self.opacity_effect = QGraphicsOpacityEffect(self.guide_label)
        self.guide_label.setGraphicsEffect(self.opacity_effect)

        self.anim_down = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_down.setDuration(1000)
        self.anim_down.setStartValue(1.0)
        self.anim_down.setEndValue(0.2)
        self.anim_down.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self.anim_up = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_up.setDuration(1000)
        self.anim_up.setStartValue(0.2)
        self.anim_up.setEndValue(1.0)
        self.anim_up.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self.pulse_anim = QSequentialAnimationGroup(self)
        self.pulse_anim.addAnimation(self.anim_down)
        self.pulse_anim.addAnimation(self.anim_up)
        self.pulse_anim.setLoopCount(-1)  # Infinite loop
        self.pulse_anim.start()

        middle_layout.addWidget(self.guide_label)

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Formatul Regulii:"))
        self.rule_list = QListWidget()
        self.rule_list.setObjectName("dropZone")  # Will style this with a dashed border
        self.rule_list.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.rule_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        right_layout.addWidget(self.rule_list)

        visual_layout.addLayout(left_layout)
        visual_layout.addLayout(middle_layout)
        visual_layout.addLayout(right_layout)

        self.stacked_widget.addWidget(self.page_visual)

        # --- Page 2: AI Mode ---
        self.page_ai = QWidget()
        ai_layout = QVBoxLayout(self.page_ai)

        self.ai_label = QLabel("Descrie regula de organizare în limbaj natural:")
        self.ai_prompt = QTextEdit()
        self.ai_prompt.setPlaceholderText(
            "Exemplu: Grupează toate facturile emise de eMAG sau PC Garage în folderul 'Facturi/An/Luna'."
        )

        ai_layout.addWidget(self.ai_label)
        ai_layout.addWidget(self.ai_prompt)

        self.stacked_widget.addWidget(self.page_ai)

        main_layout.addWidget(self.stacked_widget)

        # 3. Save Button & Success Message
        btn_layout = QHBoxLayout()

        self.save_success_label = QLabel("✔️ Rule saved")
        self.save_success_label.setStyleSheet("color: #4caf50; font-weight: bold;")
        self.save_success_label.hide()

        btn_layout.addWidget(self.save_success_label)
        btn_layout.addStretch()

        self.btn_save = QPushButton("Save Rule")
        self.btn_save.setObjectName("primaryButton")
        self.btn_save.setToolTip(
            "Funcționalitatea de salvare va fi disponibilă după implementarea bazei de date."
        )
        btn_layout.addWidget(self.btn_save)

        main_layout.addLayout(btn_layout)

        # Connect signals
        self.mode_group.idClicked.connect(self.switch_mode)
        self.btn_save.clicked.connect(self.on_save_clicked)

    def switch_mode(self, id):
        self.stacked_widget.setCurrentIndex(id)

    def on_save_clicked(self):
        self.save_success_label.show()
        # Hide it again automatically after 2.5 seconds
        QTimer.singleShot(2500, self.save_success_label.hide)
