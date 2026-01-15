import unittest
import subprocess
import time
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
LOCALSMITH_BIN = mission_root / "tools" / "bin" / "toolsmith_local"
REPO_ROOT = mission_root.parent
DDD_DIR = REPO_ROOT / ".ddd"
CONFIG_FILE = DDD_DIR / "config.json"
CONFIG_BAK = DDD_DIR / "config.json.bak"
FILTER_DIR = DDD_DIR / "filters"
TEST_FILTER = FILTER_DIR / "ignore_info.py"

class TestConfigFlow(unittest.TestCase):
    def setUp(self):
        """Prepare the battlefield."""
        with open(radio.DEFAULT_LOG, 'w') as f:
            f.write("# Scenario Test Log\n")
        
        if not DDD_DIR.exists():
            os.makedirs(DDD_DIR)
            os.makedirs(FILTER_DIR)
            
        print(f"   [Setup] Resetting {CONFIG_FILE}")
        with open(CONFIG_FILE, 'w') as f:
            json.dump({"verification_command": "echo 'initial'"}, f)

        if CONFIG_BAK.exists(): os.remove(CONFIG_BAK)
        if TEST_FILTER.exists(): os.remove(TEST_FILTER)
        
        self.processes = []

    def tearDown(self):
        print("\n[Teardown] Killing agents...")
        for p in self.processes:
            p.terminate()
            try:
                p.wait(timeout=1)
            except:
                p.kill()
        subprocess.run("docker ps -q --filter 'ancestor=aider-vertex' | xargs -r docker kill", shell=True, stderr=subprocess.DEVNULL)
        
        if CONFIG_BAK.exists():
            shutil.copy(CONFIG_BAK, CONFIG_FILE)
            os.remove(CONFIG_BAK)
        if TEST_FILTER.exists():
            os.remove(TEST_FILTER)

    def start_agent(self, name, binary_path):
        print(f"   [Launch] {name}...")
        p = subprocess.Popen(
            [str(binary_path)],
            stdout=sys.stdout,
            stderr=sys.stderr,
            text=True
        )
        self.processes.append(p)
        time.sleep(3) 
        return p

    def wait_for_ack(self, sender, recipient, match_text=None, timeout=15):
        """
        Waits for an ACK.
        If match_text is provided, only returns if the line contains that text.
        """
        print(f"   [Wait] Expecting ACK from {sender} matching '{match_text}'...")
        start = time.time()
        target_header = f"[{sender} -> {recipient}] [ACK]"
        
        while time.time() - start < timeout:
            if os.path.exists(radio.DEFAULT_LOG):
                with open(radio.DEFAULT_LOG, 'r') as f:
                    lines = f.readlines()
                    for line in reversed(lines):
                        if target_header in line:
                            # If we need specific content, check for it
                            if match_text and match_text not in line:
                                continue # This is an old ACK, keep looking or waiting
                            
                            print(f"     [✓] Received: {line.strip()}")
                            return line
            time.sleep(1)
        
        print(f"     [!] Timeout waiting for ACK")
        return None

    def test_full_configuration_cycle(self):
        self.start_agent("LocalSmith", LOCALSMITH_BIN)

        # --- STEP 1: BACKUP ---
        print("\n--- Step 1: Request Backup ---")
        radio.append_entry("Director", "LocalSmith", "REQ", "backup config.json")
        # specific check for 'Backup created'
        ack1 = self.wait_for_ack("LocalSmith", "Director", match_text="Backup created")
        self.assertIsNotNone(ack1, "Step 1: Agent timed out")
        self.assertTrue(CONFIG_BAK.exists(), "Backup file was not created!")
        print("   [✓] Backup confirmed.")

        # --- STEP 2: RECONFIGURE COMMAND ---
        print("\n--- Step 2: Update Verification Command ---")
        new_cmd = "echo 'step 1'; echo 'step 1 info'; echo 'step 3'"
        msg = f"set verification_command to: {new_cmd}"
        radio.append_entry("Director", "LocalSmith", "REQ", msg)
        
        # specific check for 'Config updated'
        ack2 = self.wait_for_ack("LocalSmith", "Director", match_text="Config updated")
        self.assertIsNotNone(ack2, "Step 2: Agent timed out")
        
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)
        self.assertEqual(data.get("verification_command"), new_cmd, "Config JSON was not updated!")
        print("   [✓] Config update confirmed.")

        # --- STEP 3: ADD FILTER ---
        print("\n--- Step 3: Add Filter ---")
        filter_code = "def filter(lines): return [l for l in lines if 'info' not in l]"
        msg = f"create filter ignore_info.py with content: ```python {filter_code} ```"
        radio.append_entry("Director", "LocalSmith", "REQ", msg)
        
        # specific check for 'Filter created'
        ack3 = self.wait_for_ack("LocalSmith", "Director", match_text="Filter created")
        self.assertIsNotNone(ack3, "Step 3: Agent timed out")
        self.assertTrue(TEST_FILTER.exists(), "Filter file was not created!")
        print("   [✓] Filter creation confirmed.")

        # --- STEP 4: VERIFY OUTPUT ---
        print("\n--- Step 4: Run Verification ---")
        radio.append_entry("Director", "LocalSmith", "REQ", "run verification")
        
        # specific check for 'Verification Output'
        ack4 = self.wait_for_ack("LocalSmith", "Director", match_text="Verification Output")
        self.assertIsNotNone(ack4, "Step 4: Agent timed out")
        print("   [✓] Verification run confirmed.")

if __name__ == '__main__':
    unittest.main()
