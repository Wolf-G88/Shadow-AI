#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
  echo "Shadow AI is not installed yet. Running ./install.sh first..."
  ./install.sh
fi

# shellcheck disable=SC1091
source venv/bin/activate
exec python main.py "$@"
