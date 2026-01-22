import os
import sys
import shutil
import json
from ..core.config import HOLOGRAM_DIR, OUTSIDE_WALL_DIR, CONFIG_FILE, save_config, update_gitignore, enforce_cursorrules, load_config
from ..core.transport import RemoteHost

def do_init(args):
    """Initializes the hologram environment."""
    host_target = args.host_target
    
    # Support user@host:path syntax
    if ":" in host_target:
        parts = host_target.split(":", 1)
        host_target = parts[0]
        # Only override remote_root if not explicitly provided
        if not args.remote_root or args.remote_root == ".":
            remote_root = parts[1]
        else:
            remote_root = args.remote_root
    else:
        remote_root = args.remote_root
        
    remote_root = remote_root.rstrip("/") if remote_root else "."
    
    print(f"Initializing Hologram for host: {host_target} (Root: {remote_root})")
    
    os.makedirs(HOLOGRAM_DIR, exist_ok=True)
    os.makedirs(OUTSIDE_WALL_DIR, exist_ok=True)
    os.makedirs(".mission-context", exist_ok=True)
    
    config = {
        "host_target": host_target,
        "remote_root": remote_root
    }
    
    if args.remote_mission_root:
        config["remote_mission_root"] = args.remote_mission_root
        
    save_config(config)
    
    # 3b. Enforce Git Ignore
    update_gitignore()
    
    # 3c. Enforce Mission Rules
    enforce_cursorrules()
    
    print("Hologram initialized.")
    
    # 4. Launch The Tower (Observability)
    print("Launching The Tower (Remote Watcher)...")
    
    # Use explicit remote root to find launch_tower
    # Check for remote_mission_root
    # We reload config or use current dict.
    # Just use dictionary logic from 'config' variable
    remote_mission_root = config.get("remote_mission_root")
    if remote_mission_root:
         mission_root = remote_mission_root
    else:
         mission_root = f"{remote_root}/.mission"

    remote = RemoteHost(host_target, transport=args.transport)
    
    # 0. Remote Bootstrap (If SSH)
    if remote.transport == 'ssh':
        print(f"🌍 Verifying Mission Pack on remote {host_target}...")
        try:
            # Check if .mission exists
            remote.run(f"test -d {mission_root}")
            print("   Mission Pack found on remote.")
        except:
            print("   Mission Pack not found. Bootstrapping...")
            # Clone it
            # Using -c http.sslVerify=false to support simulation/self-signed certs
            repo = "https://github.com/andrey-stepantsov/mission-core.git"
            cmd = f"git clone -c http.sslVerify=false {repo} {mission_root}"
            try:
                remote.run(cmd)
                print("   ✅ Bootstrapped Mission Core on remote.")
                
            except Exception as e:
                print(f"❌ Failed to bootstrap remote: {e}")
                print("   Please install manually or check connectivity.")
                sys.exit(1)

    if remote.transport == 'ssh':
        print("🚀 Launching The Tower (Remote Watcher)...")
        tower_script = f"{remote_mission_root}/tools/bin/launch_tower" if remote_mission_root else f"{mission_root}/tools/bin/launch_tower"
        
        # NOTE: Logic above set `mission_root` correctly regardless of remote_mission_root setting.
        # But `tower_script` needs full path.
        tower_script = f"{mission_root}/tools/bin/launch_tower"

        cmd = f"if [ -f {tower_script} ]; then {tower_script}; else echo 'Tower script not found at {tower_script}'; fi"
        
        try:
            remote.run(cmd)
            print("   Tower signal sent.")
        except Exception as e:
            print(f"⚠️  Failed to launch Tower: {e}")
            print("   You may need to run run it manually on the host.")
    else:
        print("Skipping Tower launch (Local Mode).")

    # 5. Deploy VSCode Configuration
    deploy_vscode_config(remote_root)
    
    # 6. Verify System Headers (Proactive Suggestion)
    sys_includes = config.get("system_includes", [])
    if not sys_includes:
        print("\n⚠️  Suggestion: Run 'projector repair-headers' to enable full IntelliSense.")
        print("   This syncs system headers (e.g. stdio.h) which are missing by default.")

