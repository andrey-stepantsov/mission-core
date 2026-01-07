#!/bin/bash
set -e

# Resolve the absolute path of the tools root
# (Assumes this script is in tools/lib/)
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TOOLS_ROOT=$(dirname "$SCRIPT_DIR")

# Virtual Environment Location
VENV_DIR="$TOOLS_ROOT/.venv"

# 1. Create Venv if missing
if [ ! -d "$VENV_DIR" ]; then
    echo "Bootstrapping..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip
fi

# 2. Install dependencies
# (Assumes requirements.txt is in tools/)
"$VENV_DIR/bin/pip" install -r "$TOOLS_ROOT/requirements.txt" > /dev/null 2>&1

# 3. Export PYTHONPATH
# This is the Critical Fix: Allow scripts to import sibling modules in lib/
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$SCRIPT_DIR"

# 4. Handover execution
exec "$VENV_DIR/bin/python3" "$@"
