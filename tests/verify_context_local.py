
import os
import time
import subprocess
from datetime import datetime

# Initialize Mock Environment
LOG_FILE = "/tmp/mock_mission_log.md"
os.environ["MISSION_JOURNAL"] = LOG_FILE

# Ensure log exists
with open(LOG_FILE, "w") as f:
    f.write("# Mock Log\n")

print("--- Launching LocalSmith (Mock) ---")
# Launch LocalSmith in background
p = subprocess.Popen(["python3", "/Users/stepants/dev/chaos/.mission/tools/lib/toolsmith_local.py"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

time.sleep(2) # Wait for startup

print("--- Simulating Context Switch ---")
with open(LOG_FILE, "a") as f:
    f.write("[CTX] Switch to /tmp/context_test\n")
    f.flush()

time.sleep(1)

print("--- Checking Output ---")
# We expect to see "Context Switched to: /tmp/context_test" in stdout
start_time = time.time()
found = False
p.file = p.stdout
while time.time() - start_time < 5:
    line = p.stdout.readline()
    if not line: break
    print(f"HOST LOG: {line.strip()}")
    if "Context Switched to: /tmp/context_test" in line:
        print("✅ SUCCESS: Context switch detected!")
        found = True
        break

if not found:
    print("❌ FAILED: Did not detect context switch.")

p.kill()
