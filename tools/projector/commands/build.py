import os
import sys
import json
import time
import subprocess
import threading

from ..core.config import load_config, HOLOGRAM_DIR, find_project_root, save_config
from ..core.transport import run_command
from ..internal.monitor import monitor_build

def find_build_context(hologram_root, start_path):
    """
    Finds the nearest build context (directory with Makefile or compile_commands.json)
    starting from start_path and walking up to hologram_root.
    Returns relative path from hologram_root, or None if no specific context found (root).
    """
    current = os.path.abspath(start_path)
    root = os.path.abspath(hologram_root)
    
    if not current.startswith(root):
        return None
        
    while True:
        # Check markers
        if os.path.exists(os.path.join(current, "Makefile")) or \
           os.path.exists(os.path.join(current, "compile_commands.json")) or \
           os.path.exists(os.path.join(current, ".ddd")):
            if current == root:
                return None # Root is default, no special context needed
            return os.path.relpath(current, root)
            
        parent = os.path.dirname(current)
        if not parent.startswith(root) or parent == current:
            break
        current = parent
        
    return None

def trigger_build(config, context_rel_path=None):
    """
    Triggers the remote build via DDD.
    Manages context switching by restarting the remote daemon if the context has changed.
    """
    host = config['host_target']
    remote_root = config.get('remote_root', '.')
    
    ssh_opts = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]

    # Calculate Target Root
    if context_rel_path:
        remote_root_rel = remote_root.lstrip(os.path.sep)
        if context_rel_path.startswith(remote_root_rel):
             target_root = f"/{context_rel_path}".replace(os.path.sep, "/")
        else:
             target_root = f"{remote_root}/{context_rel_path}".replace(os.path.sep, "/")
    else:
        target_root = remote_root

    # Context State Management
    last_context = config.get('last_context')
    
    # Check if we need to restart
    if last_context != target_root:
        print(f"🔄 Context Switch Detected: {last_context} -> {target_root}")
        print("   Restarting Remote Daemon...")
        
        try:
             run_command(["ssh"] + ssh_opts + [host, "unset HISTFILE; tmux kill-session -t mission_tower"], capture_stderr=False)
        except Exception:
             pass 

        # 2. Launch with new PROJECT_ROOT
        remote_mission_root = config.get('remote_mission_root')
        if remote_mission_root:
             mission_root = remote_mission_root
        else:
             mission_root = f"{remote_root}/.mission"
             
        launch_script = f"{mission_root}/tools/bin/launch_tower"
        cmd = f"unset HISTFILE; export PROJECT_ROOT='{target_root}'; {launch_script}"
        
        print(f"   Running: {cmd}")
        try:
             run_command(["ssh"] + ssh_opts + [host, cmd])
        except Exception as e:
             print(f"Error launching tower: {e}")
        
        config['last_context'] = target_root
        save_config(config)
        
        time.sleep(1)

    # 3. Trigger
    build_req = f"{target_root}/.ddd/run/build.request"
    
    print(f"Triggering remote build at {build_req}...")
    
    req_dir = os.path.dirname(build_req)
    try:
         run_command(["ssh"] + ssh_opts + [host, f"unset HISTFILE; mkdir -p {req_dir}"])
    except Exception:
         pass

    run_command(["ssh"] + ssh_opts + [host, f"unset HISTFILE; rm -f {build_req} && touch {build_req}"])

