import asyncio
from typing import Dict, List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QIcon, QPixmap
from PyQt5.QtWidgets import QApplication, QListWidgetItem, QMainWindow

from _internal.DeviceWindows import (DeviceInfoWindow, DeviceSearchWindow,
                                     SavedDevicesWindow)
from _internal.Initialisation import delete_preset, get_all_presets, save_preset
from _internal.LEDController import LEDStrip
from _internal.Settings import (change_settings, clamp_rgb, connect_address,
                                device_key, find_device, load_settings, settings,
                                update_device)
from _internal.Utils import (WindowDragMixin, debugger, display_name,
                             load_ui_file, spawn)


class MainWidget(WindowDragMixin, QMainWindow):
    """LED controller main window."""

    @debugger
    def __init__(self):
        super().__init__()
        if not load_ui_file(self, "MainWindow.ui"):
            raise RuntimeError("MainWindow.ui not found")
        self.setWindowFlags(Qt.FramelessWindowHint)

        self.strip: Optional[LEDStrip] = None
        self.device: Dict = {}
        self.powered_on = False
        self.running = False
        self.keep_alive_task = None
        self.presets: List[Dict] = []
        self.info_window = None
        self.saved_window = None
        self.search_window = None
        self._closing = False

        load_settings()

        self.InfoButton.clicked.connect(self.open_info)
        self.SavedDevicesButton.clicked.connect(self.open_saved)
        self.SearchDevicesButton.clicked.connect(self.open_search)
        self.PowerToggle.toggled.connect(self.toggle_clicked)
        self.ApplyColorButton.clicked.connect(lambda: spawn(self.apply_color()))
        self.close_btn.clicked.connect(self.close)
        self.minimize_btn.clicked.connect(self.showMinimized)
        self.SavePresetButton.clicked.connect(self.save_preset_clicked)
        self.RemovePresetButton.clicked.connect(self.remove_preset_clicked)
        self.PresetsList.itemClicked.connect(self.preset_clicked)
        for slider in (self.RSlider, self.GSlider, self.BSlider):
            slider.valueChanged[int].connect(self.update_color_preview)

        self.PowerToggle.setEnabled(False)
        self.set_rgb([255, 255, 255])
        self.update_presets()
        self.refresh_device_header()
        self.update_status_ui("Запуск...")
        spawn(self.startup())

    # ==== Windows ====

    @debugger
    def open_info(self, checked=False):
        if self.info_window is None:
            self.info_window = DeviceInfoWindow(self)
        self.info_window.refresh()
        self.info_window.show()
        self.info_window.raise_()
        self.info_window.activateWindow()

    @debugger
    def open_saved(self, checked=False):
        if self.saved_window is None:
            self.saved_window = SavedDevicesWindow(self)
        self.saved_window.refresh()
        self.saved_window.show()
        self.saved_window.raise_()
        self.saved_window.activateWindow()

    @debugger
    def open_search(self, checked=False):
        if self.search_window is None:
            self.search_window = DeviceSearchWindow(self)
        self.search_window.show()
        self.search_window.raise_()
        self.search_window.activateWindow()
        spawn(self.search_window.scan())

    def refresh_saved(self):
        if self.saved_window is not None:
            self.saved_window.refresh()

    @debugger
    def refresh_device_header(self):
        self.device = find_device(settings.default_device)
        self.DeviceNameLabel.setText(display_name(self.device))
        if self.info_window is not None:
            self.info_window.refresh()

    # ==== Devices ====

    async def startup(self):
        if settings.default_device:
            await self.switch_device(settings.default_device)
        else:
            self.update_status_ui("Устройство не выбрано")
            self.open_search()

    async def apply_settings(self):
        """Reconnect only when the actual BLE address changed."""
        current = self.strip.address if self.strip else ""
        target = connect_address(find_device(settings.default_device))
        self.refresh_device_header()
        if target != current:
            await self.switch_device(settings.default_device)

    async def switch_device(self, key: str):
        self.stop_keep_alive()
        if self.strip:
            old, self.strip = self.strip, None
            self.powered_on = False
            self.sync_toggle(False)
            await old.disconnect()

        self.device = find_device(key)
        self.refresh_device_header()
        if not self.device:
            self.PowerToggle.setEnabled(False)
            self.update_status_ui("Устройство не выбрано")
            return

        address = connect_address(self.device)
        self.strip = LEDStrip(address, display_name(self.device))
        self.set_rgb(self.device.get("last_rgb", [255, 255, 255]))
        self.strip.rgb = clamp_rgb(self.device.get("last_rgb", [255, 255, 255]))
        if not address:
            self.PowerToggle.setEnabled(False)
            self.update_status_ui("Для macOS нужен UUID: сохраните ленту из поиска")
            return

        self.update_status_ui(f"Подключение к {address}...")
        ok = await self.strip.connect()
        self.PowerToggle.setEnabled(ok)
        self.update_status_ui("Подключено" if ok else "Нет связи, повторим автоматически")
        self.start_keep_alive()
        if ok and self.device.get("auto_power_on_start", True):
            await self.set_power(True)

    # ==== Power and color ====

    @debugger
    def toggle_clicked(self, checked=False):
        spawn(self.set_power(bool(checked)))

    async def set_power(self, on: bool):
        if not self.strip:
            self.sync_toggle(False)
            self.update_status_ui("Устройство не выбрано")
            return
        self.update_status_ui("Включение..." if on else "Выключение...")
        ok = await (self.strip.power_on() if on else self.strip.power_off())
        self.powered_on = self.strip.powered
        self.sync_toggle(self.powered_on)
        self.PowerToggle.setEnabled(self.strip.connected)
        self.update_status_ui(("Включено" if on else "Выключено") if ok else "Команда не прошла")
        if self.info_window is not None:
            self.info_window.refresh()

    async def apply_color(self):
        if not self.strip:
            self.update_status_ui("Устройство не выбрано")
            return
        rgb = self.current_rgb()
        self.update_status_ui("Отправка цвета...")
        ok = await self.strip.set_color(*rgb)
        self.powered_on = self.strip.powered
        self.sync_toggle(self.powered_on)
        self.PowerToggle.setEnabled(self.strip.connected)
        if self.device:
            update_device(device_key(self.device), last_rgb=rgb)
            self.refresh_device_header()
        self.update_status_ui("Цвет применён" if ok else "Не удалось отправить цвет")

    def current_rgb(self) -> List[int]:
        return [self.RSlider.value(), self.GSlider.value(), self.BSlider.value()]

    def sync_toggle(self, state: bool):
        self.PowerToggle.setCheckedSilently(state)

    @debugger
    def set_rgb(self, rgb):
        for slider, value in zip((self.RSlider, self.GSlider, self.BSlider), clamp_rgb(rgb)):
            slider.blockSignals(True)
            slider.setValue(value)
            slider.blockSignals(False)
        self.update_color_preview()

    @debugger
    def update_color_preview(self, value=0):
        r, g, b = self.current_rgb()
        self.RValue.setText(str(r))
        self.GValue.setText(str(g))
        self.BValue.setText(str(b))
        self.ColorPreview.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); border-radius: 12px; border: 1px solid #334155;")

    def update_status_ui(self, message: str = ""):
        if not self.strip:
            self.StatusLabel.setText(message or "Устройство не выбрано")
            return
        state = "включена" if self.powered_on else "выключена"
        link = "подключено" if self.strip.connected else "нет связи"
        text = f"Лента {state}, {link}\nRGB {tuple(self.strip.rgb)}"
        self.StatusLabel.setText(f"{message}\n{text}" if message else text)

    # ==== Keep alive ====

    @debugger
    def start_keep_alive(self):
        if self.running:
            return
        self.running = True
        self.keep_alive_task = spawn(self.keep_alive_loop())

    @debugger
    def stop_keep_alive(self):
        self.running = False
        if self.keep_alive_task:
            self.keep_alive_task.cancel()
            self.keep_alive_task = None

    async def keep_alive_loop(self):
        while self.running:
            interval = int(self.device.get("reconnect_timeout_sec", 5)) if self.device else 5
            await asyncio.sleep(max(1, interval))
            if not self.running or not self.strip or self.strip.connected:
                continue
            self.update_status_ui("Переподключение...")
            ok = await self.strip.connect()
            self.PowerToggle.setEnabled(ok)
            if ok:
                await self.strip.apply_state()
            self.update_status_ui("Связь восстановлена" if ok else "Устройство недоступно")

    # ==== Presets ====

    @debugger
    def update_presets(self):
        self.PresetsList.clear()
        self.presets = get_all_presets()
        for preset in self.presets:
            item = QListWidgetItem(preset["name"])
            pixmap = QPixmap(22, 22)
            pixmap.fill(QColor(*preset["rgb"]))
            item.setIcon(QIcon(pixmap))
            item.setToolTip(f"RGB {tuple(preset['rgb'])}")
            self.PresetsList.addItem(item)

    @debugger
    def preset_clicked(self, item):
        row = self.PresetsList.row(item)
        if 0 <= row < len(self.presets):
            self.set_rgb(self.presets[row]["rgb"])
            spawn(self.apply_color())

    @debugger
    def save_preset_clicked(self, checked=False):
        rgb = self.current_rgb()
        name = self.PresetNameEdit.text().strip() or f"RGB {rgb[0]}-{rgb[1]}-{rgb[2]}"
        save_preset(name, rgb)
        self.PresetNameEdit.clear()
        self.update_presets()

    @debugger
    def remove_preset_clicked(self, checked=False):
        row = self.PresetsList.currentRow()
        if not 0 <= row < len(self.presets):
            self.update_status_ui("Выберите пресет в списке")
            return
        delete_preset(self.presets[row]["path"])
        self.update_presets()

    # ==== Shutdown ====

    def closeEvent(self, event):
        if self._closing:
            event.accept()
            QApplication.instance().quit()
            return
        event.ignore()
        spawn(self.shutdown())

    async def shutdown(self):
        self.stop_keep_alive()
        for window in (self.info_window, self.search_window, self.saved_window):
            if window is not None:
                window.hide()
        if self.strip:
            if self.powered_on and self.device.get("auto_power_off_exit", True):
                await self.strip.power_off()
            await self.strip.disconnect()
        self._closing = True
        self.close()