#!/bin/bash
set -e

# --- 1. Path Resolution ---
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MISSION_PACK_ROOT="$(dirname "$SCRIPT_DIR")"

# We still mount the Mock Repo so the Developer can "see" what they are controlling
HOST_MOCK_REPO="/repos/mock-repo"

# --- 2. Credential Auto-Detection ---
if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    if [ -f "/tmp/auth.json" ]; then
        echo "🔑 Found credentials at /tmp/auth.json"
        export GOOGLE_APPLICATION_CREDENTIALS="/tmp/auth.json"
    else
        echo "❌ Error: GOOGLE_APPLICATION_CREDENTIALS not set."
        exit 1
    fi
fi

# Defaults
: "${VERTEXAI_PROJECT:=gen-lang-client-0140206225}"
: "${VERTEXAI_LOCATION:=us-central1}"
IMAGE="ghcr.io/andrey-stepantsov/aider-vertex:latest"

# --- 3. Construct Docker Arguments ---
DOCKER_ARGS=(
  -it --rm
  --platform linux/amd64
  --entrypoint /bin/bash
  --user "$(id -u):$(id -g)"
  -e HOME=/tmp
  
  # --- MOUNTS ---
  # A. The Mission Pack (RW) - This is what we are editing!
  -v "${MISSION_PACK_ROOT}:/mission-pack:z"
  
  # B. The Mock Repo (RW) - Mounted so we can verify our mocks/configs
  -v "${HOST_MOCK_REPO}:${HOST_MOCK_REPO}:z"
  
  # C. Credentials
  -v "$GOOGLE_APPLICATION_CREDENTIALS:/tmp/auth.json:ro,z"
  
  # --- ENV VARS ---
  -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/auth.json
  -e VERTEXAI_PROJECT="${VERTEXAI_PROJECT}"
  -e VERTEXAI_LOCATION="${VERTEXAI_LOCATION}"
  
  # CRITICAL: Start in the Mission Pack directory
  -w "/mission-pack"
)

# --- 4. Global Gitignore ---
HOST_IGNORE=""
if [ -f "${HOME}/.gitignore" ]; then HOST_IGNORE="${HOME}/.gitignore"; fi
if [ -n "$HOST_IGNORE" ]; then
    DOCKER_ARGS+=(-v "${HOST_IGNORE}:/tmp/global.gitignore:ro,z")
    GIT_IGNORE_CMD="git config --global core.excludesfile /tmp/global.gitignore"
else
    GIT_IGNORE_CMD="true"
fi

echo "🧠 Launching AiderDev (The Architect)..."
echo "   Editing: /mission-pack"

# --- 5. Launch ---
docker run "${DOCKER_ARGS[@]}" \
  "$IMAGE" -c "
    export PATH=\$PATH:/bin:/usr/bin
    
    # 1. Setup Git Safety
    git config --global --add safe.directory /mission-pack
    git config --global --add safe.directory ${HOST_MOCK_REPO}
    git config --global core.hooksPath /dev/null
    $GIT_IGNORE_CMD

    # 2. Find Aider
    if command -v aider-vertex &> /dev/null; then AIDER_BIN='aider-vertex';
    elif [ -f /bin/aider-vertex ]; then AIDER_BIN='/bin/aider-vertex';
    else echo '❌ Aider binary not found'; exit 1; fi
    
    echo '🚀 Starting Mission Developer...'
    
    # 3. Run Aider
    # Note: We do NOT provide a --message here, so it opens ready for your command
    \$AIDER_BIN --model vertex_ai/gemini-2.5-pro
    
    echo '🛑 Session ended.'
    exec /bin/bash
  "