def do_build(args):
    """Explicitly triggers the remote build."""
    config = load_config()
    
    project_root = find_project_root()
    if not project_root:
        print("Error: Could not find project root (.hologram_config).")
        sys.exit(1)
        
    hologram_abs = os.path.join(project_root, HOLOGRAM_DIR)
    
    # Determine Context
    if hasattr(args, 'context_from') and args.context_from:
        start_path = os.path.dirname(os.path.abspath(args.context_from))
        print(f"Build Context Derived from: {args.context_from}")
    elif hasattr(args, 'sync') and args.sync:
        start_path = os.path.dirname(os.path.abspath(args.sync))
        print(f"Build Context Derived from: {args.sync}")
    else:
        start_path = os.getcwd()

    # Pre-Build Sync
    if hasattr(args, 'sync') and args.sync:
        print(f"🔄 Syncing {args.sync} before build...")
        from .sync import do_push
        class PushArgs:
            file = args.sync
        try:
            do_push(PushArgs, trigger=False)
        except Exception as e:
            print(f"⚠️ Warning: Sync failed: {e}")

    context_path = find_build_context(hologram_abs, start_path)
    
    trigger_build(config, context_path)
    print("✅ Build triggered.")
    
    if hasattr(args, 'wait') and args.wait:
        print("⏳ Waiting for build to complete...")
        config_reloaded = load_config()
        remote_root = config.get('remote_root', '.')
        target_root = config_reloaded.get('last_context', remote_root)
        remote_log = f"{target_root}/.ddd/run/build.log"
        
        exit_code = monitor_build(config['host_target'], remote_log, stop_on_finish=True)
        sys.exit(exit_code)

def do_log(args):
    """Fetches the latest build log from the remote host."""
    config = load_config()
    host = config['host_target']
    remote_root = config.get('remote_root', '.')
    
    target_root = config.get('last_context', remote_root)
    remote_log = f"{target_root}/.ddd/run/build.log"
    
    ssh_opts = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]
    
    if args.lines:
        cmd_str = f"unset HISTFILE; tail -n {args.lines} {remote_log} 2>/dev/null"
        cmd = ["ssh"] + ssh_opts + [host, cmd_str]
    else:
        cmd_str = f"unset HISTFILE; cat {remote_log} 2>/dev/null"
        cmd = ["ssh"] + ssh_opts + [host, cmd_str]
        
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"Error: Could not retrieve log from {host}:{remote_log}")
            sys.exit(1)
            
        print(result.stdout, end='') 
    except Exception as e:
        print(f"Error fetching log: {e}")
        sys.exit(1)

def do_listen(args):
    """Listens to the Mission Radio (remote build logs)."""
    config = load_config()
    host = config['host_target']
    remote_root = config.get('remote_root', '.')
    target_root = config.get('last_context', remote_root)
    remote_log = f"{target_root}/.ddd/run/build.log"
    
    mirror_log = args.mirror_log if hasattr(args, 'mirror_log') else None
    
    monitor_build(host, remote_log, stop_on_finish=False, mirror_log=mirror_log)

