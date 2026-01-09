import sys
import os
import json
import shlex
import yaml
from pathlib import Path

def get_external_paths(db_path, repo_root):
    mount_pairs = set()
    repo_root = Path(repo_root).resolve()
    
    try:
        with open(db_path, 'r') as f:
            db = json.load(f)
    except Exception:
        return set()

    for entry in db:
        args = []
        if "arguments" in entry:
            args = entry["arguments"]
        elif "command" in entry:
            args = shlex.split(entry["command"])
        
        i = 0
        while i < len(args):
            arg = args[i]
            val = None
            if arg.startswith("-I"):
                val = arg[2:]
                if not val and i + 1 < len(args):
                    val = args[i+1]
            elif arg == "-isystem":
                if i + 1 < len(args):
                    val = args[i+1]
            
            if val:
                path_obj = Path(val)
                if not path_obj.is_absolute():
                    work_dir = Path(entry.get("directory", repo_root))
                    logical_path = (work_dir / path_obj)
                else:
                    logical_path = path_obj

                logical_str = os.path.normpath(str(logical_path))

                try:
                    physical_path = Path(logical_str).resolve()
                    physical_str = str(physical_path)
                    
                    try:
                        physical_path.relative_to(repo_root)
                    except ValueError:
                        if physical_path.exists():
                            mount_pairs.add((physical_str, physical_str))
                            if physical_str != logical_str:
                                mount_pairs.add((physical_str, logical_str))
                except OSError:
                    pass
            i += 1
            
    return mount_pairs

def load_config(repo_root):
    config_paths = [
        Path(repo_root) / ".weaves/weave.yaml",
        Path(repo_root) / ".mission/weave.yaml",
        Path(repo_root) / "weave.yaml",
    ]
    for path in config_paths:
        if path.exists():
            try:
                with open(path, 'r') as f:
                    config = yaml.safe_load(f)
                    return config.get("compilation_dbs", [])
            except Exception:
                pass
    return []

def optimize_mounts(mounts):
    """
    Removes redundant child mounts.
    If '/a/b' is mounted, we don't need '/a/b/c'.
    """
    # Sort by length so we process parents before children
    sorted_mounts = sorted(list(mounts), key=lambda x: x[0])
    final_mounts = []

    for host_p, container_p in sorted_mounts:
        # Check if this path is already covered by an existing parent mount
        covered = False
        for parent_h, parent_c in final_mounts:
            # We only consolidate if BOTH host and container paths match the nesting
            # (To avoid complex mapping edge cases)
            try:
                # Check if host path is inside parent host path
                Path(host_p).relative_to(Path(parent_h))
                # Check if container path is inside parent container path
                Path(container_p).relative_to(Path(parent_c))
                covered = True
                break
            except ValueError:
                continue
        
        if not covered:
            final_mounts.append((host_p, container_p))
            
    return final_mounts

def main():
    repo_root = os.getcwd()
    db_paths = {
        Path(repo_root) / "compile_commands.json",
        Path(repo_root) / "build/compile_commands.json"
    }
    extra_dbs = load_config(repo_root)
    for db_str in extra_dbs:
        db_paths.add((Path(repo_root) / db_str).resolve())
    
    all_mounts = set()
    for db in db_paths:
        if db.exists():
            all_mounts.update(get_external_paths(db, repo_root))

    # OPTIMIZATION STEP
    optimized = optimize_mounts(all_mounts)

    flags = []
    for host_p, container_p in optimized:
        # CHANGED: Removed 'z' flag to avoid SELinux issues on NFS (/auto)
        flags.append(f'-v {host_p}:{container_p}:ro')
        
    if flags:
        print(" ".join(flags))

if __name__ == "__main__":
    main()
