# Shadow AI 2.75 Linux Install Guide

## Recommended Path: Source Install

Use this on most Linux distros:

```bash
git clone https://github.com/Wolf-G88/Shadow-AI.git
cd Shadow-AI
chmod +x install.sh run.sh
./install.sh
./run.sh
```

## Debian / Ubuntu Package

Use this when the `2.75` `.deb` asset is available:

```bash
wget https://github.com/Wolf-G88/Shadow-AI/releases/download/v2.75/shadow-ai-2.75.deb
sudo dpkg -i shadow-ai-2.75.deb
shadow-ai
```

## Notes

- Source install is the recommended fallback for Fedora, Arch, openSUSE, and similar distros.
- The Debian package sets up a local virtual environment under `/opt/shadow-ai/venv`.
- If optional GGUF dependencies fail, Shadow still installs its core runtime.
