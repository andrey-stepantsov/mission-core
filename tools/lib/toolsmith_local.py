#!/usr/bin/env python3
import time
import sys
import os
import re
import json
import shutil
import subprocess
from pathlib import Path

# Import Radio
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))
import radio

# Configuration
AGENT_NAME = "LocalSmith"
REPO_ROOT = Path("/repo") # Container View
DDD_DIR = REPO_ROOT / ".ddd"
CONFIG_FILE = DDD_DIR / "config.json"

def log(msg):
    """Stdout log for container logs."""
    print(f"[{AGENT_NAME}] {msg}")

def execute_shell(command):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=str(REPO_ROOT),
            capture_output=True, 
            text=True
        )
        return result.stdout.strip() + "\n" + result.stderr.strip()
    except Exception as e:
        return f"Execution Error: {str(e)}"

def handle_backup(filename):
    """CMD: backup <file>"""
    src = DDD_DIR / filename
    dst = DDD_DIR / (filename + ".bak")
    
    if not src.exists():
        return f"Error: File {filename} not found in .ddd"
        
    try:
        shutil.copy(src, dst)
        return f"Backup created: {dst}"
    except Exception as e:
        return f"Backup failed: {e}"

def smart_strip_quotes(text):
    """Removes quotes only if they wrap the content."""
    text = text.strip()
    if len(text) >= 2:
        if text.startswith('"') and text.endswith('"'):
            return text[1:-1]
        if text.startswith("'") and text.endswith("'"):
            return text[1:-1]
    return text

def handle_config_update(key, value):
    """CMD: set <key> to <value>"""
    if not CONFIG_FILE.exists():
        return "Error: config.json not found"
        
    try:
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)
        
        # SMART FIX HERE
        clean_value = smart_strip_quotes(value)
        data[key] = clean_value
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f, indent=4)
            
        return f"Config updated: {key} = {clean_value}"
    except Exception as e:
        return f"Config update failed: {e}"

def handle_create_filter(name, content):
    """CMD: create filter <name> with content: <content>"""
    filters_dir = DDD_DIR / "filters"
    if not filters_dir.exists():
        os.makedirs(filters_dir)
        
    target_file = filters_dir / name
    
    # Clean up markdown code blocks if present
    clean_content = content
    if "```python" in clean_content:
        clean_content = clean_content.split("```python")[1].split("```")[0].strip()
    elif "```" in clean_content:
        clean_content = clean_content.split("```")[1].split("```")[0].strip()
        
    try:
        with open(target_file, 'w') as f:
            f.write(clean_content)
        return f"Filter created: {target_file}"
    except Exception as e:
        return f"Write failed: {e}"

def handle_run_verification():
    """CMD: run verification"""
    if not CONFIG_FILE.exists():
        return "Error: No config found"
        
    try:
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)
        
        cmd = data.get("verification_command", "echo 'No command defined'")
        log(f"Running verification: {cmd}")
        output = execute_shell(cmd)
        return f"Verification Output:\n{output}"
    except Exception as e:
        return f"Verification failed: {e}"

def process_request(request, sender):
    """The Brain: Routing Logic."""
    req_lower = request.lower()
    # Keep the debug log for now, it's useful
    log(f"Processing RAW: {repr(request)}")

    # 1. Backup
    if req_lower.startswith("backup "):
        filename = request.split(" ", 1)[1].strip()
        result = handle_backup(filename)
        radio.append_entry(AGENT_NAME, sender, "ACK", result)
        return

    # 2. Config Update
    match_set = re.match(r"set\s+(\w+)\s+to\s*[:]?\s*(.+)", request, re.IGNORECASE)
    if match_set:
        key = match_set.group(1)
        value = match_set.group(2)
        result = handle_config_update(key, value)
        radio.append_entry(AGENT_NAME, sender, "ACK", result)
        return

    # 3. Create Filter
    match_filter = re.match(r"create filter\s+([\w\.]+)\s+with content:?\s*(.*)", request, re.IGNORECASE | re.DOTALL)
    if match_filter:
        name = match_filter.group(1)
        content = match_filter.group(2)
        result = handle_create_filter(name, content)
        radio.append_entry(AGENT_NAME, sender, "ACK", result)
        return

    # 4. Run Verification
    if "run verification" in req_lower:
        result = handle_run_verification()
        radio.append_entry(AGENT_NAME, sender, "ACK", result)
        return

    # Fallback
    radio.append_entry(AGENT_NAME, sender, "LOG", f"Unknown command: {request[:30]}...")

def main():
    log("Online. Monitoring radio frequencies...")
    
    if not os.path.exists(radio.DEFAULT_LOG):
        with open(radio.DEFAULT_LOG, 'w') as f:
            f.write(f"# Mission Log - {AGENT_NAME}\n")

    with open(radio.DEFAULT_LOG, "r") as f:
        f.seek(0, 2)
        
        while True:
            line = f.readline()
            if not line:
                time.sleep(1)
                continue
            
            # log(f"READ LINE: {repr(line)}") # Verbose debug off for prod
            
            if f"-> {AGENT_NAME}]" in line and "[REQ]" in line:
                try:
                    parts = line.split("->")
                    sender_part = parts[0].split("[")[-1].strip()
                    msg_content = line.split("[REQ]", 1)[1].strip()
                    process_request(msg_content, sender_part)
                except Exception as e:
                    log(f"Parse Error: {e}")

if __name__ == "__main__":
    main()
