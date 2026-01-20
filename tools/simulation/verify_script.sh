#!/bin/bash
set -e

PROJECTOR=/mission/tools/bin/projector

echo "--- 1. Testing Projector Init ---"
$PROJECTOR init mission@mission-host

echo "--- 2. Testing Projector Pull ---"
$PROJECTOR pull /home/mission/test_file.txt

echo "--- 3. Verifying Pull ---"
if [ ! -f hologram/home/mission/test_file.txt ]; then
    echo "FAILED: File not pulled to hologram"
    exit 1
fi
cat hologram/home/mission/test_file.txt

if [ ! -f outside_wall/dummy_dependency.h ]; then
    echo "FAILED: Dummy dependency not created"
    exit 1
fi

echo "--- 4. Testing Projector Push (Success) ---"
echo "Modification from client" >> hologram/home/mission/test_file.txt
$PROJECTOR push hologram/home/mission/test_file.txt

echo "--- 5. Verifying on Host ---"
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null mission@mission-host "cat /home/mission/test_file.txt" | grep "Modification from client"
if [ $? -eq 0 ]; then
    echo "SUCCESS: Host verification passed"
else
    echo "FAILED: Host verification failed"
    exit 1
fi

echo "--- 6. Testing The Wall (Push Failure) ---"
echo "bad" > outside_wall/bad_file.txt
# This command SHOULD fail
set +e
$PROJECTOR push outside_wall/bad_file.txt
RET=$?
set -e

if [ $RET -ne 0 ]; then
    echo "SUCCESS: The Wall blocked the push (Exit code $RET)"
else
    echo "FAILED: The Wall was breached!"
    exit 1
fi

echo "ALL TESTS PASSED"
