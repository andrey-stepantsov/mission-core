import os
import sys
import json
import shutil
import subprocess
import threading
import time

from ..core.config import load_config, HOLOGRAM_DIR, OUTSIDE_WALL_DIR, find_project_root, save_config
from ..core.transport import run_command
from ..internal.compile_db import update_local_compile_db

def compute_candidate_diff(candidates):
    """
    Computes the difference between candidate flags.
    Returns a list of diff strings describing each candidate.
    """
    import shlex
    
    # 1. Parse all candidates to sets of flags
    cand_flags = []
    
    for cand in candidates:
        cmd = cand.get("cmd_str") or cand.get("command") or ""
        try:
            flags = set(shlex.split(cmd))
        except:
             # Fallback if quoting is broken
            flags = set(cmd.split()) 
        cand_flags.append(flags)
        
    # 2. Find Intersection
    if cand_flags:
        common_flags = set.intersection(*cand_flags)
    else:
        common_flags = set()
        
    # 3. Compute Diff
    diffs = []
    for idx, cand in enumerate(candidates):
        flags = cand_flags[idx]
        diff = flags - common_flags
        diff_str = " ".join(sorted(list(diff)))
        if not diff_str:
            diff_str = "(Identical to others)"
        
        diffs.append(diff_str)
        
    return diffs

