#!/bin/bash
set -e

VENV_DIR="$HOME/.cache/mission-packs/mock-repo-venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Bootstrapping..." >&2
    python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/pip" install -r requirements.txt

exec "$VENV_DIR/bin/python3" "$@"
