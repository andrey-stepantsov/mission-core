#!/bin/bash
set -e
set -x

# Resolve Locations
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TOOLS_ROOT=$(dirname "$SCRIPT_DIR")
VENV_DIR="$TOOLS_ROOT/.venv"
REQ_FILE="$TOOLS_ROOT/requirements.txt"

# 1. Create Venv if missing
if [ ! -d "$VENV_DIR" ]; then
    printf "📦 Bootstrapping Python Environment...\n" >&2
    # Try system site-packages first (Docker optimization) -> Fallback to clean venv -> Fallback to no-pip
    python3 -m venv --system-site-packages "$VENV_DIR" || python3 -m venv "$VENV_DIR" || python3 -m venv --without-pip "$VENV_DIR"
    
    # Verify Pip
    if [ ! -x "$VENV_DIR/bin/pip" ]; then
        printf "⚠️  Pip not found in venv. Fetching get-pip.py...\n" >&2
        
        PY_VER=$("$VENV_DIR/bin/python3" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        if [[ "$PY_VER" == "3.8" || "$PY_VER" == "3.7" || "$PY_VER" == "3.6" ]]; then
            URL="https://bootstrap.pypa.io/pip/$PY_VER/get-pip.py"
        else
            URL="https://bootstrap.pypa.io/get-pip.py"
        fi
        
        curl -sSL "$URL" -o "$VENV_DIR/get-pip.py"
        "$VENV_DIR/bin/python3" "$VENV_DIR/get-pip.py" --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org
        rm "$VENV_DIR/get-pip.py"
    fi

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
