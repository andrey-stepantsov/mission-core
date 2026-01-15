import time
import os
import sys
import re
import json
import subprocess
from pathlib import Path

# Force Line Buffering for Docker Logs
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Add radio to path (Assuming /mission/tools/lib structure)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import radio

MY_NAME = "LocalSmith"
POLL_INTERVAL = 1.0

# Paths (Container View)
REPO_ROOT = Path("/repo")
DDD_CONFIG = REPO_ROOT / ".ddd" / "config.json"
DDD_TEST_BIN = Path("/mission/tools/ddd/bin/ddd-test")

def run_verification():
    """Runs the ddd-test harness to verify config changes."""
    print("   [Test] Running DDD Verification...")
    if not DDD_TEST_BIN.exists():
        return False, "Error: ddd-test binary not found in container."
    
    try:
        # We run ddd-test from the repo root
        result = subprocess.run(
            [str(DDD_TEST_BIN)], 
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return True, "Verification Passed."
        else:
            # Shorten output to prevent log bloating
            err_msg = result.stderr[:500] + "..." if len(result.stderr) > 500 else result.stderr
            return False, f"Verification Failed:\n{err_msg}"
    except Exception as e:
        return False, f"Harness Error: {e}"

def process_request(request, sender):
    print(f"🔨 Processing request from {sender}")
    
    # 1. Simulate Action
    action_log = f"Analyzed request from {sender}. (Simulated Edit)"
    
    # 2. Verify
    success, message = run_verification()
    
    if success:
        return "ACK", f"{action_log}\n\n✅ {message}"
    else:
        return "LOG", f"{action_log}\n\n❌ {message}"

def main():
    print(f"🔧 Local Smith Online (Containerized)")
    print(f"   Watching: {radio.DEFAULT_LOG}")
    
    log_path = radio.DEFAULT_LOG
    last_pos = 0
    if os.path.exists(log_path):
        last_pos = os.path.getsize(log_path)

    while True:
        try:
            if os.path.exists(log_path):
                current_size = os.path.getsize(log_path)
                
                if current_size > last_pos:
                    with open(log_path, 'r') as f:
                        f.seek(last_pos)
                        new_lines = f.readlines()
                        last_pos = f.tell()

                    for line in new_lines:
                        # CRITICAL FIX: Only match lines STARTING with ###
                        # This prevents matching quoted messages inside other messages
                        if not line.startswith("###"):
                            continue
                            
                        match = re.match(r"^### \[.*\] \[(.*) -> (.*)\] \[(.*)\]", line)
                        if match:
                            sender, recipient, msg_type = match.group(1), match.group(2), match.group(3)
                            
                            if recipient == MY_NAME and msg_type == "REQ":
                                print(f"⚡️ Activated by {sender}")
                                reply_type, reply_msg = process_request(line, sender)
                                radio.append_entry(MY_NAME, sender, reply_type, reply_msg)
                
                elif current_size < last_pos:
                    last_pos = 0
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
