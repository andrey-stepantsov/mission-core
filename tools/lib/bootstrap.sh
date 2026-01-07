#!/bin/bash
set -e

# Resolve the absolute path of the tools root
# (Assumes this script is in tools/lib/)
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TOOLS_ROOT=$(dirname "$SCRIPT_DIR")

# Virtual Environment Location
# We use OS-specific venvs to allow Host and Docker to share this directory
# without binary format collisions (e.g. Darwin-arm64 vs Linux-x86_64).
OS_TYPE=$(uname -s)
ARCH_TYPE=$(uname -m)
RUNTIME=${MISSION_RUNTIME:-host}
VENV_DIR="$TOOLS_ROOT/.venv-${OS_TYPE}-${ARCH_TYPE}-${RUNTIME}"

# 1. Create Venv if missing
if [ ! -d "$VENV_DIR" ]; then
    echo "Bootstrapping..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip
fi

# 2. Install dependencies
# (Assumes requirements.txt is in tools/)
# We silence stdout (logs) but keep stderr (errors) visible.
"$VENV_DIR/bin/pip" install -r "$TOOLS_ROOT/requirements.txt" > /dev/null

# 3. Export PYTHONPATH
# This is the Critical Fix: Allow scripts to import sibling modules in lib/
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$SCRIPT_DIR"

# 4. Handover execution
exec "$VENV_DIR/bin/python3" "$@"