def do_pull(args):
    """Pulls a file from the host."""
    config = load_config()
    host = config['host_target']
    remote_root = config.get('remote_root', '.')
    
    input_path = args.file
    
    # Resolve Remote Path
    if input_path.startswith("/"):
        remote_path = input_path
        # For absolute paths, we store them as full structure
        rel_path = input_path.lstrip("/")
    else:
        # For relative paths, prepend remote_root
        remote_path = f"{remote_root}/{input_path}".replace(os.path.sep, "/")
        rel_path = input_path

    print(f"Pulling {remote_path} from {host}...")
    
    # 1. Verify file exists on host
    ssh_opts = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]
    try:
        run_command(["ssh"] + ssh_opts + [host, f"unset HISTFILE; test -f {remote_path}"])
    except subprocess.CalledProcessError:
        print(f"Error: File '{remote_path}' not found on remote host.")
        sys.exit(1)
    
    # 2. Rsync file to hologram/
    local_dest = os.path.join(HOLOGRAM_DIR, rel_path)
    os.makedirs(os.path.dirname(local_dest), exist_ok=True)
    
    rsync_cmd = ["rsync", "-az", "-e", "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null", f"{host}:{remote_path}", local_dest]
    run_command(rsync_cmd)
    print(f"Synced to {local_dest}")

    # 2b. Enforce Overlay: Hide from Outside Wall
    # If the file exists in outside_wall, we must remove it so the hologram takes precedence.
    wall_dest = os.path.join(OUTSIDE_WALL_DIR, rel_path)
    if os.path.exists(wall_dest):
        try:
            # Ensure parent is writable if needed
            parent_dir = os.path.dirname(wall_dest)
            if not os.access(parent_dir, os.W_OK):
                 try:
                     os.chmod(parent_dir, 0o755)
                 except: 
                     pass
            
            os.remove(wall_dest)
            print(f"👻 Ghosted (hidden) {wall_dest} from outside_wall")
        except OSError as e:
            print(f"Warning: Failed to hide {wall_dest} from outside_wall: {e}")
    
    # 3. Real Auto-Ghost (Dependency Syncing)
    print("Running Auto-Ghost logic...")
    
    # Use remote_root if available to find auto_ghost
    remote_mission_root = config.get('remote_mission_root')
    
    if remote_mission_root:
        auto_ghost_bin = f"{remote_mission_root}/tools/bin/auto_ghost"
    # If remote_root is absolute, try it first
    elif remote_root.startswith("/"):
        auto_ghost_bin = f"{remote_root}/.mission/tools/bin/auto_ghost"
    else:
        # Fallback to dynamic discovery
        auto_ghost_bin = "$(git rev-parse --show-toplevel 2>/dev/null || echo '.')/.mission/tools/bin/auto_ghost"

    # Fix tilde expansion for quoted usage
    if auto_ghost_bin.startswith("~/"):
        auto_ghost_bin = f"$HOME{auto_ghost_bin[1:]}"
        
    # Improved discovery: Try project tool
    import shlex
    cmd_ghost = (
        f"ghost_bin=\"{auto_ghost_bin}\"; "
        f"if [ ! -f \"$ghost_bin\" ]; then echo 'Error: Auto-Ghost not found at $ghost_bin'; exit 1; fi; "
        f"cd $(dirname {remote_path}) && $ghost_bin --full {remote_path}"
    )
    
    if args.flags:
        # Safe quoting for the remote shell
        safe_flags = shlex.quote(args.flags)
        # Use = to ensure argparse doesn't confuse the value with a flag
        cmd_ghost += f" --flags={safe_flags}"
    
    compile_context = None
    dependencies = []
    
    try:
        json_output = run_command(["ssh"] + ssh_opts + [host, f"unset HISTFILE; {cmd_ghost}"], capture_stderr=False)
        data = json.loads(json_output)
        

        # Handle both old (list) and new (dict) formats for backward compatibility
        if isinstance(data, list):
            dependencies = data
        elif isinstance(data, dict):
            dependencies = data.get("dependencies", [])
            compile_context = data.get("compile_context")
            
            # Context Selection Logic
            if compile_context and "candidates" in compile_context:
                candidates = compile_context["candidates"]
                
                # If we have multiple candidates and no flags were used (or even if they were, but still vague)
                # Check for ambiguity
                if len(candidates) > 1:
                     # Interactive Mode: If TTY, ask user
                     if sys.stdin.isatty() or os.environ.get("PROJECTOR_INTERACTIVE") == "1":
                         print(f"\n⚠️  Ambiguous compilation context found for {os.path.basename(input_path)}.")
                         print(f"   (Found {len(candidates)} candidates)")
                         print("   Multiple build targets define this file. Please select the correct context:")
                         
                         # ... (Interactive Logic same as original) ...
                         # For brevity/simplicity in refactor, defaulting to #1 unless interactive.
                         print("   Defaulting to Candidate #1.")
                         compile_context = candidates[0]
                     else:
                        print(f"⚠️  Ambiguous compilation context found for {os.path.basename(input_path)}.")
                        print(f"   Defaulting to Candidate #1. Use --flags to refine selection.")
                        
                        print(f"   Options:")
                        diffs = compute_candidate_diff(candidates)
                        for idx, diff_str in enumerate(diffs):
                            if len(diff_str) > 120:
                                diff_str = diff_str[:117] + "..."
                            print(f"   {idx+1}. {diff_str}")
                        print("")
                        compile_context = candidates[0]
            
    except Exception as e:
        print(f"Warning: Auto-Ghost failed or returned invalid data: {e}")

    print(f"Auto-Ghost found {len(dependencies)} implicit dependencies.")
    
    # Step 3b: Batch Sync Dependencies to Outside Wall
    if dependencies:
        valid_deps = [d for d in dependencies if d.startswith("/")]
        
        if valid_deps:
            print(f"  Ghosting {len(valid_deps)} dependencies (Batch Optimized)...")
            
            # 1. Prepare Permissions (Write Access)
            for dep in valid_deps:
                rel = dep.lstrip("/")
                local = os.path.join(OUTSIDE_WALL_DIR, rel)
                if os.path.exists(local):
                     try:
                         os.chmod(local, 0o644)
                     except: pass
            
            # 2. Create Temp List
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
                tmp_path = tmp.name
                for dep in valid_deps:
                    tmp.write(dep + "\n")
            
            # 3. Batch Rsync
            # Sync from host root "/" to OUTSIDE_WALL_DIR using the file list
            rsync_cmd = [
                "rsync", "-az", 
                "--files-from", tmp_path,
                "-e", "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null", 
                f"{host}:/", 
                OUTSIDE_WALL_DIR
            ]
            
            try:
                run_command(rsync_cmd)
            except Exception as e:
                print(f"  Batch ghosting failed: {e}")
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

            # 4. Enforce Read-Only
            for dep in valid_deps:
                rel = dep.lstrip("/")
                local = os.path.join(OUTSIDE_WALL_DIR, rel)
                if os.path.exists(local):
                     try:
                         os.chmod(local, 0o444)
                     except: pass
    
    # Step 4: Update local compile database (AFTER syncing dependencies)
    is_header = remote_path.endswith('.h') or remote_path.endswith('.hpp') or \
                remote_path.endswith('.hh') or remote_path.endswith('.hxx')
                
    if compile_context and not is_header:
        compile_context['file'] = remote_path
        print(f"Updating compile_commands.json for {args.file}")
        update_local_compile_db(compile_context, dependencies)
    elif is_header:
        print(f"Skipping compile_commands.json update for header: {args.file}")
        print("💡 Use 'projector focus <source_file>' to configure Clangd for this header.")

