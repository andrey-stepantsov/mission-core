import os
import sys
import json
import shutil

HOLOGRAM_DIR = "hologram"
OUTSIDE_WALL_DIR = "outside_wall"
CONFIG_FILE = ".hologram_config"

def load_config():
    current = os.path.abspath(os.getcwd())
    steps = 0
    while True:
        if steps > 30:
            print(f"Debug: Reached directory walk limit (30) at {current}", file=sys.stderr)
            break
        steps += 1
        
        candidate = os.path.join(current, CONFIG_FILE)
        if os.path.exists(candidate):
            with open(candidate, 'r') as f:
                config_data = json.load(f)
                # Avoid circular import by returning just dict or delaying RemoteHost import
                # The original code returned (config_data, RemoteHost(...))
                # To keep it clean, let's just return config_data and let caller instantiate RemoteHost
                # Or import RemoteHost inside.
                return config_data
        
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
        
    print("Warning: Hologram Config not found. Checking for Direct Mode...")
    return None

def save_config(config):
    # Always save to CWD or explicit root?
    # For now, save to CWD as that's usually init root
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def update_gitignore():
    """Ensures critical directories are ignored by git."""
    ignores = [".mission", ".mission-context", ".weaves", ".ddd", ".hologram_config", "outside_wall"]
    
    # Check .gitignore
    gitignore_path = ".gitignore"
    existing = set()
    
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            for line in f:
                existing.add(line.strip())
    
    missing = [i for i in ignores if i not in existing]
    
    if missing:
        print(f"Update: Adding {len(missing)} entries to .gitignore...")
        with open(gitignore_path, 'a') as f:
            if os.path.getsize(gitignore_path) > 0 and not open(gitignore_path).read().endswith("\n"):
                 f.write("\n")
            for m in missing:
                f.write(f"{m}\n")
    else:
        print("Git ignore verification: OK.")


def enforce_cursorrules():
    """Ensures the root .cursorrules is a symlink to the Mission Pack's rules."""
    # Logic:
    # 1. Find .mission/.cursorrules
    mission_rules = os.path.join(".mission", ".cursorrules")
    if not os.path.exists(mission_rules):
        # Fallback: try to find it relative to script if .mission is not in CWD
        # Since we are in a package now, this logic needs adjustment or reliance on CWD.
        pass
            
    # Assuming standard layout: CWD contains .mission
    target_link = ".cursorrules"
    
    if os.path.exists(mission_rules):
        print(f"Verifying {target_link} -> {mission_rules}...")
        
        # Check if it exists and is correct
        if os.path.exists(target_link):
            if os.path.islink(target_link):
                current_target = os.readlink(target_link)
                if current_target == mission_rules:
                    return # All good
                else:
                    print(f"Warning: {target_link} points to {current_target}, updating to {mission_rules}")
                    os.remove(target_link)
            else:
                # It's a real file.
                # Check if it was manually created.
                # We should back it up if it differs?
                # For now: Backup and overwrite with link.
                print(f"Warning: Replacing existing {target_link} with symlink to Mission Pack.")
                os.rename(target_link, f"{target_link}.bak")
        
        try:
            os.symlink(mission_rules, target_link)
            print(f"✅ Linked {target_link} -> {mission_rules}")
        except OSError as e:
            print(f"Warning: Failed to symlink .cursorrules: {e}")
            # Fallback: Copy
            try:
                shutil.copy2(mission_rules, target_link)
                print(f"   Copied instead.")
            except:
                pass
    else:
        # If .mission/.cursorrules doesn't exist, we can't enforce it.
        # But we should probably warn?
        pass

def find_project_root():
    current = os.path.abspath(os.getcwd())
    while True:
        if os.path.exists(os.path.join(current, CONFIG_FILE)):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None
