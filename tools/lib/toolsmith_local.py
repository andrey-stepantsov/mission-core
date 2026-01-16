import os
import time
import subprocess
import sys
import json
from datetime import datetime

# --- Configuration ---
LOG_FILE = os.environ.get("MISSION_JOURNAL", ".mission-context/mission_log.md")
REPO_ROOT = "/repo"

def log(msg):
    """Prints to Docker logs with flushing."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)

def write_ack(message):
    """Writes an [ACK] to the radio file."""
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    entry = f"\n### [{timestamp}] [LocalSmith -> Director] [ACK] {message}\n"
    
    try:
        with open(LOG_FILE, "a") as f:
            f.write(entry)
            f.flush()
            os.fsync(f.fileno())
        log(f"Sent ACK: {message}")
    except Exception as e:
        log(f"Radio Write Error: {e}")

def execute_shell(cmd, cwd=REPO_ROOT):
    try:
        res = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        return res.stdout.strip() if res.returncode == 0 else f"Error: {res.stderr.strip()}"
    except Exception as e:
        return f"Exception: {e}"

def process_command(cmd_text):
    log(f"Processing: {cmd_text}")
    
    # Normalizing command
    cmd_clean = cmd_text.strip()
    
    # 1. BACKUP
    if cmd_clean.startswith("backup "):
        filename = cmd_clean.replace("backup ", "").strip()
        result = execute_shell(f"cp -r {filename} {filename}.bak")
        if not result: result = "Success" # cp produces no stdout on success
        return f"Backup of {filename}: {result}"

    # 2. CONFIG (Flexible parsing)
    # Matches: "set key to value" or "set key = value"
    elif cmd_clean.startswith("set "):
        parts = cmd_clean.split(" ", 2) # set, key, rest
        if len(parts) >= 3:
            key = parts[1]
            value = parts[2]
            # Remove "to" or "=" if present
            if value.startswith("to "): value = value[3:]
            elif value.startswith("= "): value = value[2:]
            
            # Simulate saving config
            config_path = os.path.join(REPO_ROOT, ".ddd")
            os.makedirs(config_path, exist_ok=True)
            with open(os.path.join(config_path, "config.json"), "w") as f:
                json.dump({key: value}, f)
                
            return f"Config updated: {key} -> {value}"
        return "Config format error. Use: set <key> to <value>"

    # 3. VERIFICATION
    elif "verification" in cmd_clean:
        # Read the config we just saved
        try:
            with open(os.path.join(REPO_ROOT, ".ddd/config.json"), "r") as f:
                cfg = json.load(f)
                cmd = cfg.get("verification_command", "echo 'System Online'")
                output = execute_shell(cmd)
                return f"Verification Output: {output}"
        except:
            return "Verification: System Online (Default)"

    # 4. ECHO/DEBUG
    elif cmd_clean.startswith("echo "):
        return execute_shell(cmd_clean)

    # UNKNOWN
    else:
        return f"Unknown command: {cmd_clean}"

def main():
    log("LocalSmith v2 Daemon Started.")
    
    # Ensure log exists
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            f.write("# Mission Log\n")

    # Open file and go to end
    f = open(LOG_FILE, "r")
    f.seek(0, 2)

    while True:
        line = f.readline()
        if not line:
            time.sleep(0.1)
            continue
            
        # Look for [REQ] from Director
        if "[REQ]" in line and "[Director -> LocalSmith]" in line:
            # Extract command part
            try:
                cmd_part = line.split("[REQ]", 1)[1].strip()
                response = process_command(cmd_part)
                write_ack(response)
            except Exception as e:
                log(f"Parse Error: {e}")

if __name__ == "__main__":
    main()
