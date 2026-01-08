import sys
import os
import json
import shlex
import yaml
from pathlib import Path

def get_external_paths(db_path, repo_root):
    external_paths = set()
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
                p = Path(val)
                if not p.is_absolute():
                    work_dir = Path(entry.get("directory", repo_root))
                    p = (work_dir / p).resolve()
                else:
                    p = p.resolve()
                try:
                    p.relative_to(repo_root)
                except ValueError:
                    if p.exists():
                        external_paths.add(p)
            i += 1
    return external_paths

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
    
    found_paths = set()
    for db in db_paths:
        if db.exists():
            found_paths.update(get_external_paths(db, repo_root))

    flags = []
    for p in sorted(list(found_paths)):
        flags.append(f'-v {p}:{p}:ro,z')
    if flags:
        print(" ".join(flags))

if __name__ == "__main__":
    main()
