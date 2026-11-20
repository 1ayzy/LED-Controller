import os
import sys


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def base_dir() -> str:
    """Root for read-only resources (source tree or PyInstaller bundle)."""
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def app_dir() -> str:
    """Root for writable data (settings, presets)."""
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return base_dir()


def resource_path(*parts) -> str:
    candidates = [
        os.path.join(base_dir(), *parts),
        os.path.join(base_dir(), "_internal", *parts),
        os.path.join(os.getcwd(), *parts),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]


def data_dir(*parts) -> str:
    path = os.path.join(app_dir(), *parts)
    os.makedirs(path, exist_ok=True)
    return path


def data_file(*parts) -> str:
    path = os.path.join(app_dir(), *parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path