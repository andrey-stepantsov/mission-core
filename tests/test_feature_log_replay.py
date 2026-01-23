import unittest
import subprocess
import time
import pytest
import os
import sys
import json
import shutil
from pathlib import Path

# --- Setup Paths ---
current_file = Path(__file__).resolve()
mission_root = current_file.parent.parent
lib_dir = mission_root / "tools" / "lib"
sys.path.insert(0, str(lib_dir))

import radio

# Paths
# Use Mock Agent for stable testing
LOCALSMITH_BIN = mission_root / "tests" / "mock_agent.py"
REPO_ROOT = mission_root.parent
DDD_DIR = REPO_ROOT / ".ddd"
CONFIG_FILE = DDD_DIR / "config.json"
FILTER_DIR = DDD_DIR / "filters"
TEST_FILTER = FILTER_DIR / "remove_noise.py"

class TestLogReplay(unittest.TestCase):
    def setUp(self):
        """Prepare the battlefield."""
        host_log_path = REPO_ROOT / ".mission-context" / "mission_log.md"
        radio.DEFAULT_LOG = str(host_log_path)
        
        if not host_log_path.parent.exists():
            os.makedirs(host_log_path.parent)

        with open(radio.DEFAULT_LOG, 'w') as f:
            f.write("# Replay Test Log\n")
        
        if not DDD_DIR.exists():
            os.makedirs(DDD_DIR)
            os.makedirs(FILTER_DIR)
            
        # 1. Config: Echo 3 lines
        with open(CONFIG_FILE, 'w') as f:
            json.dump({"verification_command": "echo 'line1'; echo 'noise'; echo 'line3'"}, f)

        # Cleanup
        if TEST_FILTER.exists(): os.remove(TEST_FILTER)
        
        self.processes = []

    def tearDown(self):
        print("\n[Teardown] Killing agents...")
        # 1. Terminate python subprocesses
        for p in self.processes:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait()
        
        # 2. Kill Docker containers (safety net)
        subprocess.run("docker ps -q --filter 'ancestor=mission-core:latest' | xargs -r docker kill", shell=True, stderr=subprocess.DEVNULL)
        
        # 3. Cleanup files
        if TEST_FILTER.exists():
            os.remove(TEST_FILTER)

    def start_agent(self, name, binary_path):
        print(f"   [Launch] {name}...")
        env = os.environ.copy()
        env["MISSION_JOURNAL"] = radio.DEFAULT_LOG
        
        p = subprocess.Popen(
            [str(binary_path), name],
            stdout=sys.stdout,
            stderr=sys.stderr,
            text=True,
            env=env
        )
        self.processes.append(p)
        time.sleep(3) 
        return p

    def wait_for_ack(self, sender, recipient, match_text=None, timeout=15):
        print(f"   [Wait] Expecting ACK from {sender} matching '{match_text}'...")
        start = time.time()
        start_marker = f"[{sender} -> {recipient}] [ACK]"
        
        while time.time() - start < timeout:
            if os.path.exists(radio.DEFAULT_LOG):
                with open(radio.DEFAULT_LOG, 'r') as f:
                    content = f.read()
                    
                # Split by entries (###)
                entries = content.split("###")
                for entry in reversed(entries):
                    if start_marker in entry:
                        if match_text and match_text not in entry:
                            continue
                        print(f"     [✓] Received: {entry.strip()[:60]}...")
                        return entry.strip()
            time.sleep(1)
        
        print(f"     [!] Timeout waiting for ACK")
        return None

    @pytest.mark.skip(reason="Mock agent unstable in devbox")
    def test_log_replay_filtering(self):
        self.start_agent("LocalSmith", LOCALSMITH_BIN)

        # --- STEP 1: Run Verification (Unfiltered) ---
        print("\n--- Step 1: Run Verification (Unfiltered) ---")
        radio.append_entry("Director", "LocalSmith", "REQ", "run verification")
        ack1 = self.wait_for_ack("LocalSmith", "Director", match_text="Verification Output")
        self.assertIsNotNone(ack1, "Step 1: Agent timed out")
        
        self.assertIn("line1", ack1)
        self.assertIn("noise", ack1) # Should be present initially
        self.assertIn("line3", ack1)
        print("   [✓] Initial output confirmed (Unfiltered).")

        # --- STEP 2: Add Filter ---
        print("\n--- Step 2: Add Filter (remove 'noise') ---")
        filter_code = "def filter(lines): return [l for l in lines if 'noise' not in l]"
        msg = f"create filter remove_noise.py with content: ```python {filter_code} ```"
        radio.append_entry("Director", "LocalSmith", "REQ", msg)
        
        ack2 = self.wait_for_ack("LocalSmith", "Director", match_text="Filter created")
        self.assertIsNotNone(ack2, "Step 2: Agent timed out")
        self.assertTrue(TEST_FILTER.exists(), "Filter file was not created!")
        print("   [✓] Filter creation confirmed.")

        # --- STEP 3: Replay Logs (Filtered) ---
        print("\n--- Step 3: Replay Logs (Should apply filter) ---")
        radio.append_entry("Director", "LocalSmith", "REQ", "replay logs")
        
        ack3 = self.wait_for_ack("LocalSmith", "Director", match_text="Replay Output")
        self.assertIsNotNone(ack3, "Step 3: Agent timed out")
        
        # VERIFICATION: 'noise' should be GONE, 'line1' and 'line3' should REMAIN
        self.assertIn("line1", ack3)
        self.assertIn("line3", ack3)
        self.assertNotIn("noise", ack3, "Filter FAILED: 'noise' still present in replay output!")
        
        print("   [✓] Replay filtered successfully.")

if __name__ == '__main__':
    unittest.main()
