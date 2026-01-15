#!/bin/bash
# Infrastructure Verification Suite

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "🏥 Mission Infrastructure Health Check"
echo "======================================"

EXIT_CODE=0

# 1. Host-Side Radio Test
echo -n "[Host] Testing Radio Logic... "
if python3 .mission/tests/test_radio.py > /dev/null 2>&1; then
    echo -e "${GREEN}PASSED${NC}"
else
    echo -e "${RED}FAILED${NC}"
    python3 .mission/tests/test_radio.py
    EXIT_CODE=1
fi

# 2. Container-Side Radio Test (via Local Smith Wrapper)
# We use the wrapper to ensure the container mount logic works
echo -n "[Container] Testing Radio Logic (inside Docker)... "
if ./.mission/tools/bin/toolsmith_local bash -c "python3 /mission/tests/test_radio.py" > /dev/null 2>&1; then
     echo -e "${GREEN}PASSED${NC}"
else
    echo -e "${RED}FAILED${NC}"
    # Re-run with output for debug
    ./.mission/tools/bin/toolsmith_local bash -c "python3 /mission/tests/test_radio.py"
    EXIT_CODE=1
fi

# 3. Director Startup Test (Dry Run)
echo -n "[Director] Testing Startup Latency... "
START=$(date +%s%N)
./.mission/tools/bin/director --help > /dev/null 2>&1
END=$(date +%s%N)
DIFF=$(( ($END - $START) / 1000000 ))

if [ $DIFF -lt 2000 ]; then
     echo -e "${GREEN}PASSED${NC} (${DIFF}ms)"
else
     echo -e "${RED}SLOW${NC} (${DIFF}ms - Should be < 2000ms)"
     # Not a hard failure, just a warning
fi

echo "======================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "Result: ${GREEN}SYSTEM HEALTHY${NC}"
else
    echo -e "Result: ${RED}SYSTEM UNSTABLE${NC}"
fi
exit $EXIT_CODE
