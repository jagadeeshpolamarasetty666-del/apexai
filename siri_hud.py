import sys
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QObject
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QFont
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton
)

class HudSignals(QObject):
    show_hud = pyqtSignal(str)
    hide_hud = pyqtSignal()
    update_text = pyqtSignal(str)
    cancel_requested = pyqtSignal()

signals = HudSignals()

class SiriOrbWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedSize(360, 160)

        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 400, screen.height() - 220)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 14, 18, 14)

        top_bar = QHBoxLayout()
        self.label = QLabel("Apex Active", self)
        self.label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.label.setStyleSheet("color: #00F0FF; background: transparent;")
        top_bar.addWidget(self.label)
        top_bar.addStretch()

        self.close_btn = QPushButton("✕", self)
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton {
                color: #CBD5E1;
                background-color: rgba(239, 68, 68, 60);
                border: 1px solid rgba(239, 68, 68, 150);
                border-radius: 14px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #FFFFFF;
                background-color: rgba(239, 68, 68, 230);
                border: 1px solid #EF4444;
            }
        """)
        self.close_btn.clicked.connect(self.on_cancel_clicked)
        top_bar.addWidget(self.close_btn)

        main_layout.addLayout(top_bar)

        self.subtext = QLabel("", self)
        self.subtext.setFont(QFont("Segoe UI", 10))
        self.subtext.setStyleSheet("color: #F1F5F9; background: transparent;")
        self.subtext.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.subtext.setWordWrap(True)
        main_layout.addWidget(self.subtext)

        # Connect signals
        signals.show_hud.connect(self.display_state)
        signals.hide_hud.connect(self.hide_safely)
        signals.update_text.connect(self.set_subtext)

    def on_cancel_clicked(self):
        signals.cancel_requested.emit()
        self.label.setText("Cancelled")
        self.subtext.setText("Stopping...")
        self.hide_safely()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        gradient = QRadialGradient(180, 80, 160)
        gradient.setColorAt(0.0, QColor(15, 23, 42, 245))
        gradient.setColorAt(0.7, QColor(15, 23, 42, 230))
        gradient.setColorAt(1.0, QColor(0, 240, 255, 80))

        painter.setBrush(gradient)
        painter.setPen(QColor(0, 240, 255, 200))
        painter.drawRoundedRect(4, 4, 350, 150, 18, 18)

    @pyqtSlot(str)
    def display_state(self, message: str):
        try:
            self.label.setText(message)
            self.show()
            self.raise_()
            self.update()
        except Exception:
            pass

    @pyqtSlot(str)
    def set_subtext(self, text: str):
        try:
            self.subtext.setText(text)
            self.update()
        except Exception:
            pass

    @pyqtSlot()
    def hide_safely(self):
        try:
            self.hide()
        except Exception:
            pass