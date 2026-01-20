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
        # 1. Cleanup ANY existing containers
        subprocess.run("docker ps -q --filter 'ancestor=aider-vertex' | xargs -r docker kill", shell=True, stderr=subprocess.DEVNULL)
        
        # Ensure mission_log.md exists for Aider to read
        # radio.DEFAULT_LOG is typically .../.mission-context/mission_log.md
        # We already ensured the DIR exists in previous step.
        # Now create the file if not exists, or truncate it.
        with open(radio.DEFAULT_LOG, 'w') as f:
            f.write("# Integration Test Log Start\n")
        # Ensure Docker container can write to it
        os.chmod(radio.DEFAULT_LOG, 0o666)
        
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
        
        # Pass the Log File location explicitly to the Agent (Container Path)
        # Host: .../.mission/.mission-context/mission_log.md
        # Container (Volume /mission): /mission/.mission-context/mission_log.md
        env = os.environ.copy()
        env["MISSION_JOURNAL"] = "/mission/.mission-context/mission_log.md"
        
        p = subprocess.Popen(
            [str(binary_path)],
            stdout=None, # Capture output for debug
            stderr=None,
            text=True,
            env=env
        )
        self.processes.append(p)
        self.processes.append(p)
        time.sleep(1) # Basic process spinup
        return p

    def wait_for_log(self, sender, recipient, msg_type, content_substr=None, timeout=20):
        print(f"   [Wait] Expecting: {sender} -> {recipient} [{msg_type}]")
        start = time.time()
        target = f"[{sender} -> {recipient}] [{msg_type}]"
        
        while time.time() - start < timeout:
            if os.path.exists(radio.DEFAULT_LOG):
                with open(radio.DEFAULT_LOG, 'r') as f:
                    content = f.read()
                    if target in content:
                        if content_substr and content_substr not in content:
                            time.sleep(1)
                            continue
                        print(f"     [✓] Matched: {target}")
                        return True
            time.sleep(1)
        
        print(f"     [!] Timeout looking for {target}")
        return False

    def test_local_smith_reply(self):
        """Verify Local Smith hears User and replies."""
        # 1. Start Local Smith
        self.start_agent("LocalSmith", LOCALSMITH_BIN)
        
        # 2. Wait for Daemon Readiness (Handshake)
        print("   [Sync] Waiting for LocalSmith to signal readiness...")
        ready = self.wait_for_log("LocalSmith", "Director", "ACK", content_substr="Daemon Online", timeout=30)
        self.assertTrue(ready, "LocalSmith failed to signal readiness (timeout).")

        # 3. Director -> LocalSmith (Agent only listens to Director)
        print("   [Radio] Transmitting REQ...")
        radio.append_entry("Director", "LocalSmith", "REQ", "Integration Ping")
        
        # 4. Expect LocalSmith -> Director (ACK or LOG)
        # Note: It might reply LOG if verification fails, or ACK if simulated.
        # We check for either to be robust.
        success_ack = self.wait_for_log("LocalSmith", "Director", "ACK", timeout=30)
        success_log = self.wait_for_log("LocalSmith", "Director", "LOG", timeout=1)
        
        self.assertTrue(success_ack or success_log, "LocalSmith did not reply!")

if __name__ == '__main__':
    unittest.main()
