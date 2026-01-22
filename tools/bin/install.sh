#!/bin/bash
set -e

# Mission Pack Bootstrap Script
# Usage:
#   Remote Mode: curl ... | bash -s -- remote <user@host> <remote_root> [--mission-root <path>]
#   Local Mode:  curl ... | bash -s -- local

MODE="$1"
shift

if [ -z "$MODE" ]; then
    echo "Usage: install.sh <mode> [args]"
    echo "Modes:"
    echo "  remote <user@host> <remote_root> [--mission-root <path>]"
    echo "  local"
    exit 1
fi

# Check Prerequisites
if ! command -v tmux &> /dev/null; then
    echo "❌ Error: 'tmux' is required for Mission Control (Radio/Tower)."
    echo "   Please install tmux (e.g., 'brew install tmux' or 'apt-get install tmux') and try again."
    exit 1
fi

MISSION_REPO="https://github.com/andrey-stepantsov/mission-core.git"
MISSION_DIR=".mission"

MISSION_BRANCH="${MISSION_BRANCH:-main}"

# 1. Acquire Mission Pack
if [ ! -d "$MISSION_DIR" ]; then
    echo "🔮 Summoning Mission Pack ($MISSION_BRANCH)..."
    # Try submodule first (suppress error if not in git repo), then clone
    (git submodule add -b "$MISSION_BRANCH" "$MISSION_REPO" "$MISSION_DIR" 2>/dev/null) || git clone -b "$MISSION_BRANCH" "$MISSION_REPO" "$MISSION_DIR"
    (cd "$MISSION_DIR" && git submodule update --init --recursive)
else
    echo "🔮 Mission Pack already present."
fi


# 1.1. Deploy Components
DEPLOY_TOOLS_DIR="$MISSION_DIR/tools"

ensure_repo() {
    local name="$1"
    local url="$2"
    local path="$3"
    
    # 1. Git Repo (File or Dir)
    if [ -e "$path/.git" ]; then
        echo "✅ $name (Git) is present."
        if [ -d "$path/.git" ]; then
             # Only update standard repos, submodules are managed by parent usually, 
             # but we can try pulling if we want latest. 
             # For now, just logging content.
             echo "   Updating..."
             (cd "$path" && git pull --quiet)
        fi
        
    # 2. Directory exists but empty (clone)
    elif [ -d "$path" ] && [ -z "$(ls -A "$path")" ]; then
        echo "📦 Cloning $name..."
        git clone --quiet "$url" "$path"
    elif [ ! -d "$path" ]; then
        echo "📦 Cloning $name..."
        git clone --quiet "$url" "$path"
    else
        echo "⚠️  $path exists but is not empty/git repo. Skipping."
    fi
}

ensure_repo "DDD" "https://github.com/andrey-stepantsov/ddd" "$DEPLOY_TOOLS_DIR/ddd"

# 1.2. Bootstrap Config
if [ ! -f ".ddd/config.yaml" ] && [ ! -f "ddd.config" ]; then
    echo "⚙️  Generating initial .ddd/config.yaml..."
    mkdir -p .ddd
    cat > .ddd/config.yaml <<EOF
version: "1.0"
mode: "dummy"
commands:
  build: "echo 'Dummy Build Success'"
  verify: "echo 'Dummy Verify Success'"
EOF
fi

# Ensure tools are executable (ignore broken symlinks/errors)
chmod +x "$MISSION_DIR/tools/bin/"* 2>/dev/null || true

# 2. Mode Execution
if [ "$MODE" == "remote" ]; then
    HOST_TARGET="$1"
    REMOTE_ROOT="$2"
    shift 2
    
    if [ -z "$HOST_TARGET" ] || [ -z "$REMOTE_ROOT" ]; then
        echo "Error: Remote mode requires user@host and remote_root"
        exit 1
    fi
    
    echo "🚀 Initializing Remote Brain..."
    "$MISSION_DIR/tools/bin/projector" init "$HOST_TARGET" --remote-root "$REMOTE_ROOT" "$@"

elif [ "$MODE" == "local" ]; then
    echo "🧠 Initializing Local Brain (Standardizing on Projector)..."
    
    # Use projector to initialize local mode
    # host_target='local' is just a label here
    "./$MISSION_DIR/tools/bin/projector" init local --transport local --remote-root "$(pwd)"
    
    echo "✅ Local Environment Configured via Projector."
    echo "   Run: ./.mission/tools/bin/projector context <file> \"Task\""

else
    echo "Error: Unknown mode '$MODE'"
    exit 1
fi
