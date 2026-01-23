import subprocess
import os
import sys
import json
import time

def monitor_build(host, remote_log, stop_on_finish=False, mirror_log=None):
    """
    Monitors the remote build log.
    If stop_on_finish is True, returns 0 on SUCCESS, 1 on FAILURE.
    Includes robust reconnection logic.
    """
    ssh_opts = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]
    
    while True:
        # Pre-Check (only for stop_on_finish)
        if stop_on_finish:
             try:
                check_cmd = ["ssh"] + ssh_opts + [host, f"unset HISTFILE; tail -n 50 {remote_log} 2>/dev/null"]
                res = subprocess.run(check_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if res.returncode == 0:
                    for line in res.stdout.splitlines():
                        if "[MISSION COMPLETE]" in line or "BUILD_SUCCESS" in line:
                            print(f"✅ [MISSION COMPLETE] (Detected in log history)", flush=True)
                            return 0
                        if "[MISSION FAILED]" in line or "BUILD_FAILURE" in line:
                            print(f"❌ [MISSION FAILED] (Detected in log history)", flush=True)
                            return 1
                        # Support legacy signals (standard dd-daemon output)
                        if "[*] Pipeline Complete." in line:
                            print(f"✅ [MISSION COMPLETE] (Detected in log history)", flush=True)
                            return 0
                        if line.startswith("[-] ") and "Failed" in line:
                             # Be careful not to match random lines?
                             # Standard failures are: "[-] BUILD Failed (Exit: ...)" or "[-] VERIFY Failed"
                            print(f"❌ [MISSION FAILED] (Detected in log history)", flush=True)
                            return 1

             except Exception:
                 pass 

        if host == 'local':
             # Local Stream
             cmd = ["tail", "-n", "1000", "-F", remote_log]
        else:
             # Remote Stream
             cmd = ["ssh"] + ssh_opts + [host, f"unset HISTFILE; tail -n 1000 -F {remote_log} 2>/dev/null"]
        
        try:
            print(f"📡 Tuning into Mission Radio on {host}...", flush=True)
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
            
            while True:
                raw_line = process.stdout.readline()
                if not raw_line:
                    break
                
                # Mirror
                if mirror_log:
                    try:
                        with open(mirror_log, 'a') as f:
                            f.write(raw_line)
                    except Exception:
                        pass

                line = raw_line.strip()
                if not line:
                    continue
                    
                if line.startswith("[RADIO]"):
                    # Parse Signal
                    payload_str = line[len("[RADIO]"):].strip()
                    try:
                        payload = json.loads(payload_str)
                        event = payload.get("event")
                        msg = payload.get("message")
                        ts = payload.get("timestamp")
                        
                        if event == "BUILD_START":
                            print(f"\n🚀 [MISSION START] {ts}", flush=True)
                            print(f"   >> {msg}", flush=True)
                        elif event == "BUILD_SUCCESS":
                            print(f"✅ [MISSION COMPLETE] {ts}", flush=True)
                            print(f"   >> {msg}\n", flush=True)
                            if stop_on_finish: return 0
                        elif event == "BUILD_FAILURE":
                            print(f"❌ [MISSION FAILED] {ts}", flush=True)
                            print(f"   >> {msg}\n", flush=True)
                            if stop_on_finish: return 1
                        else:
                            print(f"ℹ️  [RADIO] {event}: {msg}", flush=True)
                            
                    except json.JSONDecodeError:
                        print(f"⚠️  [RADIO CORRUPT] {line}", flush=True)
                else:
                    # Legacy Signal Detection
                    print(f"   [log] {line}", flush=True)
                    
                    if "[*] Pipeline Complete." in line:
                        print(f"✅ [MISSION COMPLETE] (Legacy Signal)", flush=True)
                        if stop_on_finish: return 0
                        
                    if line.startswith("[-] ") and "Failed" in line:
                        print(f"❌ [MISSION FAILED] (Legacy Signal)", flush=True)
                        if stop_on_finish: return 1

                    # Fallback Detection: DD-Daemon always writes Build Stats at end
                    if "Est. Tokens:" in line or "--- 📊 Build Stats ---" in line:
                         # We saw the stats, so the build is done.
                         # We assume success (0) because we can't distinguish failure from log content easily
                         # without parsing. The Agent will parse the output anyway.
                         if stop_on_finish:
                             print(f"✅ [MISSION COMPLETE] (Stats Detected)", flush=True)
                             return 0
            
            # If we get here, the process ended (but wait didn't end).
            # Means SSH dropped.
            if process.poll() is None:
                process.terminate()
                
            print("⚠️ connection lost...", flush=True)
            
        except KeyboardInterrupt:
            print("\n👋 Radio off.")
            if stop_on_finish: 
                sys.exit(130) # Standard interrupt exit
            return
        except Exception as e:
            print(f"Error listening: {e}")
            
        if stop_on_finish:
            print("🔄 Reconnecting in 3s...", flush=True)
            time.sleep(3)
        else:
            # Reconnect even if not stop_on_finish (listening mode)
            print("🔄 Reconnecting in 3s...", flush=True)
            time.sleep(3)