def do_live(args):
    """Reflex + Impulse + Synthesis: Live Mode"""
    print("🧠 The Synapse is active. (Live Mode)")
    print("👂 Connecting to The Radio...")

    mirror_path = os.path.join(HOLOGRAM_DIR, ".ddd", "run", "build.log")
    os.makedirs(os.path.dirname(mirror_path), exist_ok=True)
    args.mirror_log = mirror_path
    
    print(f"🪞 Mirroring logs to {mirror_path}")

    radio_thread = threading.Thread(target=do_listen, args=(args,), daemon=True)
    radio_thread.start()
    
    print("👁️  Watching hologram for changes...")
    
    poll_interval = 1.0 
    debounce_delay = 0.5
    
    last_mtimes = {}
    pending_changes = set()
    
    if os.path.exists(HOLOGRAM_DIR):
        for root, dirs, files in os.walk(HOLOGRAM_DIR):
            for f in files:
                path = os.path.join(root, f)
                try:
                    last_mtimes[path] = os.path.getmtime(path)
                except OSError:
                    pass
    else:
        print(f"Warning: {HOLOGRAM_DIR} does not exist. Please run 'projector init' first.")
                
    try:
        from .sync import do_push
        while True:
            time.sleep(poll_interval)
            
            # Scan for changes
            current_changes = set()
            if os.path.exists(HOLOGRAM_DIR):
                for root, dirs, files in os.walk(HOLOGRAM_DIR):
                    for f in files:
                        path = os.path.join(root, f)
                        try:
                            mtime = os.path.getmtime(path)
                            if path not in last_mtimes:
                                last_mtimes[path] = mtime
                                current_changes.add(path)
                            elif mtime > last_mtimes[path]:
                                last_mtimes[path] = mtime
                                current_changes.add(path)
                        except OSError:
                            pass
            
            if current_changes:
                pending_changes.update(current_changes)
                print(f"⚡ Reflex: Detected {len(current_changes)} changes. Debouncing...")
                time.sleep(debounce_delay)
                
                files_to_push = list(pending_changes)
                pending_changes.clear()
                
                first_file = None
                
                for f_path in files_to_push:
                    if os.path.exists(f_path): 
                        if not first_file: first_file = f_path
                        print(f"🌊 Impulse: Pushing {f_path}...")
                        class PushArgs:
                            file = f_path
                        
                        try:
                            do_push(PushArgs(), trigger=False)
                        except SystemExit:
                            print(f"⚠️ Push failed for {f_path}")
                        except Exception as e:
                            print(f"⚠️ Error pushing {f_path}: {e}")
                            
                if args.auto_build and first_file:
                    print("Triggering remote build for batch...")
                    hologram_abs = os.path.abspath(HOLOGRAM_DIR)
                    context_path = find_build_context(hologram_abs, os.path.dirname(first_file))
                    trigger_build(load_config(), context_path)
                    print("✨ Synced & Triggered.")
                else:
                    print("✨ Synced (Use 'projector build' or run with --auto-build to trigger).")

    except KeyboardInterrupt:
        print("\n🔌 Disconnecting Synapse.")
        sys.exit(0)

def do_context(args):
    """
    Displays the compilation context for a file in a structured format for AI agents.
    Read from local compile_commands.json.
    """
    config = load_config()
    
    if config:
        print(f"🔮 Projector: Hologram Mode active.", file=sys.stderr)
        
        if not args.file:
             print("Usage: projector context <file> [task]")
             sys.exit(1)

        project_root = find_project_root() 
        if not project_root: project_root = os.getcwd() 
        
        hologram_dir = os.path.join(project_root, HOLOGRAM_DIR)
        compile_commands_path = os.path.join(hologram_dir, "compile_commands.json")

    else:
        print(f"🧠 Projector: Direct Mode active (no hologram config).", file=sys.stderr)
        project_root = os.getcwd()
        compile_commands_path = os.path.join(project_root, "compile_commands.json")
        
        if not os.path.exists(compile_commands_path):
             print(f"Error: Hologram not initialized AND compile_commands.json not found in {project_root}")
             sys.exit(1)

    if not os.path.exists(compile_commands_path):
        print(f"Error: {compile_commands_path} not found.") 
        if config: print("Tip: Run 'projector pull' to sync context.")
        sys.exit(1)
        
    target_path = os.path.abspath(args.file) 
    
    try:
        print(f"📄 Loading compilation database: {compile_commands_path} ...", file=sys.stderr)
        with open(compile_commands_path, 'r') as f:
            db = json.load(f)
        print(f"   Loaded {len(db)} compilation entries.", file=sys.stderr)
    except Exception as e:
        print(f"Error parsing compile_commands.json: {e}")
        sys.exit(1)
        
    entry = next((e for e in db if e.get("file") == target_path), None)
    
    if not entry:
        print(f"Error: No compilation context found for {args.file}")
        print("Tip: Run 'projector pull' to sync context.")
        sys.exit(1)
        
    import shlex
    cmd_args = []
    if "arguments" in entry:
        cmd_args = entry["arguments"]
    elif "command" in entry:
        cmd_args = shlex.split(entry["command"])
        
    macros = []
    includes = []
    standard = None
    
    i = 0
    while i < len(cmd_args):
        arg = cmd_args[i]
        
        if arg.startswith("-D"):
            macros.append(arg[2:])
            
        elif arg.startswith("-std="):
            standard = arg[5:]
            
        elif arg.startswith("-I"):
            val = arg[2:]
            if not val and i + 1 < len(cmd_args):
                val = cmd_args[i+1]
            if val: includes.append(val)
        elif arg == "-isystem":
            if i + 1 < len(cmd_args):
                includes.append(cmd_args[i+1])
        
        i += 1
        
    print(f"# Mission Request")
    if hasattr(args, 'task') and args.task:
        print(f"{args.task}\n")
    else:
        print("No specific task description provided.\n")
        
    print("# Compilation Context")
    print(f"**Target File**: `{os.path.relpath(target_path, project_root)}`")
    if standard:
        print(f"**Standard**: `{standard}`")
    
    print("\n## Macros")
    if macros:
        for m in sorted(macros):
            print(f"- `{m}`")
    else:
        print("(None)")
        
    print("\n## Includes")
    if includes:
        for inc in includes:
            if inc.startswith(project_root):
                rel = os.path.relpath(inc, project_root)
                print(f"- `{rel}`")
            else:
                print(f"- `{inc}`")
    else:
        print("(None)")
        
    print("\n# Source Code")
    try:
        ext = os.path.splitext(target_path)[1].lower()
        if ext in ['.c', '.h']:
            lang = "c"
        elif ext in ['.cpp', '.hpp', '.cc', '.hh', '.cxx']:
            lang = "cpp"
        else:
            lang = ""
            
        with open(target_path, 'r') as f:
            content = f.read()
            
        print(f"```{lang}")
        print(content)
        print("```")
    except Exception as e:
        print(f"Error reading source file: {e}")

