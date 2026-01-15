#!/bin/bash
# Infrastructure Verification Suite (Robust)

# 1. Resolve Paths Dynamicallly
# Get directory of this script (e.g., .../chaos/.mission/tests)
TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Get Mission Root (e.g., .../chaos/.mission)
MISSION_ROOT="$(dirname "$TEST_DIR")"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "🏥 Mission Infrastructure Health Check"
echo "======================================"

EXIT_CODE=0

# --- Test 1: Host-Side Radio Logic ---
echo -n "[Host] Testing Radio Logic... "
if python3 "$TEST_DIR/test_radio.py" > /dev/null 2>&1; then
    echo -e "${GREEN}PASSED${NC}"
else
    echo -e "${RED}FAILED${NC}"
    # Re-run for debug
    python3 "$TEST_DIR/test_radio.py"
    EXIT_CODE=1
fi

# --- Test 2: Container-Side Radio Logic ---
echo -n "[Container] Testing Radio Logic (inside Docker)... "
# We assume the container mounts $MISSION_ROOT to /mission
TOOLSMITH="$MISSION_ROOT/tools/bin/toolsmith_local"

if "$TOOLSMITH" bash -c "python3 /mission/tests/test_radio.py" > /dev/null 2>&1; then
     echo -e "${GREEN}PASSED${NC}"
else
    echo -e "${RED}FAILED${NC}"
    echo "Command: $TOOLSMITH bash -c 'python3 /mission/tests/test_radio.py'"
    EXIT_CODE=1
fi

# --- Test 3: Director Startup Latency ---
echo -n "[Director] Testing Startup Latency... "
DIRECTOR="$MISSION_ROOT/tools/bin/director"
START=$(date +%s%N)
# Check exit code to ensure it actually ran
if "$DIRECTOR" --help > /dev/null 2>&1; then
    END=$(date +%s%N)
    # Calculate ms (Linux/Mac compatible math often tricky, keeping it simple)
    DIFF=$(( ($END - $START) / 1000000 ))
    
    if [ $DIFF -lt 2500 ]; then
         echo -e "${GREEN}PASSED${NC} (${DIFF}ms)"
    else
         echo -e "${RED}SLOW${NC} (${DIFF}ms)"
    fi
else
    echo -e "${RED}FAILED${NC} (Binary error)"
    EXIT_CODE=1
fi

# --- Test 4: Swarm Integration (AI Chat) ---
echo -n "[Swarm] Testing Agent Integration... "
if python3 "$TEST_DIR/test_integration_chat.py" > /dev/null 2>&1; then
     echo -e "${GREEN}PASSED${NC}"
else
     echo -e "${RED}FAILED${NC}"
     python3 "$TEST_DIR/test_integration_chat.py"
     EXIT_CODE=1
fi

echo "======================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "Result: ${GREEN}SYSTEM HEALTHY${NC}"
else
    echo -e "Result: ${RED}SYSTEM UNSTABLE${NC}"
fi
exit $EXIT_CODE
