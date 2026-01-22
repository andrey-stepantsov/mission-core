import os
import sys
import subprocess
from ..core.config import load_config, HOLOGRAM_DIR, OUTSIDE_WALL_DIR, find_project_root, save_config
from ..internal.compile_db import update_local_compile_db

def do_grep(args):
    """Executes remote ripgrep and maps paths to local hologram."""
    config = load_config()
    host = config['host_target']
    remote_root = config.get('remote_root', '.')
    
    pattern = args.pattern
    search_path = args.path
    
    # Resolve Remote Search Path
    if search_path:
        abs_search = os.path.abspath(search_path)
        project_root = find_project_root()
        hologram_abs = os.path.join(project_root, HOLOGRAM_DIR)
        
        # Check if inside hologram
        if abs_search.startswith(hologram_abs):
            rel = os.path.relpath(abs_search, hologram_abs)
            remote_search_path = os.path.join(remote_root, rel)
        else:
            if search_path.startswith("/"):
                remote_search_path = search_path
            else:
                remote_search_path = os.path.join(remote_root, search_path)
    else:
        remote_search_path = remote_root

    cmd_str = f"unset HISTFILE; rg --line-number --with-filename --no-heading --color=always {pattern} {remote_search_path}"
    
    ssh_opts = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]
    cmd = ["ssh"] + ssh_opts + [host, cmd_str]
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        
        hologram_cwd = os.path.join(find_project_root(), HOLOGRAM_DIR)
        
        while True:
            line = process.stdout.readline()
            if not line:
                break
            
            decoded_line = line
            
            if remote_root in decoded_line:
                new_line = decoded_line.replace(remote_root, hologram_cwd, 1) 
                print(new_line, end='')
            else:
                print(decoded_line, end='')

        process.wait()
        if process.returncode != 0 and process.returncode != 1: 
             err = process.stderr.read()
             if "command not found" in err:
                 print("Error: 'rg' (ripgrep) not found on remote host.")
             elif err:
                 print(err, end='')
                 
    except Exception as e:
        print(f"Error executing grep: {e}")

def do_repair_headers(args):
    """Syncs system headers from the remote host."""
    config = load_config()
    host = config['host_target']
    remote_root = config.get('remote_root', '.')
    
    print("🚑  Repairing System Headers...")
    
    remote_mission_root = config.get('remote_mission_root')
    if remote_mission_root:
         sys_headers_bin = f"{remote_mission_root}/tools/lib/sys_headers.py"
    else:
         sys_headers_bin = f"{remote_root}/.mission/tools/lib/sys_headers.py"
         
    cmd = f"chmod +x {sys_headers_bin} && {sys_headers_bin}"
    ssh_opts = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]
    
    try:
        print("   Querying remote compiler for default includes...")
        full_cmd = ["ssh"] + ssh_opts + [host, f"unset HISTFILE; {cmd}"]
        
        result = subprocess.run(full_cmd, 
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            print(f"Error querying headers: {result.stderr}")
            sys.exit(1)
            
        includes = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        
        if not includes:
            print("Warning: No system includes found. Check if proper compiler is installed on remote.")
            print("         (e.g. gcc/g++ or clang)")
            return

        print(f"   Found {len(includes)} system include paths.")
        print(f"   Syncing {len(includes)} paths (recursive)...")
        
        for inc in includes:
             print(f"     - {inc}")
             rsync_cmd = [
                "rsync", "-azR", 
                "-e", "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null",
                f"{host}:{inc}", 
                OUTSIDE_WALL_DIR
             ]
             try:
                 subprocess.run(rsync_cmd, check=True, stderr=subprocess.PIPE)
             except subprocess.CalledProcessError as e:
                 print(f"       Warning: Failed to sync {inc}: {e}")
                 print(f"                (Is it a valid directory on remote?)")
        
        config["system_includes"] = includes
        save_config(config)
        
        print("   Updating compilation database...")
        update_local_compile_db({})
        
        print("✅  System headers repaired and synced.")
        
    except Exception as e:
        print(f"Repair failed: {e}")
        sys.exit(1)
