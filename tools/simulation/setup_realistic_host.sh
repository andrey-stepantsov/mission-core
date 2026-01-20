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
echo "   Deploying Toolchain..."
rsync -az --exclude '.git' .mission/ "$HOST:$REMOTE_MISSION/"

# 3. Create Chaos Plan
echo "   Planting 'Project0' Chaos Plan..."
ssh $HOST "cat > /tmp/chaos_plan_project0.yaml" <<EOF
root: $PROJECT_ROOT
components:
  - name: libs/lib0
    path: libs/lib0
    headers: [lib0.h]
    sources: [lib0.c]
    style: driver_c_legacy
    compile_db: local
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
  build_command: "./mk"
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
echo "🔨 Building Project0 (Root)..."
# Simulate build by running the commands in compile_commands.json? Or just successfully compiling main?
# For sim, let's just re-run the compile commands manually or rely on chaos generated 'lmk' equivalents if they existed.
# Chaos generates simple build scripts? It generates 'lmk' in components.
# Let's make 'mk' wrap the compilation of src.
g++ -I$PROJECT_ROOT/libs/lib0 -I$FRAMEWORK_DIR/include -c $PROJECT_ROOT/src/main.cpp -o $PROJECT_ROOT/src/main.o
echo "✅ Project0 Build Success"
EOF
ssh $HOST "chmod +x $PROJECT_ROOT/mk"

# mk-test (Root Verify)
ssh $HOST "cat > $PROJECT_ROOT/mk-test" <<EOF
#!/bin/bash
echo "🧪 Testing Project0..."
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
  "build_command": "./lmk",
  "test_command": "./test/run.sh"
}
JSON
elif [ "\$TARGET" == "root" ]; then
    echo "🔄 Switching DDD to Root..."
    cat > $PROJECT_ROOT/.ddd/config.json <<JSON
{
  "project_root": "$PROJECT_ROOT",
  "build_command": "./mk",
  "test_command": "./mk-test"
}
JSON
else
    echo "Usage: ./switch_ddd [root|lib0]"
    exit 1
fi
echo "✅ Switched."
EOF
ssh $HOST "chmod +x $PROJECT_ROOT/switch_ddd"

# 7. Clean up old daemon
echo "   Killing old daemons..."
ssh $HOST "tmux kill-session -t mission_tower 2>/dev/null || true"

echo "✨ Host Ready. Target: $PROJECT_ROOT"
