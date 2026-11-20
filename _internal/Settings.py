import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from _internal.Paths import data_file, resource_path

SETTINGS_FILE = data_file("settings", "settings.json")
UUID_RE = re.compile(r"^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$")
FILTERS = ("all", "saved", "unsaved")


@dataclass
class DeviceConfig:
    """Per-strip configuration stored inside the saved devices list."""
    name: str = ""
    mac: str = ""
    uuid: str = ""
    auto_power_on_start: bool = True
    auto_power_off_exit: bool = True
    reconnect_timeout_sec: int = 5
    last_rgb: List[int] = field(default_factory=lambda: [255, 255, 255])


@dataclass
class AppSettings:
    devices: List[Dict] = field(default_factory=list)
    default_device: str = ""
    scan_timeout_sec: int = 5
    filter_mode: str = "all"
    hide_unnamed: bool = False


# Single instance: mutated in place so imported references stay valid
settings: AppSettings = AppSettings()


# ==== Normalization ====

def clamp_rgb(rgb) -> List[int]:
    try:
        values = [max(0, min(255, int(v))) for v in list(rgb)[:3]]
    except (TypeError, ValueError):
        return [255, 255, 255]
    return values if len(values) == 3 else [255, 255, 255]


def normalize_mac(value) -> str:
    raw = re.sub(r"[^0-9a-fA-F]", "", str(value or ""))
    if len(raw) != 12:
        return ""
    return ":".join(raw[i:i + 2].upper() for i in range(0, 12, 2))


def normalize_uuid(value) -> str:
    text = str(value or "").strip().upper()
    return text if UUID_RE.match(text) else ""


def device_key(device: Dict) -> str:
    return device.get("uuid") or device.get("mac") or ""


def connect_address(device: Dict) -> str:
    """macOS speaks UUID, everything else speaks MAC."""
    if sys.platform == "darwin":
        return device.get("uuid") or device.get("mac") or ""
    return device.get("mac") or device.get("uuid") or ""


def _coerce(value, default):
    if isinstance(default, bool):
        return bool(value)
    if isinstance(default, int):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
    if isinstance(default, str):
        return value if isinstance(value, str) else default
    if isinstance(default, list):
        return value if isinstance(value, list) else list(default)
    return value


def _clean_device(raw) -> Optional[Dict]:
    if not isinstance(raw, dict):
        return None
    clean = {key: _coerce(raw.get(key, default), default)
             for key, default in asdict(DeviceConfig()).items()}
    clean["name"] = clean["name"].strip()
    clean["mac"] = normalize_mac(clean["mac"])
    clean["uuid"] = normalize_uuid(clean["uuid"])
    clean["last_rgb"] = clamp_rgb(clean["last_rgb"])
    clean["reconnect_timeout_sec"] = max(1, min(60, clean["reconnect_timeout_sec"]))
    return clean if (clean["mac"] or clean["uuid"]) else None


def _clean(data: Dict) -> Dict:
    clean = {key: _coerce(data.get(key, default), default)
             for key, default in asdict(AppSettings()).items()}

    devices, seen = [], {}
    for raw in clean["devices"]:
        device = _clean_device(raw)
        if device is None:
            continue
        key = device_key(device)
        if key in seen:
            existing = seen[key]
            existing["mac"] = existing["mac"] or device["mac"]
            existing["uuid"] = existing["uuid"] or device["uuid"]
            existing["name"] = existing["name"] or device["name"]
            continue
        seen[key] = device
        devices.append(device)

    clean["devices"] = devices
    clean["filter_mode"] = clean["filter_mode"] if clean["filter_mode"] in FILTERS else "all"
    clean["scan_timeout_sec"] = max(2, min(30, clean["scan_timeout_sec"]))

    allowed = set()
    for device in devices:
        allowed.update(v for v in (device["mac"], device["uuid"]) if v)
    if clean["default_device"] not in allowed:
        clean["default_device"] = device_key(devices[0]) if devices else ""
    return clean


# ==== File operations ====

def _read() -> Dict:
    for path in (SETTINGS_FILE, resource_path("settings", "settings.json")):
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except (OSError, ValueError):
            continue
    return {}


def load_settings() -> AppSettings:
    for key, value in _clean(_read()).items():
        setattr(settings, key, value)
    if not os.path.exists(SETTINGS_FILE):
        save_settings()
    return settings


def save_settings() -> None:
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(asdict(settings), f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"Failed to save settings: {e}")


def reset_settings() -> None:
    for key, value in asdict(AppSettings()).items():
        setattr(settings, key, value)
    save_settings()


def change_settings(**kwargs) -> None:
    """Update only the provided fields, then persist immediately."""
    clean = _clean({**asdict(settings), **kwargs})
    for key in kwargs:
        if key in clean:
            setattr(settings, key, clean[key])
    save_settings()


# ==== Device CRUD ====

def find_device(key: str) -> Dict:
    for device in settings.devices:
        if key and key in (device.get("uuid"), device.get("mac")):
            return device
    return {}


def active_device() -> Dict:
    return find_device(settings.default_device)


def set_active(key: str) -> None:
    change_settings(default_device=key)


def store_device(name: str, mac: str, uuid: str) -> str:
    """Save a discovered device, keeping its custom name and settings."""
    mac, uuid = normalize_mac(mac), normalize_uuid(uuid)
    if not mac and not uuid:
        return ""
    devices = [dict(d) for d in settings.devices]
    for device in devices:
        if (uuid and device.get("uuid") == uuid) or (mac and device.get("mac") == mac):
            device["mac"] = device.get("mac") or mac
            device["uuid"] = device.get("uuid") or uuid
            if not device.get("name"):
                device["name"] = (name or "").strip()
            break
    else:
        devices.append(_clean_device({**asdict(DeviceConfig()),
                                      "name": name, "mac": mac, "uuid": uuid}))
    payload = {"devices": devices}
    if not settings.default_device:
        payload["default_device"] = uuid or mac
    change_settings(**payload)
    return uuid or mac


def update_device(key: str, **fields) -> str:
    """Edit a saved device; returns the (possibly new) key."""
    devices = [dict(d) for d in settings.devices]
    for index, device in enumerate(devices):
        if key not in (device.get("uuid"), device.get("mac")):
            continue
        clean = _clean_device({**device, **fields})
        if clean is None:
            return ""
        devices[index] = clean
        new_key = device_key(clean)
        payload = {"devices": devices}
        if settings.default_device == key:
            payload["default_device"] = new_key
        change_settings(**payload)
        return new_key
    return ""


def remove_device(key: str) -> None:
    devices = [d for d in settings.devices if device_key(d) != key]
    payload = {"devices": devices}
    if settings.default_device == key:
        payload["default_device"] = device_key(devices[0]) if devices else ""
    change_settings(**payload)