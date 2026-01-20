#!/bin/bash
# setup_realistic_host.sh
# Provisions mission-sim with a "Realistic" Enterprise Layout (Project0)

HOST="mission-sim"
USER="oracle"

# Layout Constants
PROJECT_ROOT="/repos/projects/project0"
LIB_DIR="$PROJECT_ROOT/libs/lib0"
SDK_DIR="/auto/sdk0"
FRAMEWORK_DIR="/opt/framework0"

REMOTE_MISSION="/home/$USER/.mission"

echo "🏭 Provisioning Realistic Factory on $HOST..."

# 1. Clean & Create Structure
echo "   Cleaning old workspaces & creating dirs..."
# We use sudo for root-level dirs if needed, but for simplicity in sim we might own them or make them in user space then move?
# Actually simpler: just make them in user space if possible or use sudo mkdir.
# The sim user 'oracle' likely has sudo passwordless or we assume we can write to /repos if we chown it.
# Let's assume we need to setup permissions first.
ssh $HOST "sudo rm -rf /repos /auto /opt/framework0"
ssh $HOST "sudo mkdir -p $PROJECT_ROOT $SDK_DIR $FRAMEWORK_DIR $REMOTE_MISSION"
ssh $HOST "sudo chown -R $USER:$USER /repos /auto /opt"

# 2. Deploy Mission Tools
echo "   Deploying Toolchain via Git..."
# Install git and python deps if missing
ssh $HOST "which git >/dev/null || (sudo apt-get update && sudo apt-get install -y git python3-venv curl)"

# Clone Mission Core
echo "   Cloning Mission Core..."
ssh $HOST "rm -rf $REMOTE_MISSION"
ssh $HOST "git clone https://github.com/andrey-stepantsov/mission-core $REMOTE_MISSION"

# Clone DDD
echo "   Cloning DDD..."
ssh $HOST "rm -rf $REMOTE_MISSION/tools/ddd"
ssh $HOST "git clone https://github.com/andrey-stepantsov/ddd $REMOTE_MISSION/tools/ddd"

# Install DDD Dependencies
echo "   Installing DDD Dependencies..."
ssh $HOST "python3 -m pip install -r $REMOTE_MISSION/tools/ddd/requirements.txt"

# 3. Create Chaos Plan
echo "   Planting 'Project0' Chaos Plan..."
# OVERRIDE: Copy local chaos.py to ensure we have the latest logic (supporting 'both' mode)
# This handles the case where the cloned repo is behind our local development.
scp .mission/tools/lib/chaos.py $HOST:$REMOTE_MISSION/tools/lib/chaos.py

# OVERRIDE: Copy local launch_tower as it might not be in the default git branch yet
scp .mission/tools/bin/launch_tower $HOST:$REMOTE_MISSION/tools/bin/launch_tower
ssh $HOST "chmod +x $REMOTE_MISSION/tools/bin/launch_tower"

ssh $HOST "cat > /tmp/chaos_plan_project0.yaml" <<EOF
root: $PROJECT_ROOT
components:
  - name: libs/lib0
    path: libs/lib0
    headers: [lib0.h]
    sources: [lib0.c]
    style: driver_c_legacy
    compile_db: both
    external_includes: ["$SDK_DIR/include"]

  - name: src/root_app
    path: src
    sources: [main.cpp]
    includes: [libs/lib0]
    external_includes: ["$FRAMEWORK_DIR/include"]
    style: app_modern_cpp
    compile_db: root

ddd_config:
  project_root: "$PROJECT_ROOT"
  targets:
    dev:
      build:
        cmd: "./mk"
      verify:
        cmd: "./mk-test"
  test_command: "./mk-test"
EOF

# 4. Generate Headers for External Deps (so critical defines exist)
echo "   Mocking External SDKs..."
ssh $HOST "mkdir -p $SDK_DIR/include $FRAMEWORK_DIR/include"
ssh $HOST "cat > $SDK_DIR/include/sdk.h" <<EOF
#ifndef SDK_H
#define SDK_H
#define SDK_VERSION 100
#define SDK_INIT() printf(\"SDK Init\\\n\")
#endif
EOF
ssh $HOST "cat > $FRAMEWORK_DIR/include/framework.h" <<EOF
#ifndef FRAMEWORK_H
#define FRAMEWORK_H
#define FW_ENABLED 1
#define FW_LOG(msg) printf(\"FW: %s\\\n\", msg)
#endif
EOF

