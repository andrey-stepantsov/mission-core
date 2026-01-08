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

DOCKER_ARGS=(
    -it --rm
    --platform linux/amd64
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
    -e MISSION_RUNTIME=container
    -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/auth.json
    -e VERTEXAI_PROJECT="${VERTEXAI_PROJECT}"
    -e VERTEXAI_LOCATION="${VERTEXAI_LOCATION}"
    -w "/repo"
)

if [ -n "$MISSION_RULES_FILE" ]; then
    DOCKER_ARGS+=(-v "$MISSION_RULES_FILE:/etc/mission_rules.md:ro,z")
fi

echo "🐳 Launching Container ($IMAGE)..."

PREFLIGHT_SCRIPT=$(cat <<INNER_EOF
set -e
git config --global user.name "$GIT_NAME"
git config --global user.email "$GIT_EMAIL"
git config --global core.excludesfile /tmp/global_gitignore

# --- FIX: EXPOSE LOCAL TOOLS ---
# Add the mission pack's bin directory to PATH so local scripts (like the real 'weave') work.
export PATH="/mission/tools/bin:\$PATH"

# Check if 'weave' is found now
if ! command -v weave &> /dev/null; then
    # Fallback check: Is it installed as 'ctx-tool'?
    if command -v ctx-tool &> /dev/null; then
        echo "⚠️  'weave' not found, but 'ctx-tool' detected. Aliasing..." >&2
        mkdir -p /tmp/bin
        ln -sf \$(which ctx-tool) /tmp/bin/weave
        export PATH="/tmp/bin:\$PATH"
    fi
fi

exec aider-vertex "\$@"
INNER_EOF
)

if [[ -z "$1" ]] || [[ "$1" == -* ]]; then
      AIDER_ARGS=("--model" "vertex_ai/gemini-2.5-pro" "--restore-chat-history")
      
      if [ -n "$MISSION_RULES_FILE" ]; then
          AIDER_ARGS+=("--read" "/etc/mission_rules.md")
      fi
      AIDER_ARGS+=("$@")
      
      exec docker run --entrypoint /bin/bash "${DOCKER_ARGS[@]}" \
           "$IMAGE" -c "$PREFLIGHT_SCRIPT" -- "${AIDER_ARGS[@]}"
else
      exec docker run --entrypoint "" "${DOCKER_ARGS[@]}" "$IMAGE" "$@"
fi