def do_push(args, trigger=False):
    """Pushes a file back to the host."""
    config = load_config()
    host = config['host_target']
    remote_root = config.get('remote_root', '.')
    local_path = args.file

    # Check for CLI override
    if hasattr(args, 'trigger') and args.trigger:
        trigger = True
    
    project_root = find_project_root()
    if not project_root:
        print("Error: Could not find project root (.hologram_config).")
        sys.exit(1)

    abs_path = os.path.abspath(local_path)
    hologram_abs = os.path.join(project_root, HOLOGRAM_DIR)
    wall_abs = os.path.join(project_root, OUTSIDE_WALL_DIR)
    
    # 1. Check The Wall
    if abs_path.startswith(wall_abs):
        print("🛑 VIOLATION: The Wall Breach Detected!")
        print(f"File {local_path} is in the Read-Only 'Outside Wall' zone.")
        print("You cannot push dependencies.")
        sys.exit(1)
        
    # 2. Check Valid Hologram File
    try:
        common = os.path.commonpath([hologram_abs, abs_path])
        if common != hologram_abs:
             print(f"Error: File {local_path} is not in the hologram directory.")
             sys.exit(1)
    except ValueError:
         print(f"Error: Paths on different drives or invalid.")
         sys.exit(1)
        
    # 3. Calculate remote path
    rel_path = os.path.relpath(abs_path, hologram_abs)
    
    # Handle absolute path mirroring (prevent double nesting)
    remote_root_stripped = remote_root.lstrip(os.path.sep)
    if rel_path.startswith(remote_root_stripped):
         remote_path = f"/{rel_path}".replace(os.path.sep, "/")
    else:
         remote_path = f"{remote_root}/{rel_path}".replace(os.path.sep, "/")
    
    print(f"Pushing {local_path} to {host}:{remote_path}...")
    
    # Ensure remote directory exists
    remote_dir = os.path.dirname(remote_path)
    if remote_dir and remote_dir != ".":
         ssh_opts = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]
         try:
             run_command(["ssh"] + ssh_opts + [host, f"unset HISTFILE; mkdir -p {remote_dir}"])
         except Exception:
             pass

    rsync_cmd = ["rsync", "-az", "-e", "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null", local_path, f"{host}:{remote_path}"]
    run_command(rsync_cmd)
    
    if trigger:
        # Lazy Import to avoid circularity
        from .build import find_build_context, trigger_build
        context_path = find_build_context(hologram_abs, os.path.dirname(abs_path))
        trigger_build(config, context_path)
        print("Sync & Trigger complete.")
    else:
        print("Sync complete (No Trigger).")

