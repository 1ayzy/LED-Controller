import asyncio
import os
import sys
from functools import wraps
from typing import Dict

from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from _internal.Paths import resource_path

DEBUG = True

MAC_WIDTH = 150
UUID_WIDTH = 270
ROW_ADDRESS_WIDTH = 330


def debugger(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if DEBUG:
            print(f"Started {func.__name__}")
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            print(f"Unexpected exception in {func.__name__}: {e}", file=sys.stderr)
            return None
        if DEBUG:
            print(f"Successfully executed {func.__name__}")
        return result
    return wrapper


def _task_done(task: asyncio.Task) -> None:
    if task.cancelled():
        return
    error = task.exception()
    if error:
        print(f"Async task error: {error}", file=sys.stderr)


def spawn(coro) -> asyncio.Task:
    task = asyncio.ensure_future(coro)
    task.add_done_callback(_task_done)
    return task


def load_ui_file(instance, ui_filename: str) -> bool:
    for path in (resource_path("ui", ui_filename), os.path.join("ui", ui_filename), ui_filename):
        if os.path.exists(path):
            try:
                uic.loadUi(path, instance)
                return True
            except Exception as e:
                print(f"UI load error {path}: {e}")
    return False


def mono_font() -> QFont:
    font = QFont("Menlo" if sys.platform == "darwin" else "Consolas")
    font.setStyleHint(QFont.Monospace)
    font.setPixelSize(11)
    return font


def set_mono(label, text: str, width: int) -> None:
    """Fixed-width monospace text, elided instead of wrapped so rows never overlap."""
    label.setFont(mono_font())
    text = text or "—"
    label.setText(label.fontMetrics().elidedText(text, Qt.ElideMiddle, max(40, width - 6)))
    label.setToolTip(text)


def set_elided(label, text: str, width: int) -> None:
    text = text or "—"
    label.setText(label.fontMetrics().elidedText(text, Qt.ElideRight, max(60, width)))
    label.setToolTip(text)


def display_name(device: Dict) -> str:
    """Custom name, otherwise the first 10 characters of UUID / MAC."""
    name = (device.get("name") or "").strip()
    if name:
        return name
    ident = device.get("uuid") or device.get("mac") or ""
    return ident[:10] if ident else "Не выбрано"


def address_line(device: Dict) -> str:
    parts = [value for value in (device.get("mac"), device.get("uuid")) if value]
    return "  ·  ".join(parts) if parts else "адрес неизвестен"


class WindowDragMixin:
    """Dragging for frameless windows."""

    old_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.old_pos:
            delta = event.globalPos() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPos()