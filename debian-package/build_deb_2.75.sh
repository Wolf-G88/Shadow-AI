#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PKG_VERSION="2.75"
PKG_NAME="shadow-ai"
PKG_TEMPLATE_DIR="${SCRIPT_DIR}/${PKG_NAME}-${PKG_VERSION}"
BUILD_BASE="${SHADOW_BUILD_BASE:-/tmp/shadow-ai-deb-build}"
PKG_ROOT="${BUILD_BASE}/${PKG_NAME}-${PKG_VERSION}"
TEMP_OUTPUT_DEB="${BUILD_BASE}/${PKG_NAME}-${PKG_VERSION}.deb"
OUTPUT_DEB="${SCRIPT_DIR}/${PKG_NAME}-${PKG_VERSION}.deb"

echo "Preparing Debian package tree for ${PKG_NAME} ${PKG_VERSION}..."

rm -rf "${PKG_ROOT}"
mkdir -p "${BUILD_BASE}"
rm -f "${TEMP_OUTPUT_DEB}"
mkdir -p \
  "${PKG_ROOT}/DEBIAN" \
  "${PKG_ROOT}/opt/shadow-ai" \
  "${PKG_ROOT}/usr/bin" \
  "${PKG_ROOT}/usr/share/applications" \
  "${PKG_ROOT}/usr/share/pixmaps"

copy_source_tree() {
  python3 - "$REPO_ROOT" "${PKG_ROOT}/opt/shadow-ai" <<'PY'
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])

skip_dirs = {
    ".git",
    ".venv",
    ".venv-win",
    "venv",
    "__pycache__",
    ".pytest_cache",
}
skip_prefixes = (
    ".tmp-home",
)
skip_names = {
    "_tmp_sils_eval_smoke.json",
    "torch",
}
skip_suffixes = (
    ".deb",
    ".pyc",
    ".pyo",
    ".pyd",
)
skip_parts = {
    "debian-package",
}

def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    if parts & skip_parts:
        return True
    name = path.name
    path_str = path.as_posix()
    if name in skip_dirs or name in skip_names:
        return True
    if "/training/runtime_" in f"/{path_str}" or path_str.startswith("training/runtime_"):
        return True
    if "/Shadow training/output_" in f"/{path_str}" or path_str.startswith("Shadow training/output_"):
        return True
    if any(name.startswith(prefix) for prefix in skip_prefixes):
        return True
    if any(name.endswith(suffix) for suffix in skip_suffixes):
        return True
    return False

for root, dirs, files in os.walk(src):
    root_path = Path(root)
    rel_root = root_path.relative_to(src)
    if rel_root != Path(".") and should_skip(rel_root):
        dirs[:] = []
        continue

    dirs[:] = [d for d in dirs if not should_skip(rel_root / d)]

    target_root = dst / rel_root
    target_root.mkdir(parents=True, exist_ok=True)

    for file_name in files:
        rel_path = rel_root / file_name
        if should_skip(rel_path):
            continue
        src_file = src / rel_path
        dst_file = dst / rel_path
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dst_file)
PY
}

copy_source_tree

cp "${PKG_TEMPLATE_DIR}/DEBIAN/control" "${PKG_ROOT}/DEBIAN/control"
cp "${PKG_TEMPLATE_DIR}/DEBIAN/postinst" "${PKG_ROOT}/DEBIAN/postinst"
cp "${PKG_TEMPLATE_DIR}/usr/bin/shadow-ai" "${PKG_ROOT}/usr/bin/shadow-ai"
cp "${PKG_TEMPLATE_DIR}/usr/share/applications/shadow-ai.desktop" "${PKG_ROOT}/usr/share/applications/shadow-ai.desktop"
cp "${PKG_TEMPLATE_DIR}/usr/share/pixmaps/shadow-ai.svg" "${PKG_ROOT}/usr/share/pixmaps/shadow-ai.svg"

find "${PKG_ROOT}" -type d -exec chmod 0755 {} \;
find "${PKG_ROOT}" -type f -exec chmod 0644 {} \;
chmod 0755 "${PKG_ROOT}/DEBIAN/postinst"
chmod 0755 "${PKG_ROOT}/usr/bin/shadow-ai"

echo "Building ${OUTPUT_DEB}..."
dpkg-deb --build "${PKG_ROOT}" "${TEMP_OUTPUT_DEB}"
cp "${TEMP_OUTPUT_DEB}" "${OUTPUT_DEB}"

echo "Done: ${OUTPUT_DEB}"
