from PyQt5.QtCore import Qt, QRectF, QSize, QVariantAnimation
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import QAbstractButton


class ToggleSwitch(QAbstractButton):
    """Animated ON/OFF switch used instead of two power buttons."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self._progress = 0.0
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(140)
        self._animation.valueChanged.connect(self._on_value)

    def sizeHint(self):
        return QSize(124, 56)

    def _on_value(self, value):
        self._progress = float(value)
        self.update()

    def _animate(self):
        self._animation.stop()
        self._animation.setStartValue(self._progress)
        self._animation.setEndValue(1.0 if self.isChecked() else 0.0)
        self._animation.start()

    def setChecked(self, checked):
        super().setChecked(bool(checked))
        self._animate()

    def nextCheckState(self):
        super().nextCheckState()
        self._animate()

    def setCheckedSilently(self, checked):
        blocked = self.blockSignals(True)
        self.setChecked(checked)
        self.blockSignals(blocked)

    @staticmethod
    def _mix(first: QColor, second: QColor, ratio: float) -> QColor:
        return QColor(
            int(first.red() + (second.red() - first.red()) * ratio),
            int(first.green() + (second.green() - first.green()) * ratio),
            int(first.blue() + (second.blue() - first.blue()) * ratio),
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        if not self.isEnabled():
            painter.setOpacity(0.4)

        rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        radius = rect.height() / 2.0
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._mix(QColor("#334155"), QColor("#10B981"), self._progress))
        painter.drawRoundedRect(rect, radius, radius)

        knob = rect.height() - 10
        left = rect.left() + 5 + self._progress * (rect.width() - knob - 10)
        painter.setBrush(QColor("#F8FAFC"))
        painter.drawEllipse(QRectF(left, rect.top() + 5, knob, knob))

        font = painter.font()
        font.setPixelSize(12)
        font.setBold(True)
        painter.setFont(font)
        if self._progress > 0.5:
            painter.setPen(QColor("#06281D"))
            painter.drawText(
                QRectF(rect.left() + 14, rect.top(), rect.width() - knob - 24, rect.height()),
                Qt.AlignVCenter | Qt.AlignLeft, "ON")
        else:
            painter.setPen(QColor("#94A3B8"))
            painter.drawText(
                QRectF(rect.left() + knob + 10, rect.top(), rect.width() - knob - 24, rect.height()),
                Qt.AlignVCenter | Qt.AlignRight, "OFF")
        painter.end()