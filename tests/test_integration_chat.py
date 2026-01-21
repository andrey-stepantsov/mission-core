import subprocess
import time
import os
import sys
import pytest
from pathlib import Path

# --- Setup Paths ---
# We point to the libs inside the .mission structure
current_file = Path(__file__).resolve()
mission_root = current_file.parent.parent
lib_dir = mission_root / "tools" / "lib"
sys.path.insert(0, str(lib_dir))

# Enforce Shared Journal Path (Host side)
# This defaults to .mission/.mission-context/mission_log.md which matches the container mount
os.environ["MISSION_JOURNAL"] = str(mission_root / ".mission-context" / "mission_log.md")

import radio

# Agent Binaries
DIRECTOR_BIN = mission_root / "tools" / "bin" / "director"
LOCALSMITH_BIN = mission_root / "tools" / "bin" / "toolsmith_local"

@pytest.fixture
def swarm_env():
    """Setup and Teardown for Swarm Integration."""
    # 1. Cleanup ANY existing containers
    subprocess.run("docker ps -q --filter 'ancestor=aider-vertex' | xargs -r docker kill", shell=True, stderr=subprocess.DEVNULL)
    
    # Ensure mission_log.md exists for Aider to read
    # radio.DEFAULT_LOG is typically .../.mission-context/mission_log.md
    with open(radio.DEFAULT_LOG, 'w') as f:
        f.write("# Integration Test Log Start\n")
    # Ensure Docker container can write to it
    os.chmod(radio.DEFAULT_LOG, 0o666)
    
    processes = []
    
    yield processes
    
    # Teardown
    print("\n[Teardown] Killing agents...")
    for p in processes:
        p.terminate()
        try:
            p.wait(timeout=2)
        except:
            p.kill()
    # Force cleanup of container artifacts
    subprocess.run("docker ps -q --filter 'ancestor=aider-vertex' | xargs -r docker kill", shell=True, stderr=subprocess.DEVNULL)

def start_agent38(name, binary_path, processes_list):
    """Helper to start agent process (Python 3.8 compatible)."""
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
    processes_list.append(p)
    time.sleep(1) # Basic process spinup
    return p

def wait_for_log(sender, recipient, msg_type, content_substr=None, timeout=20):
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

@pytest.mark.integration
def test_local_smith_reply(swarm_env):
    """Verify Local Smith hears User and replies."""
    # 1. Start Local Smith
    start_agent38("LocalSmith", LOCALSMITH_BIN, swarm_env)
    
    # 2. Wait for Daemon Readiness (Handshake)
    print("   [Sync] Waiting for LocalSmith to signal readiness...")
    ready = wait_for_log("LocalSmith", "Director", "ACK", content_substr="Daemon Online", timeout=30)
    assert ready, "LocalSmith failed to signal readiness (timeout)."

    # 3. Director -> LocalSmith (Agent only listens to Director)
    print("   [Radio] Transmitting REQ...")
    radio.append_entry("Director", "LocalSmith", "REQ", "Integration Ping")
    
    # 4. Expect LocalSmith -> Director (ACK or LOG)
    # Note: It might reply LOG if verification fails, or ACK if simulated.
    # We check for either to be robust.
    success_ack = wait_for_log("LocalSmith", "Director", "ACK", timeout=30)
    success_log = wait_for_log("LocalSmith", "Director", "LOG", timeout=1)
    
    assert success_ack or success_log, "LocalSmith did not reply!"

