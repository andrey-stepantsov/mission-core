#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TOOLS_ROOT="$(dirname "$SCRIPT_DIR")"
MISSION_ROOT="$(dirname "$TOOLS_ROOT")"
HOST_REPO_ROOT="$(dirname "$MISSION_ROOT")"

# 1. Credential Logic
if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    if [ -f "$HOME/.config/gcloud/application_default_credentials.json" ]; then
        export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/gcloud/application_default_credentials.json"
    elif [ -f "/tmp/auth.json" ]; then
        export GOOGLE_APPLICATION_CREDENTIALS="/tmp/auth.json"
    else
        echo "Error: No Google Credentials found."
        exit 1
    fi
fi

# 2. Defaults
export VERTEXAI_PROJECT="${VERTEXAI_PROJECT:-gen-lang-client-0140206225}"
export VERTEXAI_LOCATION="${VERTEXAI_LOCATION:-us-central1}"
IMAGE="aider-vertex"

GIT_NAME=$(git config user.name || echo "Neo")
GIT_EMAIL=$(git config user.email || echo "neo@matrix.sim")

if [ -x "$TOOLS_ROOT/bin/auto_ghost" ]; then GHOST_MOUNTS=$(cd "$HOST_REPO_ROOT" && "$TOOLS_ROOT/bin/auto_ghost" --view ghost --format docker); fi
if [ -x "$TOOLS_ROOT/bin/sync_ignore" ]; then "$TOOLS_ROOT/bin/sync_ignore" 2>/dev/null || true; fi

TTY_FLAG=""
if [ -t 0 ]; then TTY_FLAG="-t"; fi
touch .mission/.global_gitignore

printf "🐳 Launching Container (Unified Arch)...\n"

# 3. The Unified Preflight Script
# This runs INSIDE the container before the actual command.
# It sets up git, then execs whatever arguments were passed.
PREFLIGHT_SCRIPT=$(cat <<INNER_EOF
set -e
git config --global user.name "$GIT_NAME"
git config --global user.email "$GIT_EMAIL"
git config --global core.excludesfile /tmp/global_gitignore
export PATH="/mission/tools/bin:\$PATH"

# Handover to the requested command
exec "\$@"
INNER_EOF
)

DOCKER_ARGS=(
    -i $TTY_FLAG --rm
    --user "$(id -u):$(id -g)"
    -e HOME=/tmp
    --tmpfs /tmp:exec,mode=1777
    -e GIT_AUTHOR_NAME="$GIT_NAME"
    -e GIT_AUTHOR_EMAIL="$GIT_EMAIL"
    -e GIT_COMMITTER_NAME="$GIT_NAME"
    -e GIT_COMMITTER_EMAIL="$GIT_EMAIL"
    -v "$HOST_REPO_ROOT:/repo:z"
    -v "$MISSION_ROOT:/mission:z"
    -v "$GOOGLE_APPLICATION_CREDENTIALS:/tmp/auth.json:ro,z"
    -v "$MISSION_ROOT/.global_gitignore:/tmp/global_gitignore:ro,z"
    $GHOST_MOUNTS
    -e MISSION_RUNTIME=container
    -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/auth.json
    -e VERTEXAI_PROJECT="${VERTEXAI_PROJECT}"
    -e VERTEXAI_LOCATION="${VERTEXAI_LOCATION}"
    -e DIRECTOR_MODEL="${DIRECTOR_MODEL}"
    -w "/repo"
)

if [[ -z "$1" ]] || [[ "$1" == -* ]]; then
      # AIDER MODE: We explicitly pass 'aider-vertex' as the command to the preflight
      AIDER_ARGS=("aider-vertex" "--model" "vertex_ai/gemini-2.5-pro" "--no-auto-commits" "--read" "/mission/data/mission_log.md")
      AIDER_ARGS+=("$@")
      
      exec docker run --entrypoint /bin/bash "${DOCKER_ARGS[@]}" \
           "$IMAGE" -c "$PREFLIGHT_SCRIPT" -- "${AIDER_ARGS[@]}"
else
      # EXEC MODE: We pass the user command (e.g. bash) to the preflight
      # This ensures 'git config' runs even for shells.
      exec docker run --entrypoint /bin/bash "${DOCKER_ARGS[@]}" \
           "$IMAGE" -c "$PREFLIGHT_SCRIPT" -- "$@"
fi
