import os
import json

# Correct imports from package structure
from ..core.config import load_config, HOLOGRAM_DIR, OUTSIDE_WALL_DIR

def update_local_compile_db(context, dependencies=None):
    """Updates the unified local compile_commands.json with rewritten paths."""
    if not context:
        return

    config = load_config()
    remote_root = config.get('remote_root', '.')
    
    # Paths (Absolute Local)
    # We use os.getcwd() because hologram/outside_wall are in CWD where projector runs
    cwd = os.getcwd()
    hologram_abs = os.path.join(cwd, HOLOGRAM_DIR)
    outside_wall_abs = os.path.join(cwd, OUTSIDE_WALL_DIR)
    
    # 1. Rewrite Directory
    # context['directory'] is the remote build directory.
    # We map this to hologram structure.
    remote_dir = context.get('directory') or ''
    if remote_root and remote_dir.startswith(remote_root):
        rel_dir = os.path.relpath(remote_dir, remote_root)
        local_dir = os.path.join(hologram_abs, rel_dir)
    else:
        # If build dir is outside remote root (weird), fall back to hologram root
        local_dir = hologram_abs
        
    # 2. Rewrite File
    # context['file'] is remote absolute path
    remote_file = context.get('file') or ''
    if remote_root and remote_file.startswith(remote_root):
        rel_file = os.path.relpath(remote_file, remote_root)
        local_file = os.path.join(hologram_abs, rel_file)
    else:
        # If file is outside (e.g. system header?), we can't really edit it.
        # But auto_ghost usually targets files in repo.
        local_file = remote_file
        
    # 3. Rewrite Arguments
    # Rewrite -I /abs/path -> -I .../outside_wall/abs/path
    args = context.get('arguments')
    
    # Fallback: if 'arguments' is missing, parse 'command' string
    if not args:
        cmd_str = context.get('command') or context.get('cmd_str')
        if cmd_str:
            import shlex
            # On remote linux, arguments might be quoted, shlex.split should handle it
            args = shlex.split(cmd_str)
            
    args = args or []
    new_args = []
    
    i = 0
    while i < len(args):
        arg = args[i]
        
        # Handle -I /path
        if arg.startswith("-I") or arg.startswith("-L") or arg == "-isystem":
            # Check if it's a flag + value or separated
            flag = arg
            value = None
            consumed_next = False
            
            if arg == "-isystem":
                 if i + 1 < len(args):
                    value = args[i+1]
                    consumed_next = True
            elif len(arg) > 2:
                # -I/path
                flag = arg[:2]
                value = arg[2:]
            else:
                # -I /path
                 if i + 1 < len(args):
                    value = args[i+1]
                    consumed_next = True
            
            if value and value.startswith("/"):
                # Rewrite to outside_wall
                # /opt/foo -> .../outside_wall/opt/foo
                mapped_path = os.path.join(outside_wall_abs, value.lstrip("/"))
                
                # Check if we should enforce mapping or keep original?
                # Ideal: if exists locally, map it.
                if os.path.exists(mapped_path):
                     value = mapped_path
                else:
                     pass
                
                if consumed_next:
                    new_args.append(flag)
                    new_args.append(mapped_path)
                    i += 2
                else:
                    new_args.append(f"{flag}{mapped_path}")
                    i += 1
                continue
                
        new_args.append(arg)
        i += 1
        
    # 3b. Inject Dependency Includes
    if dependencies:
        include_dirs = set()
        system_dirs = set()
        
        for dep in dependencies:
            if not dep.startswith("/"):
                continue
                
            # Map to outside_wall
            rel_dep = dep.lstrip("/")
            local_dep = os.path.join(outside_wall_abs, rel_dep)
            local_dep_dir = os.path.dirname(local_dep)
            
            # Heuristic: /usr, /opt, /lib are likely system
            if dep.startswith("/usr") or dep.startswith("/opt") or dep.startswith("/lib"):
                system_dirs.add(local_dep_dir)
            else:
                include_dirs.add(local_dep_dir)
                
        # Append new flags
        for d in sorted(list(include_dirs)):
            new_args.append(f"-I{d}")
            
        for d in sorted(list(system_dirs)):
            new_args.append(f"-isystem")
            new_args.append(d)

    # 4. Inject Missing System Headers (Global Config)
    system_includes = config.get("system_includes", [])
    if system_includes:
        existing_paths = set()
        # Scan current new_args for existing -isystem paths to avoid dupes
        for i in range(len(new_args)):
             if new_args[i] == "-isystem" and i+1 < len(new_args):
                  existing_paths.add(new_args[i+1])
             elif new_args[i].startswith("-isystem"):
                  existing_paths.add(new_args[i][8:])
                  
        for sys_inc in system_includes:
             # Rewrite to outside_wall
             mapped = os.path.join(outside_wall_abs, sys_inc.lstrip("/"))
             if mapped not in existing_paths:
                  new_args.append("-isystem")
                  new_args.append(mapped)
        
    entry = {
        "directory": local_dir,
        "file": local_file,
        "arguments": new_args
    }
    
    # 4. Upsert into compile_commands.json
    db_path = os.path.join(hologram_abs, "compile_commands.json")
    db = []
    if os.path.exists(db_path):
        try:
            with open(db_path, 'r') as f:
                db = json.load(f)
        except:
             pass
             
    # Remove existing entry for this file
    db = [e for e in db if e.get("file") != local_file]
    db.append(entry)
    
    with open(db_path, 'w') as f:
        json.dump(db, f, indent=2)
        
    print(f"Updated compile_commands.json for {os.path.basename(local_file)}")
    
    # 5. Check System Headers Status (Verification)
    # We check if we have any -isystem flags in new_args
    has_system_headers = any(a == "-isystem" or a.startswith("-isystem") for a in new_args)
    
    if not has_system_headers and not config.get("system_includes"):
        print("⚠️  Warning: System headers not synced (missing in config).")
        print("   IntelliSense may be incomplete (e.g. <stdio.h>).")
        print("   Run 'projector repair-headers' to fix.")
        
    elif has_system_headers:
        # Verify they actually exist
        missing_sys = []
        for i in range(len(new_args)):
             val = None
             if new_args[i] == "-isystem" and i+1 < len(new_args):
                  val = new_args[i+1]
             elif new_args[i].startswith("-isystem"):
                  val = new_args[i][8:]
             
             if val and val.startswith(outside_wall_abs) and not os.path.exists(val):
                  missing_sys.append(val)
                  
        if missing_sys:
             print(f"⚠️  Warning: {len(missing_sys)} system header paths are missing locally.")
             print("   Run 'projector repair-headers' to re-sync.")
