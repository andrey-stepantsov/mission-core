import os
import time
import subprocess
import sys
import json
from datetime import datetime

# --- Configuration ---
LOG_FILE = os.environ.get("MISSION_JOURNAL") or ".mission-context/mission_log.md"
REPO_ROOT = "/repo"
CURRENT_CONTEXT = REPO_ROOT

def log(msg):
    """Prints to Docker logs with flushing."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)

def apply_filters(text):
    """Applies all filters in .ddd/filters/ to the text."""
    lines = text.splitlines()
    filter_dir = os.path.join(REPO_ROOT, ".ddd", "filters")
    
    if not os.path.exists(filter_dir):
        return text

    # simple mechanism: load python files, expecting 'def filter(lines): return lines'
    for f in sorted(os.listdir(filter_dir)):
        if f.endswith(".py"):
            try:
                # Dynamic import/exec
                path = os.path.join(filter_dir, f)
                with open(path, "r") as pyf:
                    code = pyf.read()
                
                # Sandboxed execution context
                local_scope = {}
                exec(code, {}, local_scope)
                
                if "filter" in local_scope:
                    lines = local_scope["filter"](lines)
            except Exception as e:
                lines.append(f"[Filter Error {f}]: {e}")
                
    return "\n".join(lines)

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
            if value.startswith("to: "): value = value[4:]
            elif value.startswith("to "): value = value[3:]
            elif value.startswith("= "): value = value[2:]
            
            # Read-Modify-Write
            config_path = os.path.join(REPO_ROOT, ".ddd")
            os.makedirs(config_path, exist_ok=True)
            cfg_file = os.path.join(config_path, "config.json")
            
            data = {}
            if os.path.exists(cfg_file):
                with open(cfg_file, "r") as f:
                    try:
                        data = json.load(f)
                    except: pass
            
            data[key] = value
            
            with open(cfg_file, "w") as f:
                json.dump(data, f)
                
            return f"Config updated: {key} -> {value}"
            return f"Config updated: {key} -> {value}"
        return "Config format error. Use: set <key> to <value>"

    # 3. CREATE FILTER (New)
    elif cmd_clean.startswith("create filter "):
        # Format: create filter <name> with content: <content>
        try:
            parts = cmd_clean.split(" with content: ", 1)
            filename = parts[0].replace("create filter ", "").strip()
            content = parts[1].strip()
            
            # Clean backticks
            if content.startswith("```python"): content = content[9:]
            elif content.startswith("```"): content = content[3:]
            if content.endswith("```"): content = content[:-3]
            content = content.strip()
            
            filter_dir = os.path.join(REPO_ROOT, ".ddd", "filters")
            os.makedirs(filter_dir, exist_ok=True)
            
            with open(os.path.join(filter_dir, filename), "w") as f:
                f.write(content)
                
            return f"Filter created: {filename}"
        except Exception as e:
            return f"Error creating filter: {e}"

    # 3. VERIFICATION
    elif "verification" in cmd_clean:
        # Read the config we just saved (Context-Aware)
        try:
            cfg_path = os.path.join(CURRENT_CONTEXT, ".ddd/config.json")
            # Fallback to Root if context config missing? No, strict is better for now.
            
            # If config doesn't exist in subtext, maybe fallback to root?
            if not os.path.exists(cfg_path) and CURRENT_CONTEXT != REPO_ROOT:
                 cfg_path = os.path.join(REPO_ROOT, ".ddd/config.json")

            cmd = "echo 'System Online'"
            if os.path.exists(cfg_path):
                with open(cfg_path, "r") as f:
                    cfg = json.load(f)
                    cmd = cfg.get("verification_command", cmd)
            
            # Execute in Context!
            output = execute_shell(cmd, cwd=CURRENT_CONTEXT)
                
            # 1. Save Raw Log (in Context)
            log_dir = os.path.join(CURRENT_CONTEXT, ".ddd")
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, "last_run.log")
            
            with open(log_path, "w") as lf:
                lf.write(output)

            # 2. Apply Filters
            filtered_output = apply_filters(output)
            return f"Verification Output: {filtered_output}"
        except Exception as e:
            return f"Verification Error: {e}"

    # 4. REPLAY LOGS (New)
    elif "replay logs" in cmd_clean:
        log_path = os.path.join(REPO_ROOT, ".ddd", "last_run.log")
        if not os.path.exists(log_path):
            return "No previous logs found. Run verification first."
            
        with open(log_path, "r") as f:
            raw_output = f.read()
            
        filtered_output = apply_filters(raw_output)
        return f"Replay Output: {filtered_output}"

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
    
    # Signal Readiness to the Radio (for synchronization)
    write_ack("Daemon Online")

    while True:
        line = f.readline()
        if not line:
            time.sleep(0.1)
            continue
            
        # Look for [CTX] Signal
        if "[CTX] Switch to " in line:
            try:
                new_ctx = line.split("[CTX] Switch to ", 1)[1].strip()
                global CURRENT_CONTEXT
                CURRENT_CONTEXT = new_ctx
                log(f"Context Switched to: {CURRENT_CONTEXT}")
            except Exception:
                pass

        # Look for [REQ] from Director
        if "[REQ]" in line and "[Director -> LocalSmith]" in line:
            # log(f"Detected REQ: {line.strip()}")
            # Extract command part
            try:
                cmd_part = line.split("[REQ]", 1)[1].strip()
                response = process_command(cmd_part)
                write_ack(response)
            except Exception as e:
                log(f"Parse Error: {e}")

if __name__ == "__main__":
    main()