# 5. Run Chaos Generator
echo "   Running Chaos Generator..."
ssh $HOST "python3 $REMOTE_MISSION/tools/lib/chaos.py /tmp/chaos_plan_project0.yaml"

# 6. Create Build Scripts & Config Switcher
echo "   Planting Build Scripts & Helpers..."

# lmk-test (Lib0 Verify)
# chaos.py generates test/run.sh, we link it to lmk-test at the component root
ssh $HOST "ln -sf test/run.sh $LIB_DIR/lmk-test"

# mk (Root Build)
ssh $HOST "cat > $PROJECT_ROOT/mk" <<EOF
#!/bin/bash
set -e
echo "🔨 Building Project0 (Root)..."

# 1. Compile Main
g++ -I$PROJECT_ROOT/libs/lib0 -I$FRAMEWORK_DIR/include -c $PROJECT_ROOT/src/main.cpp -o $PROJECT_ROOT/src/main.o

# 2. Link (Main + Lib0)
# We assume Lib0 is already built (or we should build it here? For now assuming 'lmk' was run or we just link existing .o)
# But ideally 'mk' should be recursive or we just manually link everything for this simple sim.
if [ -f $PROJECT_ROOT/libs/lib0/lib0.c.o ]; then
    LIB0_OBJ=$PROJECT_ROOT/libs/lib0/lib0.c.o
else
    echo "⚠️  Warning: lib0.c.o not found. Attempting to build lib0..."
    (cd $PROJECT_ROOT/libs/lib0 && ./lmk)
    LIB0_OBJ=$PROJECT_ROOT/libs/lib0/lib0.c.o
fi

g++ $PROJECT_ROOT/src/main.o \$LIB0_OBJ -o $PROJECT_ROOT/main

echo "✅ Project0 Build Success"
EOF
ssh $HOST "chmod +x $PROJECT_ROOT/mk"

# mk-test (Root Verify)
ssh $HOST "cat > $PROJECT_ROOT/mk-test" <<EOF
#!/bin/bash
set -e
echo "🧪 Testing Project0..."
$PROJECT_ROOT/main
echo "✅ All Tests Passed"
EOF
ssh $HOST "chmod +x $PROJECT_ROOT/mk-test"

# Switcher Script
ssh $HOST "cat > $PROJECT_ROOT/switch_ddd" <<EOF
#!/bin/bash
TARGET=\$1
if [ "\$TARGET" == "lib0" ]; then
    echo "🔄 Switching DDD to lib0..."
    cat > $PROJECT_ROOT/.ddd/config.json <<JSON
{
  "project_root": "$LIB_DIR",
  "targets": {
    "dev": {
      "build": { "cmd": "cd $LIB_DIR && ./lmk" },
      "verify": { "cmd": "cd $LIB_DIR && ./lmk-test" }
    }
  }
}
JSON
elif [ "\$TARGET" == "root" ]; then
    echo "🔄 Switching DDD to Root..."
    cat > $PROJECT_ROOT/.ddd/config.json <<JSON
{
  "project_root": "$PROJECT_ROOT",
  "targets": {
    "dev": {
      "build": { "cmd": "./mk" },
      "verify": { "cmd": "./mk-test" }
    }
  }
}
JSON
else
    echo "Usage: ./switch_ddd [root|lib0]"
    exit 1
fi

# Restarting Tower to pick up new config
echo "♻️  Restarting Tower..."
tmux kill-session -t mission_tower 2>/dev/null
# Re-launch using launch_tower (must be in path or absolute)
PROJECT_ROOT=$PROJECT_ROOT /home/$USER/.mission/tools/bin/launch_tower

echo "✅ Switched & Restarted."
EOF
ssh $HOST "chmod +x $PROJECT_ROOT/switch_ddd"

# 7. Clean up old daemon
echo "   Killing old daemons..."
ssh $HOST "tmux kill-session -t mission_tower 2>/dev/null || true"

echo "✨ Host Ready. Target: $PROJECT_ROOT"
