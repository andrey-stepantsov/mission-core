#!/bin/bash
# test_projector_live.sh
# Verifies "The Synapse" (Projector Live Mode) using The Matrix simulation.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MISSION_ROOT="$(dirname "$SCRIPT_DIR")"
SIM_DIR="$MISSION_ROOT/tools/simulation"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "🧪 Testing Projector Live Mode (The Synapse)..."

# 1. Reset & Launch Matrix
echo "   [1/6] Launching Matrix..."
cd "$SIM_DIR"
docker compose up -d --build

# Wait for healthy
sleep 5

# 2. Setup Host keys & DDD
echo "   [2/6] Configuring Host..."
# Key Exchange (Client -> Host)
# We regenerate client key to be sure
docker exec -u neo mission-client bash -c "mkdir -p ~/.ssh && [ -f ~/.ssh/id_rsa ] || ssh-keygen -t rsa -N '' -f ~/.ssh/id_rsa"
PUBKEY=$(docker exec -u neo mission-client cat /home/neo/.ssh/id_rsa.pub)
# Install on Host
docker exec mission-host bash -c "mkdir -p /home/oracle/.ssh && echo '$PUBKEY' >> /home/oracle/.ssh/authorized_keys && chmod 600 /home/oracle/.ssh/authorized_keys && chown -R oracle:oracle /home/oracle/.ssh"

# Start dd-daemon on Host (as oracle user)
docker exec -d -u oracle mission-host bash -c "/mission/tools/bin/dd-daemon > /tmp/ddd.log 2>&1"

# 3. Initialize Client
echo "   [3/6] Initializing Projector..."
# Ensure clean slate
docker exec -u neo mission-client bash -c "rm -rf /mission/hologram_test_suite"
docker exec -u neo mission-client bash -c "mkdir -p /mission/hologram_test_suite"

# Init
docker exec -u neo mission-client bash -c "mkdir -p /mission/hologram_test_suite/.mission"
docker exec -u neo mission-client bash -c "cd /mission/hologram_test_suite && /mission/tools/bin/projector init oracle@mission-host > /dev/null"

# 4. Start Live Mode
echo "   [4/6] Starting The Synapse..."
docker exec -d -u neo mission-client bash -c "export PYTHONUNBUFFERED=1; cd /mission/hologram_test_suite && /mission/tools/bin/projector live --auto-build > /tmp/live_test.log 2>&1"
sleep 3 # Wait for startup

# 5. Trigger Change
echo "   [5/6] Triggering Impulse..."
# We write to a file that maps to home dir to avoid permission issues
# Projector maps relative paths. Host is mapped to /mission/hologram_test_suite/file
# But wait, Projector 'pull' maps remote files locally. 'push' pushes local content to remote.
# 'init' uses the current dir as root.
# 'push' calculates remote path relative to hologram root?
# Let's check projector.py:
#   rel_path = os.path.relpath(abs_path, hologram_abs)
#   remote_path = "/" + rel_path
# Ah, it pushes to absolute path on remote corresponding to relative path in hologram!
# So hologram/home/oracle/foo -> /home/oracle/foo.
# We need to make sure the local struct exists.

# Flat structure for home dir mapping
docker exec -u neo mission-client bash -c "mkdir -p /mission/hologram_test_suite/hologram"
docker exec -u neo mission-client bash -c "cd /mission/hologram_test_suite && touch hologram/test_live_suite.txt"

sleep 10 # Wait for debounce + sync + build + radio


# 6. Verify Listen Log
echo "   [6/6] Verifying Feedback..."
# We expect "MISSION START" and "MISSION COMPLETE" in /tmp/live_test.log
LOG_CONTENT=$(docker exec mission-client cat /tmp/live_test.log)

if echo "$LOG_CONTENT" | grep -q "MISSION COMPLET"; then
    echo -e "${GREEN}PASSED${NC}: Radio signal received."
else
    echo -e "${RED}FAILED${NC}: Radio signal NOT found in client output."
    echo "--- Client Log ---"
    echo "$LOG_CONTENT"
    echo "------------------"
    
    echo "--- Host Log ---"
    docker exec mission-host cat /home/oracle/.ddd/run/build.log
    echo "----------------"
    
    exit 1
fi

exit 0