def deploy_vscode_config(remote_root, template_dir=None):
    """Deploys VSCode configuration templates if they exist."""
    print("Deploying VSCode configuration...")
    
    if not template_dir:
        # We are in tools/projector/commands/init.py
        # root/.mission (usually)
        # ../../../ = tools
        # ../../../../ = .mission or base
        
        # Let's rely on CWD or relative to this file
        # tools/projector/commands/init.py
        # -> tools/projector/commands
        # -> tools/projector
        # -> tools
        # -> .mission or base
        
        # It's unreliable to guess "mission root" relative to installed package if it's installed via pip somewhere else.
        # But for this task, the code lives in .mission/tools/projector
        
        current_dir = os.path.dirname(os.path.realpath(__file__))
        mission_dir = os.path.abspath(os.path.join(current_dir, "../../../")) 
        # But wait, if this is installed code, who knows.
        
        # Strategy: Checks for templates in CWD/.mission/templates
        # Or look for them relative to the code location.
        
        # 1. Check relative to code
        code_template_src = os.path.join(mission_dir, "templates", "vscode")
        
        # 2. Check CWD/.mission
        cwd_template_src = os.path.join(os.getcwd(), ".mission", "templates", "vscode")
        
        if os.path.exists(code_template_src):
             template_src = code_template_src
        elif os.path.exists(cwd_template_src):
             template_src = cwd_template_src
        else:
             template_src = None
    else:
        template_src = template_dir
        
    if template_src and os.path.exists(template_src):
        target_vscode = os.path.join(os.getcwd(), ".vscode")
        os.makedirs(target_vscode, exist_ok=True)
        
        for item in os.listdir(template_src):
            s = os.path.join(template_src, item)
            d = os.path.join(target_vscode, item)
            if os.path.isfile(s):
                if not os.path.exists(d):
                    shutil.copy2(s, d)
                    print(f"  Created {item}")
                else:
                    # Smart Merge for JSON files
                    if item.endswith(".json"):
                        try:
                            with open(s, 'r') as f_src:
                                template_data = json.load(f_src)
                            
                            try:
                                with open(d, 'r') as f_dst:
                                    existing_data = json.load(f_dst)
                            except json.JSONDecodeError:
                                print(f"  Warning: Existing {item} is invalid JSON. Backing up and overwriting.")
                                shutil.copy2(d, d + ".bak")
                                shutil.copy2(s, d)
                                continue

                            merged = False
                            
                            if item == "settings.json":
                                tmpl_args = template_data.get("clangd.arguments", [])
                                exist_args = existing_data.get("clangd.arguments", [])
                                
                                for k, v in template_data.items():
                                    if k not in existing_data:
                                        existing_data[k] = v
                                        merged = True
                                        
                                if "clangd.arguments" in template_data:
                                    current_set = set(exist_args)
                                    for arg in tmpl_args:
                                        if arg not in current_set:
                                            exist_args.append(arg)
                                            merged = True
                                    existing_data["clangd.arguments"] = exist_args
                                    
                            elif item == "c_cpp_properties.json":
                                tmpl_configs = template_data.get("configurations", [])
                                exist_configs = existing_data.get("configurations", [])
                                
                                exist_names = {c.get("name") for c in exist_configs}
                                for cfg in tmpl_configs:
                                    if cfg.get("name") not in exist_names:
                                        exist_configs.insert(0, cfg) # Prepend
                                        merged = True
                                existing_data["configurations"] = exist_configs
                                
                            else:
                                for k, v in template_data.items():
                                    if k not in existing_data:
                                        existing_data[k] = v
                                        merged = True
                                        
                            if merged:
                                with open(d, 'w') as f_dst:
                                    json.dump(existing_data, f_dst, indent=4)
                                print(f"  Merged configuration into {item}")
                            else:
                                print(f"  Skipped {item} (already up to date)")
                                
                        except Exception as e:
                            print(f"  Warning: Failed to merge {item}: {e}")
                    else:
                        print(f"  Skipped {item} (already exists)")
    else:
        print("  Warning: VSCode templates not found.")
