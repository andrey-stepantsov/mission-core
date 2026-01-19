#!/bin/bash
set -e

# This runs on the HOST container to initialize the environment
# It simulates the "Legacy Repo"

USER="mission"
REPO_DIR="/home/$USER/legacy-repo"
TOOLS_DIR="/mission/tools" # Mounted via volume

echo "🔧 Initializing Chaos Repo in $REPO_DIR..."

if [ ! -d "$REPO_DIR" ]; then
    mkdir -p "$REPO_DIR"
    chown $USER:$USER "$REPO_DIR"

    # Install Python dependency for chaos.py
    pip3 install pyyaml > /dev/null 2>&1

    # Create a plan for chaos
    # We create a simple plan that generates a few components with dependencies
    cat <<EOF > /tmp/chaos_plan.yaml
root: $REPO_DIR
components:
  - name: src/core_engine
    path: src/core
    headers: [engine.h]
    sources: [engine.c]
    style: driver_c_legacy

  - name: src/legacy_utils
    path: lib/utils
    headers: [utils.h]
    sources: [utils.c]
    style: driver_c_legacy

  - name: src/main_app
    path: src/app
    sources: [main.c]
    includes: [src/core, lib/utils]
    headers: []
    style: app_modern_cpp
EOF

    # Run Chaos Generator
    # We access the tool from the mounted /mission directory
    # Note: We run as root during setup, but target user dir
    echo "   Running Chaos Generator..."
    python3 /mission/tools/lib/chaos.py /tmp/chaos_plan.yaml
    
    # Fix permissions
    chown -R $USER:$USER "$REPO_DIR"
    
    echo "✅ Chaos Repo Generated (Rich Structure)."
else
    echo "⚡ Chaos Repo already exists."
fi