def do_focus(args):
    """
    Generates a dynamic .clangd configuration derived from a source file's compilation flags.
    """
    project_root = find_project_root()
    if not project_root:
        print("Error: Hologram not initialized.")
        sys.exit(1)
        
    hologram_dir = os.path.join(project_root, HOLOGRAM_DIR)
    db_path = os.path.join(hologram_dir, "compile_commands.json")
    
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found. Run 'projector pull' first.")
        sys.exit(1)
        
    target_path = os.path.abspath(args.file)
    
    try:
        with open(db_path, 'r') as f:
            db = json.load(f)
    except Exception as e:
        print(f"Error parsing compile_commands.json: {e}")
        sys.exit(1)
        
    entry = next((e for e in db if e.get("file") == target_path), None)
    
    if not entry:
        print(f"Error: No compilation context found for {args.file}")
        print("Make sure this source file has been pulled via 'projector pull'.")
        sys.exit(1)
        
    print(f"Found context for {args.file}")
    
    import shlex
    cmd_args = []
    if "arguments" in entry:
        cmd_args = entry["arguments"]
    elif "command" in entry:
        cmd_args = shlex.split(entry["command"])
        
    compile_flags = []
    
    i = 0
    while i < len(cmd_args):
        arg = cmd_args[i]
        
        if i == 0 and not arg.startswith("-"):
             i += 1
             continue
             
        if arg == "-o":
            i += 2 
            continue
            
        if arg == "-c":
            i += 1
            continue
            
        compile_flags.append(arg)
        i += 1
        
    compile_flags = [f for f in compile_flags if not f.endswith(".c") and not f.endswith(".cpp") and not f.endswith(".cc")]
    
    clangd_content = "CompileFlags:\n  Add:\n"
    for flag in compile_flags:
        safe_flag = flag.replace('"', '\\"')
        clangd_content += f'    - "{safe_flag}"\n'
        
    clangd_path = os.path.join(hologram_dir, ".clangd")
    
    try:
        with open(clangd_path, 'w') as f:
            f.write(clangd_content)
        print(f"✅ Generated .clangd configuration at {clangd_path}")
        print(f"   (Derived {len(compile_flags)} flags from {os.path.basename(target_path)})")
    except Exception as e:
        print(f"Error writing .clangd: {e}")
        sys.exit(1)
