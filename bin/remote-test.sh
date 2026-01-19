#!/bin/bash
set -e
LOG_FILE="remote_test_$(date +%s).log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "🔍 S.H.I.E.L.D. Remote Diagnostics"
echo "================================"
echo "Host: $(hostname)"
echo "Date: $(date)"
echo "User: $(whoami)"
echo "Dir:  $(pwd)"

echo -e "\n1. OS Release Info:"
if [ -f /etc/os-release ]; then
    cat /etc/os-release
elif [ -f /etc/redhat-release ]; then
    cat /etc/redhat-release
else
    uname -a
fi

echo -e "\n2. Python Environment:"
echo "python3 executable: $(which python3)"
python3 --version || echo "python3 not found"
echo "pip3 executable: $(which pip3 || echo 'Not found in PATH')"
echo "python3 -m pip: $(python3 -m pip --version || echo 'Failed to load module')"

echo -e "\n3. Dependency Check:"
for tool in rsync git ssh tmux sudo; do
    echo -n "$tool: "
    which $tool || echo "MISSING"
done

echo -e "\n4. Mission Bootstrap Simulation:"
# Resolve Tools Root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Script is in bin/, need to go up and into tools/
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TOOLS_ROOT="$PROJECT_ROOT/tools"
VENV_DIR="$TOOLS_ROOT/.venv"
echo "Tools Root: $TOOLS_ROOT"

if [ -d "$VENV_DIR" ]; then
    echo "Found existing venv, removing for fresh test..."
    rm -rf "$VENV_DIR"
fi

echo "Attempting to create venv..."
# Mimic bootstrap.sh logic
if python3 -m venv --system-site-packages "$VENV_DIR"; then
    echo "✅ Venv created (system-site-packages)."
elif python3 -m venv "$VENV_DIR"; then
    echo "✅ Venv created (standard)."
else
    echo "❌ Venv creation failed."
fi

if [ -d "$VENV_DIR" ]; then
    PIP_BIN="$VENV_DIR/bin/pip"
    if [ ! -f "$PIP_BIN" ]; then
        echo "⚠️ Pip binary missing in venv. Ensuring pip..."
        # Try ensurepip
        python3 -m ensurepip --upgrade --root "$VENV_DIR" || echo "Ensurepip failed."
    fi
     
    echo "Testing pip install..."
    if "$VENV_DIR/bin/python3" -m pip install pyyaml; then
        echo "✅ Pip install successful (pyyaml)."
    else
        echo "❌ Pip install failed."
    fi
fi

echo -e "\n================================"
echo "Diagnostics Complete. Log: $LOG_FILE"
