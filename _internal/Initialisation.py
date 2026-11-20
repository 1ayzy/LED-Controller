import json
import os
from typing import Dict, List, Tuple

from bleak import BleakScanner

from _internal.Paths import data_dir
from _internal.Settings import clamp_rgb, device_key, normalize_mac, normalize_uuid


def split_address(value: str) -> Tuple[str, str]:
    """Return (mac, uuid) from a single address string."""
    uuid = normalize_uuid(value)
    if uuid:
        return "", uuid
    return normalize_mac(value), ""


async def scan_ble_devices(timeout: float = 5.0) -> List[Dict]:
    discovered = await BleakScanner.discover(timeout=timeout)
    devices = []
    for device in discovered:
        address = (getattr(device, "address", "") or "").strip()
        mac, uuid = split_address(address)
        if mac or uuid:
            devices.append({"name": (device.name or "").strip(), "mac": mac, "uuid": uuid})
    return devices


def merge_devices(saved: List[Dict], scanned: List[Dict]) -> List[Dict]:
    """Saved names win, scanned data fills missing MAC / UUID / name."""
    merged: List[Dict] = []

    def index_of(mac: str, uuid: str) -> int:
        for i, device in enumerate(merged):
            if (uuid and device["uuid"] == uuid) or (mac and device["mac"] == mac):
                return i
        return -1

    def put(device: Dict, priority: bool) -> None:
        mac, uuid = normalize_mac(device.get("mac")), normalize_uuid(device.get("uuid"))
        if not mac and not uuid:
            return
        name = (device.get("name") or "").strip()
        index = index_of(mac, uuid)
        if index < 0:
            merged.append({"name": name, "mac": mac, "uuid": uuid})
            return
        entry = merged[index]
        entry["mac"] = entry["mac"] or mac
        entry["uuid"] = entry["uuid"] or uuid
        looks_like_address = entry["name"] in (entry["mac"], entry["uuid"], "")
        if name and (priority or looks_like_address):
            entry["name"] = name

    for device in saved:
        put(device, True)
    for device in scanned:
        put(device, False)
    return merged


def get_all_presets() -> List[Dict]:
    directory = data_dir("presets")
    presets = []
    for entry in sorted(os.scandir(directory), key=lambda e: e.name):
        if not entry.is_file() or not entry.name.lower().endswith(".json"):
            continue
        try:
            with open(entry.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            rgb = data.get("rgb")
            if rgb is None:
                rgb = [data.get("r", 255), data.get("g", 255), data.get("b", 255)]
            presets.append({
                "name": data.get("name") or os.path.splitext(entry.name)[0],
                "rgb": clamp_rgb(rgb),
                "path": entry.path,
            })
        except (OSError, ValueError, TypeError):
            continue
    return presets


def save_preset(name: str, rgb: List[int]) -> str:
    directory = data_dir("presets")
    safe = "".join(ch if ch.isalnum() or ch in " _-" else "_" for ch in name).strip()
    path = os.path.join(directory, (safe or "preset").lower().replace(" ", "_") + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"name": name, "rgb": clamp_rgb(rgb)}, f, ensure_ascii=False, indent=2)
    return path


def delete_preset(path: str) -> None:
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError as e:
        print(f"Failed to delete preset: {e}")