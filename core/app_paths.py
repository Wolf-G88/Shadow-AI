from __future__ import annotations

import os
from pathlib import Path


WINDOWS_APP_DIR = "Shadow AI"
UNIX_APP_DIR = ".shadow-ai"


def _resolve_shadow_home(
    os_name: str | None = None,
    home: Path | None = None,
    localappdata: str | None = None,
    appdata: str | None = None,
) -> Path:
    os_name = os_name or os.name

    if os_name == "nt":
        base = localappdata or appdata or os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return Path(base) / WINDOWS_APP_DIR
        if home is not None:
            return home / "AppData" / "Local" / WINDOWS_APP_DIR
        return Path.home() / "AppData" / "Local" / WINDOWS_APP_DIR

    if home is not None:
        return home / UNIX_APP_DIR
    return Path.home() / UNIX_APP_DIR


def get_shadow_home() -> Path:
    """Return the cross-platform base directory for user state."""
    return _resolve_shadow_home()


def ensure_shadow_home() -> Path:
    home = get_shadow_home()
    home.mkdir(parents=True, exist_ok=True)
    return home


def get_config_path() -> Path:
    return get_shadow_home() / "config.json"


def get_memory_path() -> Path:
    return get_shadow_home() / "memory.json"


def get_enhanced_learning_dir() -> Path:
    return get_shadow_home() / "enhanced_learning"


def get_personalization_path(user_id: str = "default") -> Path:
    return get_shadow_home() / f"user_profile_{user_id}.json"


def get_models_dir() -> Path:
    return get_shadow_home() / "models"
