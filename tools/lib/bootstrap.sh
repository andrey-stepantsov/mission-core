#!/bin/bash
set -e

# Resolve the absolute path of the tools root
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TOOLS_ROOT=$(dirname "$SCRIPT_DIR")

# Virtual Environment Location
OS_TYPE=$(uname -s)
ARCH_TYPE=$(uname -m)
RUNTIME=${MISSION_RUNTIME:-host}
VENV_DIR="$TOOLS_ROOT/.venv-${OS_TYPE}-${ARCH_TYPE}-${RUNTIME}"

# 1. Create Venv (Robust Mode)
if [ ! -d "$VENV_DIR" ]; then
    echo "Bootstrapping Mission Environment ($OS_TYPE-$ARCH_TYPE)..."
    
    # Try standard creation (might fail to install pip)
    python3 -m venv "$VENV_DIR" || true

    # CHECK: Did pip actually get installed?
    if [ ! -f "$VENV_DIR/bin/pip" ]; then
        # Detect Python Version inside the new venv
        PY_VER=$("$VENV_DIR/bin/python3" -c "import sys; print('%d.%d' % (sys.version_info.major, sys.version_info.minor))")
        
        # Determine correct URL based on version
        PIP_URL="https://bootstrap.pypa.io/get-pip.py"
        
        if [[ "$PY_VER" == "3.6" ]]; then
            PIP_URL="https://bootstrap.pypa.io/pip/3.6/get-pip.py"
        elif [[ "$PY_VER" == "3.7" ]]; then
            PIP_URL="https://bootstrap.pypa.io/pip/3.7/get-pip.py"
        elif [[ "$PY_VER" == "3.8" ]]; then
            PIP_URL="https://bootstrap.pypa.io/pip/3.8/get-pip.py"
        fi
        
        echo "⚠️  System Python ($PY_VER) is missing ensurepip. Fetching pip from $PIP_URL..."
        
        # Download and install
        curl -sSL "$PIP_URL" -o /tmp/get-pip.py
        "$VENV_DIR/bin/python3" /tmp/get-pip.py
        rm /tmp/get-pip.py
    fi

    # Upgrade pip to be safe
    "$VENV_DIR/bin/pip" install --upgrade pip
fi

# 2. Install dependencies
if [ -f "$TOOLS_ROOT/requirements.txt" ]; then
    "$VENV_DIR/bin/pip" install -r "$TOOLS_ROOT/requirements.txt" > /dev/null
fi

# 3. Export PYTHONPATH
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$SCRIPT_DIR"

# 4. Handover execution
exec "$VENV_DIR/bin/python3" "$@"
