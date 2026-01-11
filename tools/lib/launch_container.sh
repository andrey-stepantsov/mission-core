#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TOOLS_ROOT="$(dirname "$SCRIPT_DIR")"
MISSION_ROOT="$(dirname "$TOOLS_ROOT")"
HOST_REPO_ROOT="$(dirname "$MISSION_ROOT")"

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

export VERTEXAI_PROJECT="${VERTEXAI_PROJECT:-gen-lang-client-0140206225}"
export VERTEXAI_LOCATION="${VERTEXAI_LOCATION:-us-central1}"
IMAGE="ghcr.io/andrey-stepantsov/aider-vertex:v1.2.1"

GIT_NAME=$(git config user.name || echo "Mission Developer")
GIT_EMAIL=$(git config user.email || echo "dev@mission.core")

# --- AUTO-GHOST ---
# Only print if we are in a TTY to avoid polluting pipe output
if [ -t 0 ]; then
    echo "🔍 Scanning for external dependencies (Auto-Ghost)..."
fi
GHOST_MOUNTS=$("$TOOLS_ROOT/bin/auto_ghost")

if [ -t 0 ]; then
    if [ -n "$GHOST_MOUNTS" ]; then
        echo "   Ghost Mounts: $GHOST_MOUNTS"
    else
        echo "   Ghost Mounts: None"
    fi
fi

# --- SYNC IGNORE ---
"$TOOLS_ROOT/bin/sync_ignore" 2>/dev/null || true

# --- TTY DETECTION ---
# Only request a TTY (-t) if input is actually a terminal.
# Always keep -i (interactive) to allow piping stdin.
TTY_FLAG=""
if [ -t 0 ]; then
    TTY_FLAG="-t"
fi

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
    -w "/repo"
)

if [ -n "$MISSION_RULES_FILE" ]; then
    DOCKER_ARGS+=(-v "$MISSION_RULES_FILE:/etc/mission_rules.md:ro,z")
fi

if [ -t 0 ]; then
    echo "🐳 Launching Container ($IMAGE)..."
fi

PREFLIGHT_SCRIPT=$(cat <<INNER_EOF
set -e
git config --global user.name "$GIT_NAME"
git config --global user.email "$GIT_EMAIL"
git config --global core.excludesfile /tmp/global_gitignore

export PATH="/mission/tools/bin:\$PATH"
exec aider-vertex "\$@"
INNER_EOF
)

if [[ -z "$1" ]] || [[ "$1" == -* ]]; then
      # AIDER MODE
      AIDER_ARGS=("--model" "vertex_ai/gemini-2.5-pro" "--restore-chat-history")
      if [ -n "$MISSION_RULES_FILE" ]; then
          AIDER_ARGS+=("--read" "/etc/mission_rules.md")
      fi
      AIDER_ARGS+=("$@")
      
      exec docker run --entrypoint /bin/bash "${DOCKER_ARGS[@]}" \
           "$IMAGE" -c "$PREFLIGHT_SCRIPT" -- "${AIDER_ARGS[@]}"
else
      # SHELL/EXEC MODE
      exec docker run --entrypoint "" "${DOCKER_ARGS[@]}" "$IMAGE" "$@"
fi
