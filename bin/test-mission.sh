#!/bin/bash
set -e

# --- 1. Path Resolution ---
# Resolve the Mission Pack Root (Where this script lives -> up one level)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MISSION_PACK_ROOT="$(dirname "$SCRIPT_DIR")"

# Hardcoded paths for the Host-side simulation (Matches gen_srl_mock.py)
HOST_MOCK_REPO="/repos/mock-repo"
HOST_SDK_HEADERS="/repos/mock-out-of-tree"

# --- 2. Credential Auto-Detection ---
if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    if [ -f "/tmp/auth.json" ]; then
        echo "🔑 Found credentials at /tmp/auth.json"
        export GOOGLE_APPLICATION_CREDENTIALS="/tmp/auth.json"
    else
        echo "❌ Error: GOOGLE_APPLICATION_CREDENTIALS not set and /tmp/auth.json not found."
        exit 1
    fi
fi

GIT_NAME=$(git config user.name || echo "Test User")
GIT_EMAIL=$(git config user.email || echo "test@example.com")

# Defaults
: "${VERTEXAI_PROJECT:=gen-lang-client-0140206225}"
: "${VERTEXAI_LOCATION:=us-central1}"
IMAGE="ghcr.io/andrey-stepantsov/aider-vertex:latest"

# --- 3. Safety Checks ---
if [ ! -d "$HOST_MOCK_REPO" ]; then
    echo "❌ Error: Mock repo not found at $HOST_MOCK_REPO"
    echo "   Did you run 'devbox shell' and 'gen-mock'?"
    exit 1
fi

# --- 4. Construct Docker Arguments ---
DOCKER_ARGS=(
  -it --rm
  --platform linux/amd64
  
  # Override default entrypoint (aider) so we can run setup scripts
  --entrypoint /bin/bash
  
  # Run as Host User (Crucial for sharing files with Host Daemons)
  --user "$(id -u):$(id -g)"
  
  # Redirect Home to /tmp (Since we are stateless)
  -e HOME=/tmp

  # --- GIT IDENTITY (Pass Host Credentials) ---
  -e GIT_AUTHOR_NAME="$GIT_NAME"
  -e GIT_AUTHOR_EMAIL="$GIT_EMAIL"
  -e GIT_COMMITTER_NAME="$GIT_NAME"
  -e GIT_COMMITTER_EMAIL="$GIT_EMAIL"
  
  # --- MOUNTS ---
  # A. The Mission Pack (The Tool we are testing)
  -v "${MISSION_PACK_ROOT}:/mission-pack:ro,z"
  
  # B. The Mock Repo (The Target)
  -v "${HOST_MOCK_REPO}:${HOST_MOCK_REPO}:z"
  
  # C. The External Headers (For SDK testing)
  -v "${HOST_SDK_HEADERS}:${HOST_SDK_HEADERS}:ro,z"
  
  # D. Credentials
  -v "$GOOGLE_APPLICATION_CREDENTIALS:/tmp/auth.json:ro,z"
  
  # --- ENV VARS ---
  -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/auth.json
  -e VERTEXAI_PROJECT="${VERTEXAI_PROJECT}"
  -e VERTEXAI_LOCATION="${VERTEXAI_LOCATION}"
  
  # Set Working Directory to the App Root inside the Mock
  -w "${HOST_MOCK_REPO}/srl-x/srl-repo"
)

# --- 5. Global Gitignore (Optional) ---
HOST_IGNORE=""
if [ -f "${HOME}/.gitignore" ]; then HOST_IGNORE="${HOME}/.gitignore";
elif [ -f "${HOME}/.gitignore_global" ]; then HOST_IGNORE="${HOME}/.gitignore_global"; fi

if [ -n "$HOST_IGNORE" ]; then
    echo "📄 Mounting global ignore: $HOST_IGNORE"
    DOCKER_ARGS+=(-v "${HOST_IGNORE}:/tmp/global.gitignore:ro,z")
    GIT_IGNORE_CMD="git config --global core.excludesfile /tmp/global.gitignore"
else
    GIT_IGNORE_CMD="true"
fi

echo "🚀 Launching AiderUser (Test Subject)..."
echo "   Mission Pack: /mission-pack"
echo "   Target:       ${HOST_MOCK_REPO}/srl-x/srl-repo"

# --- 6. Launch with Setup Logic ---
echo "⏳ Starting container..."
docker run "${DOCKER_ARGS[@]}" \
  "$IMAGE" -c "
    echo '🔍 Checking environment...'
    export PATH=\$PATH:/bin:/usr/bin
    
    # 1. Setup Git Safety & Disable Hooks
    echo '⚙️  Configuring Git...'
    git config --global --add safe.directory ${HOST_MOCK_REPO}
    git config --global core.hooksPath /dev/null  # <-- Disables hooks inside container
    $GIT_IGNORE_CMD
    
    # 2. Locate Aider Binary
    if command -v aider-vertex &> /dev/null; then
        AIDER_BIN='aider-vertex'
    elif [ -f /bin/aider-vertex ]; then
        AIDER_BIN='/bin/aider-vertex'
    else
        echo '❌ Error: Could not find aider-vertex binary!'
        echo 'PATH is: \$PATH'
        ls -l /bin/aider*
        exit 1
    fi
    
    echo '🚀 Starting Aider...'
    
    # 3. Run Aider (INTERACTIVE)
    # We do NOT use 'exec' here so we can catch the exit
    \$AIDER_BIN --model vertex_ai/gemini-2.5-pro
    
    # 4. Drop to Shell on Exit
    echo ''
    echo '🛑 Aider session ended.'
    echo '🐚 Dropping into container shell for inspection...'
    echo '   (Type exit to leave container completely)'
    exec /bin/bash
  "
