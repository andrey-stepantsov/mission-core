#!/bin/bash
# Test: Docker Build & Environment Verification
# Strict verification of the mission-core image.

set -e

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MISSION_ROOT="$(dirname "$TEST_DIR")"
REPO_ROOT="$(dirname "$MISSION_ROOT")"

# --- Bootstrap Environment for Shared Script ---
# We need to mimic the vars set in 'up'
ENV_FILE="$REPO_ROOT/.env"
if [ -f "$ENV_FILE" ]; then export $(grep -v '^#' "$ENV_FILE" | xargs); fi

UPSTREAM_REPO="${MISSION_UPSTREAM_REPO:-github:andrey-stepantsov/aider-vertex#docker}"
BASE_IMG="aider-vertex:latest"

# Source Bootstrap Logic
if [ -f "$MISSION_ROOT/tools/lib/image_bootstrap.sh" ]; then
    source "$MISSION_ROOT/tools/lib/image_bootstrap.sh"
    echo "🏗️ Checking Base Image Status..."
    ensure_base_image
else
    echo "⚠️ Cannot find bootstrap library. Skipping base image check."
fi

IMG_NAME="mission-core:latest"

echo "📍 Debug Paths:"
echo "   REPO_ROOT: $REPO_ROOT"
echo "   MISSION_ROOT: $MISSION_ROOT"
echo "   Dockerfile: $MISSION_ROOT/tools/Dockerfile"

echo "🧪 Starting Docker Verification..."

# 1. Build Image
echo "   [1/3] Building Image ($IMG_NAME)..."
if docker build -t "$IMG_NAME" -f "$MISSION_ROOT/tools/Dockerfile" "$MISSION_ROOT/tools"; then
    echo "   ✅ Build Successful"
else
    echo "   ❌ Build Failed"
    exit 1
fi

# 2. Verify Python Virtual Env
echo "   [2/3] Verifying Virtual Environment..."
# We check if 'python3' resolves to the venv version
# Note: --entrypoint /bin/bash is needed because base image has aider entrypoint
PYTHON_PATH=$(docker run --rm --entrypoint /bin/bash "$IMG_NAME" -c "which python3")
if [[ "$PYTHON_PATH" == *"/mission/.venv/bin/python3"* ]]; then
    echo "   ✅ Python Path Correct: $PYTHON_PATH"
else
    echo "   ❌ Python Path Incorrect: $PYTHON_PATH"
    exit 1
fi

# 3. Verify Dependencies (PyYAML)
echo "   [3/3] Verifying Installed Dependencies..."
# We try to import yaml (PyYAML) which is in requirements.txt but NOT in aider-vertex
if docker run --rm --entrypoint /bin/bash "$IMG_NAME" -c "python3 -c \"import yaml; print('PyYAML Version:', yaml.__version__)\""; then
    echo "   ✅ Dependencies Loaded Successfully"
else
    echo "   ❌ Dependency Check Failed (Could not import yaml)"
    exit 1
fi

echo "🎉 All Checks Passed. 'mission-core:latest' is ready."
