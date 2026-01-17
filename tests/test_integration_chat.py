import unittest
import subprocess
import time
import os
import sys
from pathlib import Path

# --- Setup Paths ---
# We point to the libs inside the .mission structure
current_file = Path(__file__).resolve()
mission_root = current_file.parent.parent
lib_dir = mission_root / "tools" / "lib"
sys.path.insert(0, str(lib_dir))

import radio

# Agent Binaries
DIRECTOR_BIN = mission_root / "tools" / "bin" / "director"
LOCALSMITH_BIN = mission_root / "tools" / "bin" / "toolsmith_local"

class TestSwarmIntegration(unittest.TestCase):
    def setUp(self):
        """Reset the environment before test."""
        # Truncate log to ensure we catch FRESH messages
        with open(radio.DEFAULT_LOG, 'w') as f:
            f.write("# Integration Test Log Start\n")
        self.processes = []

    def tearDown(self):
        """Cleanup processes."""
        print("\n[Teardown] Killing agents...")
        for p in self.processes:
            p.terminate()
            try:
                p.wait(timeout=2)
            except:
                p.kill()
        # Force cleanup of container artifacts
        subprocess.run("docker ps -q --filter 'ancestor=aider-vertex' | xargs -r docker kill", shell=True, stderr=subprocess.DEVNULL)

    def start_agent(self, name, binary_path):
        print(f"   [Launch] {name}...")
        p = subprocess.Popen(
            [str(binary_path)],
            stdout=subprocess.DEVNULL, # Silence stdout to keep test clean
            stderr=subprocess.DEVNULL,
            text=True
        )
        self.processes.append(p)
        time.sleep(3) # Wait for container boot
        return p

    def wait_for_log(self, sender, recipient, msg_type, timeout=20):
        print(f"   [Wait] Expecting: {sender} -> {recipient} [{msg_type}]")
        start = time.time()
        target = f"[{sender} -> {recipient}] [{msg_type}]"
        
        while time.time() - start < timeout:
            if os.path.exists(radio.DEFAULT_LOG):
                with open(radio.DEFAULT_LOG, 'r') as f:
                    content = f.read()
                    if target in content:
                        print(f"     [✓] Matched: {target}")
                        return True
            time.sleep(1)
        
        print(f"     [!] Timeout looking for {target}")
        return False

    def test_local_smith_reply(self):
        """Verify Local Smith hears User and replies."""
        # 1. Start Local Smith
        self.start_agent("LocalSmith", LOCALSMITH_BIN)
        
        # 2. Director -> LocalSmith (Agent only listens to Director)
        radio.append_entry("Director", "LocalSmith", "REQ", "Integration Ping")
        
        # 3. Expect LocalSmith -> Director (ACK or LOG)
        # Note: It might reply LOG if verification fails, or ACK if simulated.
        # We check for either to be robust.
        success_ack = self.wait_for_log("LocalSmith", "Director", "ACK", timeout=15)
        success_log = self.wait_for_log("LocalSmith", "Director", "LOG", timeout=1)
        
        self.assertTrue(success_ack or success_log, "LocalSmith did not reply!")

if __name__ == '__main__':
    unittest.main()
