#!/bin/bash
# Infrastructure Verification Suite (Robust)

# Resolve Paths
TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MISSION_ROOT="$(dirname "$TEST_DIR")"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "🏥 Mission Infrastructure Health Check"
echo "======================================"

EXIT_CODE=0

# --- 0. Infrastructure Check ---
echo -n "[Base] Verifying Docker Environment... "
if bash "$TEST_DIR/test_docker_build.sh" > /dev/null 2>&1; then
    echo -e "${GREEN}PASSED${NC}"
else
    echo -e "${RED}FAILED${NC} (Check Logs)"
    # bash "$TEST_DIR/test_docker_build.sh" # Uncomment for debug
    EXIT_CODE=1
fi

# --- 1. Host Radio ---
echo -n "[Host] Testing Radio Logic... "
if python3 "$TEST_DIR/test_radio.py" > /dev/null 2>&1; then
    echo -e "${GREEN}PASSED${NC}"
else
    echo -e "${RED}FAILED${NC}"
    python3 "$TEST_DIR/test_radio.py"
    EXIT_CODE=1
fi

# --- 2. Container Radio ---
echo -n "[Container] Testing Radio Logic (inside Docker)... "
TOOLSMITH="$MISSION_ROOT/tools/bin/toolsmith_local"
if "$TOOLSMITH" bash -c "python3 /mission/tests/test_radio.py" > /dev/null 2>&1; then
     echo -e "${GREEN}PASSED${NC}"
else
    echo -e "${RED}FAILED${NC}"
    EXIT_CODE=1
fi

# --- 3. Director Startup ---
echo -n "[Director] Testing Startup Latency... "
DIRECTOR="$MISSION_ROOT/tools/bin/director"
START=$(date +%s%N)
if "$DIRECTOR" --help > /dev/null 2>&1; then
    END=$(date +%s%N)
    DIFF=$(( ($END - $START) / 1000000 ))
    if [ $DIFF -lt 2500 ]; then
         echo -e "${GREEN}PASSED${NC} (${DIFF}ms)"
    else
         echo -e "${RED}SLOW${NC} (${DIFF}ms)"
    fi
else
    echo -e "${RED}FAILED${NC}"
    EXIT_CODE=1
fi

# --- 4. Swarm Integration ---
echo -n "[Swarm] Testing Agent Integration... "
if python3 "$TEST_DIR/test_integration_chat.py" > /dev/null 2>&1; then
     echo -e "${GREEN}PASSED${NC}"
else
     echo -e "${RED}FAILED${NC}"
     python3 "$TEST_DIR/test_integration_chat.py"
     EXIT_CODE=1
fi

# --- 5. Complex Scenario (The New Test) ---
echo -n "[Scenario] Testing Configuration Lifecycle... "
if python3 "$TEST_DIR/test_scenario_config_flow.py" > /dev/null 2>&1; then
     echo -e "${GREEN}PASSED${NC}"
else
     echo -e "${RED}FAILED${NC}"
     # Re-run to show output
     python3 "$TEST_DIR/test_scenario_config_flow.py"
     EXIT_CODE=1
fi

echo "======================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "Result: ${GREEN}SYSTEM HEALTHY${NC}"
else
    echo -e "Result: ${RED}SYSTEM UNSTABLE${NC}"
fi
exit $EXIT_CODE
