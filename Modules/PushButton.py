from PySide2.QtWidgets import QPushButton, QSizePolicy
from PySide2.QtCore import QVariantAnimation, QAbstractAnimation
from PySide2.QtGui import QColor

class PushButton(QPushButton):
    def __init__(self, title):
        super().__init__()
        self.setText(title)
        self._animation = QVariantAnimation(
            startValue=QColor("#4CAF50"),
            endValue=QColor("white"),
            duration=300
        )
        self._animation.valueChanged.connect(self._on_value_changed)
        self._update_stylesheet(QColor("white"), QColor("black"))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def _on_value_changed(self, color):
        foreground = (
            QColor("black")
            if self._animation.direction() == QAbstractAnimation.Forward
            else QColor("white")
        )
        self._update_stylesheet(color, foreground)

    def _update_stylesheet(self, background, foreground):

        self.setStyleSheet(
            """
        QPushButton{
            background-color: %s;
            border: none;
            color: %s;
            padding: 16px 32px;
            text-align: center;
            text-decoration: none;
            font-size: 16px;
            margin: 4px 2px;
            border: 2px solid #4CAF50;
        }
        """
            % (background.name(), foreground.name())
        )

    def enterEvent(self, event):
        self._animation.setDirection(QAbstractAnimation.Backward)
        self._animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animation.setDirection(QAbstractAnimation.Forward)
        self._animation.start()
        super().leaveEvent(event)
