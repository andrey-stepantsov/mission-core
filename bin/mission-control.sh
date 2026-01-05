#!/bin/bash
set -e

# --- Configuration ---
SESSION="srl-mission"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Hardcoded paths
MOCK_ROOT_DIR="/repos/mock-repo/srl-x/srl-repo"
MOCK_SDK_DIR="/repos/mock-repo/srl-x/srl-repo/asic/sdk1"

# --- Pre-Flight Checks ---
if ! command -v dd-daemon &> /dev/null; then
    echo "❌ Error: 'dd-daemon' not found."
    echo "👉 Please run 'devbox shell' first."
    exit 1
fi

if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "⚠️  Session '$SESSION' already exists. Attaching..."
    exec tmux attach -t "$SESSION"
fi

echo "🚀 Initializing Mission Control Center..."

# --- Build the 3-Column Layout ---

# 1. Start Session (Pane 0: Editor / Left Column)
#    Window 0 created. Index: 0.0
cd "$REPO_ROOT"
tmux new-session -d -s "$SESSION" -n "mission-control"

# 2. Create the Right Side (Pane 1)
#    Split Pane 0.0 horizontally. New pane takes 66% of width.
#    Result: [Editor 34%] | [New Pane 66%]
tmux split-window -h -t "$SESSION:0.0" -l 66%

# 3. Create the Middle Column (Pane 1 becomes Middle, Pane 2 becomes Right)
#    Split Pane 0.1 (the large right side) in half.
#    Result: [Editor] | [Tester] | [Right Side]
tmux split-window -h -t "$SESSION:0.1" -l 50%

# 4. Split the Right Column (Pane 2) Vertically for Logs
#    Split Pane 0.2 (the far right side) top/bottom.
#    Result: [Editor] | [Tester] | [Root Log]
#                                  [SDK Log ]
tmux split-window -v -t "$SESSION:0.2"


# --- Send Commands (Using explicit Window.Pane targets) ---

# Pane 0 (Left): Editor
tmux send-keys -t "$SESSION:0.0" "./bin/edit-pack.sh" C-m

# Pane 1 (Middle): Tester
tmux send-keys -t "$SESSION:0.1" "./bin/test-mission.sh" C-m

# Pane 2 (Top-Right): Root Daemon
tmux send-keys -t "$SESSION:0.2" "cd $MOCK_ROOT_DIR && echo 'Use: start-daemon-root' && dd-daemon" C-m

# Pane 3 (Bottom-Right): SDK Daemon
tmux send-keys -t "$SESSION:0.3" "cd $MOCK_SDK_DIR && echo 'Use: start-daemon-sdk' && dd-daemon" C-m

# --- Attach ---
tmux select-pane -t "$SESSION:0.0"
echo "✅ Session ready. Attaching..."
exec tmux attach -t "$SESSION"
