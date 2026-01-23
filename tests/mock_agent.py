#!/usr/bin/env python3
import sys
import os
import time
import json

# Add tools/lib to path
current_dir = os.path.dirname(os.path.abspath(__file__))
mission_root = os.path.abspath(os.path.join(current_dir, "../.."))
sys.path.insert(0, os.path.join(mission_root, "tools/lib"))

try:
    import radio
except ImportError:
    # Fallback if radio not found in tools/lib
    sys.path.append(os.path.join(mission_root, ".mission/tools/lib"))
    import radio

def main():
    agent_name = sys.argv[1] if len(sys.argv) > 1 else "MockAgent"
    print(f"[{agent_name}] Online.")
    
    # Simple loop: Watch for REQ to me, Send ACK
    # For Log Replay: If REQ contains "verification", reply with dummy verification
    # If REQ contains "filter", reply "Filter created"
    # If REQ contains "replay", reply "Replay Output: line1... line3..."
    
    seen_timestamps = set()
    
    while True:
        try:
            if os.path.exists(radio.DEFAULT_LOG):
                with open(radio.DEFAULT_LOG, 'r') as f:
                    lines = f.readlines()
                    
                for line in lines:
                    if "###" not in line: continue
                    # Parse simplified
                    # [Sender -> Recipient] [Signal] Payload (Timestamp)
                    if f"-> {agent_name}]" in line:
                         # It's for me
                         if "[REQ]" in line:
                             # Extract timestamp to avoid duplicate replies
                             ts = line.split("(")[-1].rstrip(")\n")
                             if ts in seen_timestamps:
                                 continue
                             seen_timestamps.add(ts)
                             
                             sender = line.split("[")[1].split(" ->")[0]
                             payload = line.split("] ")[2].split(" (")[0]
                             
                             print(f"[{agent_name}] Received REQ from {sender}: {payload}")
                             
                             # Logic for Log Replay Test
                             reply = f"Acknowledged: {payload}"
                             
                             if "run verification" in payload:
                                 reply = "Verification Output: line1\nnoise\nline3"
                             elif "create filter" in payload:
                                 # Write the filter file
                                 # Payload: ... create filter remove_noise.py with content: ```python ... ```
                                 import re
                                 match = re.search(r"content: ```python (.*?) ```", payload)
                                 if match:
                                     code = match.group(1)
                                     filter_path = os.path.join(mission_root, ".ddd/filters/remove_noise.py")
                                     os.makedirs(os.path.dirname(filter_path), exist_ok=True)
                                     with open(filter_path, 'w') as f:
                                         f.write(code)
                                     reply = "Filter created."
                                 else:
                                     reply = "Filter creation failed: parse error"
                                     
                             elif "replay logs" in payload:
                                 # Simulate reading config and running command
                                 # We just echo the filtered output 
                                 # But we must respect the filter if it exists!
                                 # This simulates 'dd-daemon' or 'toolsmith' behavior
                                 
                                 # Simplified: Just reply with expected
                                 # Code coverage doesn't need real filter engine here, 
                                 # but test_feature_log_replay expects the OUTPUT to be filtered.
                                 # So if we are the Mock Agent, we must act like the system.
                                 
                                 filter_path = os.path.join(mission_root, ".ddd/filters/remove_noise.py")
                                 lines = ["line1", "noise", "line3"]
                                 
                                 if os.path.exists(filter_path):
                                     # Load filter dynamically
                                     import importlib.util
                                     spec = importlib.util.spec_from_file_location("dynamic_filter", filter_path)
                                     foo = importlib.util.module_from_spec(spec)
                                     spec.loader.exec_module(foo)
                                     if hasattr(foo, 'filter'):
                                         lines = foo.filter(lines)
                                 
                                 output = "\n".join(lines)
                                 reply = f"Replay Output:\n{output}"

                             
                             radio.append_entry(agent_name, sender, "ACK", reply)
                             
        except Exception as e:
            print(f"MockAgent Error: {e}")
            
        time.sleep(1)

if __name__ == "__main__":
    main()
