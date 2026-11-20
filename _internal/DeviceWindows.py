from typing import Dict, List

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import (QAbstractItemView, QDialog, QListWidgetItem,
                             QMessageBox, QWidget)

from _internal.Initialisation import merge_devices, scan_ble_devices
from _internal.Settings import (change_settings, device_key, find_device,
                                normalize_mac, normalize_uuid, remove_device,
                                set_active, settings, store_device, update_device)
from _internal.Utils import (MAC_WIDTH, ROW_ADDRESS_WIDTH, UUID_WIDTH,
                             WindowDragMixin, address_line, debugger,
                             display_name, load_ui_file, set_elided, set_mono,
                             spawn)

# ==== Row geometry: the only place to tune list row heights ====

SCAN_ROW_HEIGHT = 56      # search window row
DEVICE_ROW_HEIGHT = 82    # saved devices row
LIST_GAP = 8              # vertical gap between rows

FILTER_INDEX = {"all": 0, "saved": 1, "unsaved": 2}
FILTER_NAMES = ["all", "saved", "unsaved"]
NAME_WIDTH = 260


def tune_list(widget, row_height: int) -> None:
    """Item widgets own their visuals: fixed step, no selection layer."""
    widget.setSelectionMode(QAbstractItemView.NoSelection)
    widget.setFocusPolicy(Qt.NoFocus)
    widget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
    widget.setUniformItemSizes(True)
    widget.setSpacing(LIST_GAP)
    widget.setProperty("rowHeight", row_height)


def add_row(list_widget, row: QWidget, row_height: int) -> None:
    """Pin the widget and the item step to the same value so rows cannot overlap."""
    row.setFixedHeight(row_height)
    item = QListWidgetItem()
    item.setFlags(Qt.ItemIsEnabled)
    item.setSizeHint(QSize(0, row_height))
    list_widget.addItem(item)
    list_widget.setItemWidget(item, row)


class DeviceInfoWindow(WindowDragMixin, QDialog):
    """Small scrollable window with every bit of device information."""

    def __init__(self, main_window):
        super().__init__(main_window)
        if not load_ui_file(self, "DeviceInfoWindow.ui"):
            raise RuntimeError("DeviceInfoWindow.ui not found")
        self.main_window = main_window
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.close_btn.clicked.connect(self.hide)
        self.CloseButton.clicked.connect(self.hide)
        self.RefreshButton.clicked.connect(self.refresh)
        self.refresh()

    @debugger
    def refresh(self):
        device = self.main_window.device or {}
        strip = self.main_window.strip
        self.NameValue.setText(display_name(device) if device else "—")
        self.MacValue.setText(device.get("mac") or "—")
        self.UuidValue.setText(device.get("uuid") or "—")
        self.AddressValue.setText(strip.address if strip else "—")
        self.CharValue.setText(strip.characteristic if strip else "—")
        self.ConnectionValue.setText("подключено" if strip and strip.connected else "нет связи")
        self.PowerValue.setText("включена" if self.main_window.powered_on else "выключена")
        self.ColorValue.setText(str(tuple(strip.rgb)) if strip else "—")
        self.AutoOnValue.setText("да" if device.get("auto_power_on_start") else "нет")
        self.AutoOffValue.setText("да" if device.get("auto_power_off_exit") else "нет")
        self.ReconnectValue.setText(f"{device.get('reconnect_timeout_sec', 5)} сек")
        self.ScrollArea.verticalScrollBar().setValue(0)