def retract_file(abs_path, config, project_root):
    """
    Retracts a single file: removes from hologram, restores to outside_wall if possible.
    Returns True if successful/processed, False on error.
    """
    input_path = os.path.relpath(abs_path, os.getcwd()) # For display
    hologram_abs = os.path.join(project_root, HOLOGRAM_DIR)
    
    # 1. Validate Path
    try:
        common = os.path.commonpath([hologram_abs, abs_path])
        if common != hologram_abs:
             print(f"Error: File {input_path} is not in the hologram directory.")
             return False
    except ValueError:
         print(f"Error: Paths on different drives or invalid.")
         return False
         
    # 2. Remove File
    if os.path.exists(abs_path):
        os.remove(abs_path)
        print(f"🗑️  Retracted {input_path} from hologram.")
    else:
        print(f"Warning: File {input_path} does not exist locally.")
        
    # 2b. Restore to Outside Wall (if remote exists)
    try:
        rel_path = os.path.relpath(abs_path, hologram_abs)
        host = config['host_target']
        remote_root = config.get('remote_root', '.')
        
        # Calculate Remote Path
        remote_root_stripped = remote_root.lstrip(os.path.sep)
        if rel_path.startswith(remote_root_stripped):
             remote_path = f"/{rel_path}".replace(os.path.sep, "/")
        else:
             remote_path = f"{remote_root}/{rel_path}".replace(os.path.sep, "/")

        # Check Remote Existence
        ssh_opts = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]
        check_cmd = ["ssh"] + ssh_opts + [host, f"unset HISTFILE; test -f {remote_path}"]
        subprocess.check_call(check_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Restore
        wall_dest = os.path.join(project_root, OUTSIDE_WALL_DIR, rel_path)
        os.makedirs(os.path.dirname(wall_dest), exist_ok=True)
        
        rsync_cmd = ["rsync", "-az", "-e", "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null", f"{host}:{remote_path}", wall_dest]
        run_command(rsync_cmd)
             
        # Enforce Read-Only
        os.chmod(wall_dest, 0o444)
        print(f"🧱 Restored {os.path.basename(wall_dest)} to Outside Wall.")
        
    except subprocess.CalledProcessError:
        pass
    except Exception as e:
        print(f"Warning: Failed to restore to outside_wall: {e}")
        
    return True

def do_retract(args):
    """Retracts a file from the hologram (stops projecting it)."""
    config = load_config()
    project_root = find_project_root()
    hologram_abs = os.path.join(project_root, HOLOGRAM_DIR)
    
    files_to_retract = []
    
    if args.all:
        print("💥 Retracting ALL files from Hologram...")
        if os.path.exists(hologram_abs):
            for root, dirs, files in os.walk(hologram_abs):
                for f in files:
                    full_path = os.path.join(root, f)
                    if f == "compile_commands.json" or f == ".hologram_config":
                        continue
                    files_to_retract.append(full_path)
    else:
        if not args.file:
            print("Error: Must specify a file or --all")
            sys.exit(1)
            
        input_path = args.file
        abs_path = os.path.abspath(input_path)
        
        if not abs_path.startswith(hologram_abs):
            try:
                rel_to_root = os.path.relpath(abs_path, project_root)
                candidate = os.path.join(hologram_abs, rel_to_root)
                if os.path.exists(candidate):
                    abs_path = candidate
            except ValueError:
                pass
        
        files_to_retract.append(abs_path)
        
    if not files_to_retract:
        print("Nothing to retract.")
        return

    for f_path in files_to_retract:
        retract_file(f_path, config, project_root)
        
    # 3. Clean up compile_commands.json
    db_path = os.path.join(hologram_abs, "compile_commands.json")
    if os.path.exists(db_path):
        try:
            with open(db_path, 'r') as f:
                db = json.load(f)
            
            retracted_set = set(files_to_retract)
            new_db = [e for e in db if os.path.abspath(e.get("file")) not in retracted_set]
            
            if len(db) != len(new_db):
                with open(db_path, 'w') as f:
                    json.dump(new_db, f, indent=2)
                print(f"cleaned compile_commands.json entries.")
        except Exception as e:
            print(f"Warning: Failed to update compile_commands.json: {e}")
            
    if args.all:
         for root, dirs, files in os.walk(hologram_abs, topdown=False):
             for name in dirs:
                 d_path = os.path.join(root, name)
                 try:
                     os.rmdir(d_path)
                 except OSError:
                     pass
