#!/bin/bash
set -e

# Resolve Locations
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TOOLS_ROOT=$(dirname "$SCRIPT_DIR")
VENV_DIR="$TOOLS_ROOT/.venv"
REQ_FILE="$TOOLS_ROOT/requirements.txt"

# 1. Create Venv if missing
if [ ! -d "$VENV_DIR" ]; then
    printf "📦 Bootstrapping Python Environment...\n" >&2
    # Try system site-packages first (Docker optimization)
    python3 -m venv --system-site-packages "$VENV_DIR" || python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/python3" -m pip install --upgrade pip > /dev/null
fi

# 2. Install Dependencies (Lazy Sync)
HASH_FILE="$VENV_DIR/.req_hash"
if [ -f "$REQ_FILE" ]; then
    CURRENT_HASH=$(shasum "$REQ_FILE" 2>/dev/null || md5sum "$REQ_FILE" | awk '{print $1}')
    if [ ! -f "$HASH_FILE" ] || [ "$(cat "$HASH_FILE")" != "$CURRENT_HASH" ]; then
        printf "📦 Syncing Universal Dependencies...\n" >&2
        "$VENV_DIR/bin/python3" -m pip install -r "$REQ_FILE" > /dev/null
        echo "$CURRENT_HASH" > "$HASH_FILE"
    fi
fi

# 3. Execution
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$SCRIPT_DIR"
exec "$VENV_DIR/bin/python3" "$@"
