import time
import os
import sys
import subprocess
import pytest

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(root_dir, "tools/lib"))
import radio

# Use Mock Agent for stable testing without credentials
DIRECTOR_BIN = os.path.join(os.path.dirname(__file__), "mock_agent.py")

@pytest.fixture
def director_process():
    if os.path.exists(radio.DEFAULT_LOG):
        os.remove(radio.DEFAULT_LOG)
    
    # Use a known stable model for testing
    env = os.environ.copy()
    # gemini-1.5-flash is fast, cheap, and widely available
    env["DIRECTOR_MODEL"] = "gemini-1.5-flash"
    env["MISSION_JOURNAL"] = radio.DEFAULT_LOG

    print("\n[Fixture] Starting Director (Mock)...")
    
    # Mock agent doesn't need API keys
    
    proc = subprocess.Popen(
        [DIRECTOR_BIN],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    # Warmup
    time.sleep(5) 
    
    # Check for early death
    if proc.poll() is not None:
        out, err = proc.communicate()
        print(f"\n[CRASH DETECTED] STDOUT:\n{out}")
        print(f"[CRASH DETECTED] STDERR:\n{err}")
        pytest.fail("Director crashed on startup (check stderr above)")
        
    yield proc
    
    # Teardown
    proc.terminate()
    try:
        out, err = proc.communicate(timeout=2)
    except:
        proc.kill()

@pytest.mark.skip(reason="Mock agent unstable in devbox")
def test_director_responds_to_req(director_process):
    # 1. Transmit
    print("[Test] Sending REQ...")
    radio.append_entry("TestUser", "Director", "REQ", "Test Payload")
    
    # 2. Wait
    found_ack = False
    start = time.time()
    while time.time() - start < 15:
        if not os.path.exists(radio.DEFAULT_LOG):
            time.sleep(0.5)
            continue
            
        with open(radio.DEFAULT_LOG, 'r') as f:
            content = f.read()
            # Look for ACK
            if "Director -> TestUser" in content and "[ACK]" in content:
                found_ack = True
                break
        time.sleep(1)
        
    if not found_ack:
        # Dump Log for debugging
        if os.path.exists(radio.DEFAULT_LOG):
            print("\n--- MISSION LOG DUMP ---")
            with open(radio.DEFAULT_LOG, 'r') as f:
                print(f.read())
            print("------------------------")
            
    assert found_ack, "Director failed to ACK (Logs dumped above)."
