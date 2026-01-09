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
                # 1. Resolve Logical Path (What the DB says)
                if not path_obj.is_absolute():
                    work_dir = Path(entry.get("directory", repo_root))
                    logical_path = (work_dir / path_obj)
                else:
                    logical_path = path_obj

                logical_str = os.path.normpath(str(logical_path))

                # 2. Resolve Physical Path (Where the file actually is)
                try:
                    physical_path = Path(logical_str).resolve()
                    physical_str = str(physical_path)
                    
                    # Check if external to repo
                    try:
                        physical_path.relative_to(repo_root)
                        # It is inside repo -> Ignore
                    except ValueError:
                        # It is external -> Mount it
                        if physical_path.exists():
                            # Mount 1: Physical -> Physical (Robustness)
                            mount_pairs.add((physical_str, physical_str))
                            
                            # Mount 2: Physical -> Logical (DB Compatibility)
                            # If the DB points to a symlink (e.g. /var/...) but the file 
                            # is really at /private/var/..., we need to mount the physical
                            # file to the logical location so the compiler finds it.
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

    flags = []
    # Generate Docker flags: -v HOST:CONTAINER:ro,z
    # We sort by container path to have deterministic output
    for host_p, container_p in sorted(list(all_mounts), key=lambda x: x[1]):
        flags.append(f'-v {host_p}:{container_p}:ro,z')
        
    if flags:
        print(" ".join(flags))

if __name__ == "__main__":
    main()