class DeviceSettingsWindow(WindowDragMixin, QDialog):
    """Per-device settings; every change is persisted immediately."""

    def __init__(self, main_window, saved_window):
        super().__init__(saved_window)
        if not load_ui_file(self, "DeviceSettingsWindow.ui"):
            raise RuntimeError("DeviceSettingsWindow.ui not found")
        self.main_window = main_window
        self.saved_window = saved_window
        self.key = ""
        self._loading = False
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)

        self.close_btn.clicked.connect(self.hide)
        self.CloseButton.clicked.connect(self.hide)
        self.DeleteButton.clicked.connect(self.delete_clicked)
        self.NameEdit.editingFinished.connect(self.save_fields)
        self.MacEdit.editingFinished.connect(self.save_fields)
        self.UuidEdit.editingFinished.connect(self.save_fields)
        self.AutoOnStartChk.toggled.connect(self.save_flags)
        self.AutoOffExitChk.toggled.connect(self.save_flags)
        self.ReconnectSpin.editingFinished.connect(self.save_flags)

    @debugger
    def bind(self, key: str):
        device = find_device(key)
        self.key = key
        self._loading = True
        self.TitleName.setText(display_name(device))
        self.NameEdit.setText(device.get("name", ""))
        self.NameEdit.setCursorPosition(0)

        self.MacEdit.setText(device.get("mac", ""))
        self.MacEdit.setCursorPosition(0)

        self.UuidEdit.setText(device.get("uuid", ""))
        self.UuidEdit.setCursorPosition(0)

        self.AutoOnStartChk.setChecked(bool(device.get("auto_power_on_start", True)))
        self.AutoOffExitChk.setChecked(bool(device.get("auto_power_off_exit", True)))
        self.ReconnectSpin.setText(str(device.get("reconnect_timeout_sec", 5)))
        self._loading = False
        self.StatusLabel.setText("Изменения сохраняются автоматически")

    def _notify(self):
        self.saved_window.refresh()
        spawn(self.main_window.apply_settings())

    @debugger
    def save_fields(self):
        if self._loading or not self.key:
            return
        mac = normalize_mac(self.MacEdit.text())
        uuid = normalize_uuid(self.UuidEdit.text())
        if not mac and not uuid:
            self.StatusLabel.setText("Нужен хотя бы один адрес: MAC или UUID")
            return
        new_key = update_device(self.key, name=self.NameEdit.text().strip(), mac=mac, uuid=uuid)
        if not new_key:
            self.StatusLabel.setText("Не удалось сохранить")
            return
        self.key = new_key
        self.TitleName.setText(display_name(find_device(new_key)))
        self.StatusLabel.setText("Сохранено")
        self._notify()

    @debugger
    def save_flags(self, value=None):
        if self._loading or not self.key:
            return
        update_device(self.key,
                      auto_power_on_start=self.AutoOnStartChk.isChecked(),
                      auto_power_off_exit=self.AutoOffExitChk.isChecked(),
                      reconnect_timeout_sec=self.ReconnectSpin.text())
        self.StatusLabel.setText("Сохранено")
        self._notify()

    @debugger
    def delete_clicked(self, checked=False):
        device = find_device(self.key)
        answer = QMessageBox.question(
            self, "Удаление устройства",
            f"Удалить «{display_name(device)}» из сохранённых устройств?\n"
            "Настройки этой ленты будут потеряны.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        remove_device(self.key)
        self.key = ""
        self.hide()
        self.saved_window.refresh()
        spawn(self.main_window.apply_settings())


class SavedDevicesWindow(WindowDragMixin, QDialog):
    """Own devices: rename, configure, activate."""

    def __init__(self, main_window):
        super().__init__(main_window)
        if not load_ui_file(self, "SavedDevicesWindow.ui"):
            raise RuntimeError("SavedDevicesWindow.ui not found")
        self.main_window = main_window
        self._editor = None
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        tune_list(self.DevicesList, DEVICE_ROW_HEIGHT)
        self.close_btn.clicked.connect(self.hide)
        self.CloseButton.clicked.connect(self.hide)
        self.SearchButton.clicked.connect(main_window.open_search)
        self.refresh()

    @debugger
    def refresh(self):
        self.DevicesList.clear()
        devices = settings.devices
        self.EmptyLabel.setVisible(not devices)
        self.CountLabel.setText(f"Сохранено устройств: {len(devices)}")
        for device in devices:
            key = device_key(device)
            row = QWidget()
            if not load_ui_file(row, "DeviceRow.ui"):
                continue
            active = key == settings.default_device
            set_elided(row.NameLabel, display_name(device), NAME_WIDTH)
            set_mono(row.AddressLabel, address_line(device), ROW_ADDRESS_WIDTH)
            row.ActiveLabel.setVisible(active)
            row.ActivateButton.setEnabled(not active)
            row.ActivateButton.clicked.connect(lambda ch=False, k=key: self.activate(k))
            row.ConfigureButton.clicked.connect(lambda ch=False, k=key: self.configure(k))
            add_row(self.DevicesList, row, DEVICE_ROW_HEIGHT)

    @debugger
    def activate(self, key: str):
        set_active(key)
        self.refresh()
        spawn(self.main_window.switch_device(key))

    @debugger
    def configure(self, key: str):
        if self._editor is None:
            self._editor = DeviceSettingsWindow(self.main_window, self)
        self._editor.bind(key)
        self._editor.show()
        self._editor.raise_()
        self._editor.activateWindow()


class DeviceSearchWindow(WindowDragMixin, QDialog):
    """Discovery only: filters, search, checkboxes, save selected."""

    def __init__(self, main_window):
        super().__init__(main_window)
        if not load_ui_file(self, "DeviceSearchWindow.ui"):
            raise RuntimeError("DeviceSearchWindow.ui not found")
        self.main_window = main_window
        self.scanned: List[Dict] = []
        self.scanning = False
        self._rows: List[Dict] = []
        self._known: Dict[str, Dict] = {}
        self._checked = set()
        self._loading = False
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        tune_list(self.ScanList, SCAN_ROW_HEIGHT)

        self.close_btn.clicked.connect(self.hide)
        self.CloseButton.clicked.connect(self.hide)
        self.ScanButton.clicked.connect(lambda: spawn(self.scan()))
        self.SearchEdit.textChanged.connect(self.reload_list)
        self.FilterCombo.currentIndexChanged.connect(self.filter_changed)
        self.HideUnnamedChk.toggled.connect(self.filter_changed)
        self.SelectAllButton.clicked.connect(self.select_all)
        self.ClearButton.clicked.connect(self.clear_selection)
        self.SaveCheckedButton.clicked.connect(self.save_checked)

        self._loading = True
        self.FilterCombo.setCurrentIndex(FILTER_INDEX.get(settings.filter_mode, 0))
        self.HideUnnamedChk.setChecked(settings.hide_unnamed)
        self._loading = False
        self.reload_list()

    # ==== Filtering ====

    @debugger
    def filter_changed(self, value=None):
        if self._loading:
            return
        index = max(0, min(self.FilterCombo.currentIndex(), len(FILTER_NAMES) - 1))
        change_settings(filter_mode=FILTER_NAMES[index],
                        hide_unnamed=self.HideUnnamedChk.isChecked())
        self.reload_list()

    def _visible_rows(self) -> List[Dict]:
        saved_keys = {device_key(d) for d in settings.devices}
        text = self.SearchEdit.text().strip().lower()
        rows = []
        for device in merge_devices(settings.devices, self.scanned):
            key = device_key(device)
            self._known[key] = device
            saved = key in saved_keys
            if settings.filter_mode == "saved" and not saved:
                continue
            if settings.filter_mode == "unsaved" and saved:
                continue
            if settings.hide_unnamed and not device["name"] and not saved:
                continue
            haystack = f"{device['name']} {device['mac']} {device['uuid']}".lower()
            if text and text not in haystack:
                continue
            rows.append({**device, "key": key, "saved": saved})
        rows.sort(key=lambda d: (not d["saved"], not bool(d["name"]), (d["name"] or "я").lower()))
        return rows

    @debugger
    def reload_list(self, text=None):
        self._rows = self._visible_rows()
        self.ScanList.clear()
        available = set()
        for device in self._rows:
            row = QWidget()
            if not load_ui_file(row, "ScanRow.ui"):
                continue
            key = device["key"]
            set_elided(row.SelectBox, display_name(device), NAME_WIDTH)
            set_mono(row.MacLabel, device["mac"], MAC_WIDTH)
            set_mono(row.UuidLabel, device["uuid"], UUID_WIDTH)

            if device["saved"]:
                row.setProperty("saved", True)
                row.SelectBox.setProperty("saved", True)
                row.SelectBox.setChecked(True)
                row.SelectBox.setEnabled(False)
                row.SelectBox.setToolTip("Уже в сохранённых устройствах")
            else:
                available.add(key)
                row.setProperty("saved", False)
                row.SelectBox.setProperty("saved", False)
                row.SelectBox.setChecked(key in self._checked)
                row.SelectBox.toggled.connect(lambda state, k=key: self._on_check(k, state))

            row.style().unpolish(row)
            row.style().polish(row)
            add_row(self.ScanList, row, SCAN_ROW_HEIGHT)

        self._checked &= available
        self.SaveCheckedButton.setEnabled(bool(self._checked))
        if not self.scanning:
            saved_shown = sum(1 for d in self._rows if d["saved"])
            self.StatusLabel.setText(
                f"Показано: {len(self._rows)}  ·  сохранённых: {saved_shown}  ·  "
                f"отмечено новых: {len(self._checked)}")

    def _on_check(self, key: str, state: bool):
        if state:
            self._checked.add(key)
        else:
            self._checked.discard(key)
        self.SaveCheckedButton.setEnabled(bool(self._checked))

    @debugger
    def select_all(self, checked=False):
        self._checked.update(d["key"] for d in self._rows if not d["saved"])
        self.reload_list()

    @debugger
    def clear_selection(self, checked=False):
        self._checked.clear()
        self.reload_list()

    # ==== Scanning and saving ====

    async def scan(self):
        if self.scanning:
            return
        self.scanning = True
        self.ScanButton.setEnabled(False)
        self.StatusLabel.setText(f"Сканирование Bluetooth... {settings.scan_timeout_sec} сек")
        try:
            self.scanned = await scan_ble_devices(settings.scan_timeout_sec)
        except Exception as e:
            self.StatusLabel.setText(f"Ошибка сканирования: {e}")
        finally:
            self.scanning = False
            self.ScanButton.setEnabled(True)
            self.reload_list()

    @debugger
    def save_checked(self, checked=False):
        saved = 0
        for key in list(self._checked):
            device = self._known.get(key)
            if not device:
                continue
            if store_device(device.get("name", ""), device.get("mac", ""), device.get("uuid", "")):
                saved += 1
        self._checked.clear()
        self.reload_list()
        self.main_window.refresh_saved()
        self.StatusLabel.setText(f"Сохранено устройств: {saved}")
        spawn(self.main_window.apply_settings())