# Shadow AI v2.75

> Open source, privacy-first, local-first AI assistance.
> No accounts. No telemetry. No paywall.

[![Release](https://img.shields.io/badge/release-v2.75-blue.svg)](https://github.com/Wolf-G88/Shadow-AI/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-yellow.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows-orange.svg)](https://kernel.org/)

## What Shadow AI Is

Shadow AI is a standalone assistant built around:

- privacy-first local control
- Wolfy-style structured memory
- SILS routing and cleanup
- safer shell execution
- optional stronger backends when the tiny local path is outmatched

The current runtime is tuned to be grounded instead of flashy:

- memory and retrieval first
- honest decline instead of fake confidence
- explicit command safety gates
- clearer agent-style planning
- local-first command and file workflows

## Install

### Recommended: Source Install

This is the recommended path for most Linux distros.

```bash
git clone https://github.com/Wolf-G88/Shadow-AI.git
cd Shadow-AI
chmod +x install.sh run.sh
./install.sh
./run.sh
```

`install.sh` is source-first and aims to work across common Linux setups. It checks Python, `venv`, `tkinter`, and core runtime dependencies. If an optional backend dependency fails, it still installs the core runtime.

### Debian / Ubuntu Package

For Debian-family releases, use the packaged release asset:

```bash
wget https://github.com/Wolf-G88/Shadow-AI/releases/download/v2.75/shadow-ai-2.75.deb
sudo dpkg -i shadow-ai-2.75.deb
shadow-ai
```

### Windows

For Windows source installs:

```powershell
git clone https://github.com/Wolf-G88/Shadow-AI.git
cd Shadow-AI
powershell -ExecutionPolicy Bypass -File .\install_windows.ps1 -AutoInstallPython
wscript .\run_windows.vbs
```

Windows keeps Shadow's local state under `%LOCALAPPDATA%\Shadow AI`.

## Linux Notes

- Debian packages are still best for Debian/Ubuntu releases.
- Source install is the right fallback for Fedora, Arch, openSUSE, and similar distros.
- If `llama-cpp-python` does not build on your system, Shadow still installs the core runtime and you can add GGUF support later.
- Ollama is optional. Shadow can still run local SILS logic and non-Ollama backends without it.

## Windows Notes

- `install_windows.ps1` creates and uses `.venv-win`.
- The default Windows install now uses `requirements-windows-core.txt` so the thin package stays small and reliable.
- `run_windows.bat` can call the installer with `-AutoInstallPython` when Python 3.10+ is missing and `winget` is available.
- `run_windows.vbs` is the normal Windows launcher and starts Shadow without flashing a `cmd` window.
- `ShadowAI.ico` is now the packaged Windows app icon for the installer, shortcuts, and Windows app bundle.
- First Windows launch can take a few minutes while `.venv-win` and the core runtime are installed.
- Windows bootstrap logs are written to `%TEMP%\shadow-ai-windows-install.log`.
- Optional GGUF support lives in `requirements-windows-optional.txt` and can be added later with:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_windows.ps1 -InstallOptionalBackends
```

- `build_windows_portable.ps1` creates a thin portable Windows bundle and `.zip` with the shipped TinyLM included.
- `build_windows_release.ps1` builds a PyInstaller app bundle and, when Inno Setup is installed, a Windows installer too.
- `build_windows_thin_release.ps1` builds the smaller Windows installer path based on source files plus the shipped TinyLM.
- The Windows release track is packaged separately as `Shadow AI V1.00 for Windows`.

### Windows Packaging

Portable bundle:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows_portable.ps1
```

Thin installer with bundled TinyLM:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows_thin_release.ps1
```

PyInstaller app bundle plus installer:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows_release.ps1 -SkipInstaller
```

If Inno Setup is installed and `ISCC.exe` is on PATH:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows_release.ps1
```

## Highlights in 2.75

- hardened SILS runtime path
- template-backed intent handling for fragile local tasks
- stronger local command safety behavior
- better file handling for text, code, docx, and image honesty fallback
- GPU-capable retraining flow on stronger machines
- improved runtime model auto-pick for best checkpoints
- cleaner warning behavior and green test suite

## Memory Model

Shadow remembers through its memory systems, not by secretly mutating the model every chat.

- live memory stores facts, preferences, and context
- structured retrieval is used for recall
- TinyLM behavior improves through retraining, not hidden online weight updates

That keeps memory inspectable, editable, and privacy-safe.

## Current Validation

Recent local validation on this codebase:

- full Python test suite: `65/65` passing
- hardened SILS benchmark: `32/32`

## Project Layout

- [main.py](main.py)
- [core/engine.py](core/engine.py)
- [core/enhanced_learning.py](core/enhanced_learning.py)
- [core/sils_backend.py](core/sils_backend.py)
- [output/gui.py](output/gui.py)
- [training](training)

## License

MIT. See [LICENSE](LICENSE).
