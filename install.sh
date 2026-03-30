#!/usr/bin/env bash

set -euo pipefail

APP_NAME="Shadow AI"
APP_VERSION="2.75"
PYTHON_MIN="3.10"
VENV_DIR="venv"

log() {
  printf '%s\n' "$1"
}

has_cmd() {
  command -v "$1" >/dev/null 2>&1
}

version_ge() {
  [ "$(printf '%s\n' "$1" "$2" | sort -V | head -n1)" = "$2" ]
}

detect_pkg_manager() {
  if has_cmd apt-get; then
    printf 'apt'
  elif has_cmd dnf; then
    printf 'dnf'
  elif has_cmd pacman; then
    printf 'pacman'
  elif has_cmd zypper; then
    printf 'zypper'
  else
    printf 'unknown'
  fi
}

install_system_deps() {
  local pkg_manager="$1"

  case "$pkg_manager" in
    apt)
      sudo apt-get update
      sudo apt-get install -y \
        python3 \
        python3-venv \
        python3-pip \
        python3-tk \
        python3-psutil \
        python3-pynvml \
        git \
        curl
      ;;
    dnf)
      sudo dnf install -y \
        python3 \
        python3-pip \
        python3-tkinter \
        python3-psutil \
        git \
        curl
      ;;
    pacman)
      sudo pacman -Sy --noconfirm \
        python \
        python-pip \
        tk \
        python-psutil \
        git \
        curl
      ;;
    zypper)
      sudo zypper --non-interactive install \
        python3 \
        python3-pip \
        python3-tk \
        python3-psutil \
        git \
        curl
      ;;
    *)
      log "Could not auto-install system packages on this distro."
      log "Please install Python, pip, tkinter, git, and curl manually, then run ./install.sh again."
      exit 1
      ;;
  esac
}

ensure_python() {
  if ! has_cmd python3; then
    local pkg_manager
    pkg_manager="$(detect_pkg_manager)"
    log "Python 3 was not found. Trying to install it with ${pkg_manager}..."
    install_system_deps "$pkg_manager"
  fi

  local py_version
  py_version="$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')"
  if ! version_ge "$py_version" "$PYTHON_MIN"; then
    log "Python ${py_version} found, but Python ${PYTHON_MIN}+ is required."
    exit 1
  fi
  log "Python ${py_version} detected."
}

ensure_tkinter() {
  if python3 -c "import tkinter" >/dev/null 2>&1; then
    log "tkinter detected."
    return
  fi

  local pkg_manager
  pkg_manager="$(detect_pkg_manager)"
  log "tkinter is missing. Trying to install required system packages with ${pkg_manager}..."
  install_system_deps "$pkg_manager"

  if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    log "tkinter is still unavailable after package install."
    exit 1
  fi
}

ensure_venv() {
  if [ ! -d "$VENV_DIR" ]; then
    log "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
  else
    log "Virtual environment already exists."
  fi
}

install_python_deps() {
  # shellcheck disable=SC1091
  source "${VENV_DIR}/bin/activate"
  python -m pip install --upgrade pip setuptools wheel

  local fallback_core=(
    ollama
    pillow
    gitpython
    requests
    torch
    numpy
    tqdm
    python-dotenv
    psutil
    pynvml
  )

  if [ -f "requirements.txt" ]; then
    log "Installing Python requirements..."
    if ! python -m pip install -r requirements.txt; then
      log "Full dependency install failed. Falling back to core runtime dependencies."
      python -m pip install "${fallback_core[@]}"
      log "Optional note: GGUF support may still need a manual install of llama-cpp-python."
    fi
  else
    log "requirements.txt not found. Installing core runtime dependencies."
    python -m pip install "${fallback_core[@]}"
  fi
}

check_optional_backends() {
  if has_cmd ollama; then
    log "Ollama CLI detected."
  else
    log "Ollama CLI not found. Local Ollama models will be unavailable until installed."
  fi
}

write_gitignore_if_missing() {
  if [ -f ".gitignore" ]; then
    return
  fi

  cat > .gitignore <<'EOF'
# Shadow AI - generated defaults
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
*.egg-info/
dist/
build/
EOF
}

main() {
  log "================================================"
  log "  ${APP_NAME} ${APP_VERSION} - Linux Installer"
  log "================================================"
  log ""
  log "This installer is source-first and meant to work across common Linux distros."
  log ""

  if [ "${EUID}" -eq 0 ]; then
    log "Running as root is not recommended."
    log "Please install as a normal user when possible."
  fi

  ensure_python
  ensure_tkinter
  ensure_venv
  install_python_deps
  check_optional_backends

  mkdir -p data docs
  chmod +x run.sh || true
  chmod +x main.py || true
  write_gitignore_if_missing

  log ""
  log "================================================"
  log "Installation complete."
  log "================================================"
  log "Run Shadow with: ./run.sh"
  log ""
  log "Notes:"
  log "- Debian package installs are still best for Debian/Ubuntu releases."
  log "- Source install is the recommended path for broader Linux compatibility."
  log "- If llama-cpp-python was skipped, GGUF mode may need manual setup later."
}

main "$@"
