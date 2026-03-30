from __future__ import annotations

import sys
from pathlib import Path


def get_resource_root() -> Path:
    """Return the base directory for bundled/static resources."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(__file__).resolve().parent.parent

