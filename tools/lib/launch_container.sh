#!/bin/bash
set -e

# --- 1. Context Resolution ---
HOST_REPO_ROOT=$(git rev-parse --show-toplevel)
# Resolve the tools root (Parent of this script's directory)
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TOOLS_ROOT=$(dirname "$SCRIPT_DIR")
# NEW: Resolve the Mission Root (Parent of tools)
MISSION_ROOT=$(dirname "$TOOLS_ROOT")

# --- 2. Credential Discovery ---
if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    if [ -f "$HOME/.config/gcloud/application_default_credentials.json" ]; then
        export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/gcloud/application_default_credentials.json"
    elif [ -f "/tmp/auth.json" ]; then
        export GOOGLE_APPLICATION_CREDENTIALS="/tmp/auth.json"
    else
        echo "❌ Error: No Google Credentials found."
        exit 1
    fi
fi

# --- 3. Configuration ---
export VERTEXAI_PROJECT="${VERTEXAI_PROJECT:-gen-lang-client-0140206225}"
export VERTEXAI_LOCATION="${VERTEXAI_LOCATION:-us-central1}"
IMAGE="ghcr.io/andrey-stepantsov/aider-vertex:latest"
GIT_NAME=$(git config user.name || echo "Mission Developer")
GIT_EMAIL=$(git config user.email || echo "dev@mission.core")

# --- 4. Build Docker Arguments ---
DOCKER_ARGS=(
    -it --rm
    --platform linux/amd64
    --user "$(id -u):$(id -g)"
    -e HOME=/tmp
    
    # CRITICAL FIX: Mac M1 Permission Support
    --tmpfs /tmp:exec,mode=1777

    # Git Identity
    -e GIT_AUTHOR_NAME="$GIT_NAME"
    -e GIT_AUTHOR_EMAIL="$GIT_EMAIL"
    -e GIT_COMMITTER_NAME="$GIT_NAME"
    -e GIT_COMMITTER_EMAIL="$GIT_EMAIL"

    # Mounts
    -v "$HOST_REPO_ROOT:/repo:z"
    -v "$GOOGLE_APPLICATION_CREDENTIALS:/tmp/auth.json:ro,z"
    
    # CRITICAL CHANGE: Mount the ENTIRE mission pack to /mission
    -v "$MISSION_ROOT:/mission:z"

    # Environment
    -e MISSION_RUNTIME=container
    -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/auth.json
    -e VERTEXAI_PROJECT="${VERTEXAI_PROJECT}"
    -e VERTEXAI_LOCATION="${VERTEXAI_LOCATION}"

    # Working Directory
    -w "/repo"
)

echo "🐳 Launching Container..."

# --- 5. Execution (Bifurcated Logic) ---

if [[ -z "$1" ]] || [[ "$1" == -* ]]; then
     # AGENT MODE:
     exec docker run --entrypoint aider-vertex "${DOCKER_ARGS[@]}" \
          "$IMAGE" \
          --model vertex_ai/gemini-2.5-pro \
          --restore-chat-history \
          "$@"
else
     # TOOL MODE:
     exec docker run --entrypoint "" "${DOCKER_ARGS[@]}" "$IMAGE" "$@"
fi