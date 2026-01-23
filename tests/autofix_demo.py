
import os
import json
import sys
import subprocess
import time

# Resolve paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
HOLOGRAM_DIR = os.path.join(PROJECT_ROOT, "hologram")
CONFIG_FILE = os.path.join(HOLOGRAM_DIR, ".ddd", "config.json")
BAD_FILE = os.path.join(HOLOGRAM_DIR, "bad.c")

def run_projector(args):
    """Runs projector using the python command to avoid path issues."""
    # Use the shim at tools/bin/projector
    shim = os.path.join(PROJECT_ROOT, ".mission/tools/bin/projector")
    cmd = [sys.executable, shim] + args
    
    # Ensure PYTHONPATH includes tools/
    env = os.environ.copy()
    
    # We should run this from mission root usually, but here we run from absolute path
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    return result

def test_autofix():
    print("--- 🧪 Starting Autofix Demo ---")
    
    # 1. Setup Bad File
    print("1. Creating broken file (bad.c)...")
    os.makedirs(os.path.dirname(BAD_FILE), exist_ok=True)
    with open(BAD_FILE, "w") as f:
        f.write("int main() { return 0 }") # Missing semicolon
        
    # 2. Configure for JSON output
    print("2. Configuring .ddd/config.json with gcc_json filter...")
    config = {
        "targets": {
            "dev": {
                "sentinel_file": "SENTINEL", 
                "build": {
                    "cmd": "gcc -o bad bad.c",
                    "filter": "gcc_json"
                }
            }
        }
    }
    
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)
        
    # 3. Push context
    print("3. Pushing context...")
    # Use absolute path so projector can verify it's inside hologram
    res = run_projector(["push", CONFIG_FILE])
    if res.returncode != 0:
        print("❌ Push config failed:", res.stderr)
        print("Stdout:", res.stdout)
        sys.exit(1)
        
    res = run_projector(["push", BAD_FILE])
    if res.returncode != 0:
        print("❌ Push bad.c failed:", res.stderr)
        sys.exit(1)

    # 4. Run Build (Expect Failure)
    print("4. Triggering Build (Expect Failure)...")
    res = run_projector(["build", "--wait"])
    
    # output contains the monitor_build output which prints "[log] ..."
    # We need to scan the logs lines, strip "[log] ".
    
    lines = res.stdout.splitlines()
    cleaned_log = []
    for line in lines:
        if "[log]" in line:
            # Extract content after [log]
            parts = line.split("[log] ", 1)
            if len(parts) > 1:
                cleaned_log.append(parts[1])
        else:
            # Maybe it wasn't prefixed if it came from other stdout
            pass
            
    full_log = "\n".join(cleaned_log)
    
    # Find JSON block
    json_start = full_log.find("[")
    json_end = full_log.rfind("]")
    
    errors = []
    if json_start != -1 and json_end != -1:
        try:
            json_str = full_log[json_start:json_end+1]
            errors = json.loads(json_str)
            print(f"✅ Found {len(errors)} structured errors.")
        except Exception as e:
            print(f"⚠️ Failed to parse JSON: {e}")
            print("Cleaned Log snippet:", full_log[:500])
    else:
        print("⚠️ No JSON found in output.")
        print("Full Output snippet:", res.stdout[:500])
        
    if not errors:
        print("❌ Test Failed: No errors detected to fix.")
        sys.exit(1)
        
    # 5. Autofix
    print("6. Applying Autofix...")
    target_error = errors[0]
    # Check if correct error
    # gcc output: bad.c:1:22: error: expected ';' before '}' token
    if "expected ';'" in target_error["message"] and target_error["file"] == "bad.c":
        print(f"   Fixing '{target_error['message']}' at line {target_error['line']}")
        
        with open(BAD_FILE, "r") as f:
            lines = f.readlines()
        
        # Simple fix logic
        target_line_idx = target_error["line"]-1
        if 0 <= target_line_idx < len(lines):
            lines[target_line_idx] = lines[target_line_idx].replace("}", "; }")
            
            with open(BAD_FILE, "w") as f:
                f.writelines(lines)
            
            print("   File patched.")
        else:
             print("❌ Invalid line number.")
             sys.exit(1)
    else:
        print("❌ Unexpected error content:", target_error)
        sys.exit(1)
        
    # 6. Push Fix
    print("7. Pushing Fix...")
    run_projector(["push", "bad.c"])
    
    # 7. Verify
    print("8. Verifying Fix...")
    res = run_projector(["build", "--wait"])
    
    if "MISSION COMPLETE" in res.stdout or "Pipeline Complete" in res.stdout:
        print("✅ Autofix Successful! Build passed.")
        sys.exit(0)
    else:
        print("❌ Build still failing after fix.")
        print(res.stdout)
        sys.exit(1)

if __name__ == "__main__":
    test_autofix()
