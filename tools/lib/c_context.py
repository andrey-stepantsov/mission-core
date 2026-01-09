import sys
import os
import json
import shlex
import argparse
import yaml
from pathlib import Path

def load_db(db_path):
    try:
        with open(db_path, 'r') as f:
            return json.load(f)
    except Exception:
        return []

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

def get_host_prefix(entry_file_abs, target_rel):
    """
    Detects the prefix used in the DB that doesn't exist in the current env.
    DB: /Users/me/repo/src/main.c
    Target: src/main.c
    Result: /Users/me/repo
    """
    entry_file_abs = str(Path(entry_file_abs))
    target_rel = str(Path(target_rel))
    if entry_file_abs.endswith(target_rel):
        prefix = entry_file_abs[:-len(target_rel)]
        if prefix.endswith(os.sep):
            prefix = prefix[:-1]
        return prefix
    return None

def find_entry_and_prefix(db, target_file, repo_root):
    target_abs = str(Path(target_file).resolve())
    try:
        target_rel = str(Path(target_file).resolve().relative_to(repo_root))
    except ValueError:
        target_rel = str(Path(target_file))

    for entry in db:
        entry_file = entry['file']
        
        # 1. Exact Match
        if entry_file == target_abs:
            return entry, None
            
        # 2. Resolved Match
        try:
            if str(Path(entry_file).resolve()) == target_abs:
                return entry, None
        except OSError:
            pass
            
        # 3. Suffix Match (Host vs Container)
        if entry_file.endswith(target_rel):
            prefix = get_host_prefix(entry_file, target_rel)
            return entry, prefix
            
    return None, None

def rebase_path(path_str, host_prefix, repo_root):
    """
    If path starts with host_prefix, replace it with repo_root.
    """
    if not host_prefix:
        return Path(path_str)
    
    path_str = str(Path(path_str))
    if path_str.startswith(host_prefix):
        rel_part = path_str[len(host_prefix):]
        if rel_part.startswith(os.sep):
            rel_part = rel_part[1:]
        return (repo_root / rel_part).resolve()
    return Path(path_str)

def extract_includes(entry, repo_root, host_prefix):
    includes = []
    args = []
    if 'arguments' in entry:
        args = entry['arguments']
    elif 'command' in entry:
        args = shlex.split(entry['command'])
    
    raw_work_dir = entry.get('directory', str(repo_root))
    work_dir = rebase_path(raw_work_dir, host_prefix, repo_root)

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
                resolved = (work_dir / p).resolve()
            else:
                # Absolute path in DB. Check if it needs re-homing.
                resolved = rebase_path(str(p), host_prefix, repo_root)
            includes.append(str(resolved))
        i += 1
    
    includes.insert(0, str(work_dir))
    return includes

def scan_file_headers(file_path):
    headers = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith("#include"):
                    parts = line.split()
                    if len(parts) > 1:
                        h = parts[1].strip('"<>')
                        headers.append(h)
    except Exception:
        pass
    return headers

def resolve_headers(headers, include_dirs):
    resolved = []
    missing = []
    for h in headers:
        found = False
        for d in include_dirs:
            p = Path(d) / h
            if p.exists():
                resolved.append(str(p))
                found = True
                break
        if not found:
            missing.append(h)
    return resolved, missing

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="Source file to analyze")
    parser.add_argument("--db", default="compile_commands.json", help="Default DB")
    parser.add_argument("--root", default=".", help="Project root")
    args = parser.parse_args()
    
    repo_root = Path(args.root).resolve()
    db_paths = [Path(args.db)]
    
    extra_dbs = load_config(repo_root)
    for db_str in extra_dbs:
        db_paths.append(repo_root / db_str)
        
    entry = None
    host_prefix = None
    
    # Try finding the file in all known DBs
    for db_path in db_paths:
        if db_path.exists():
            db = load_db(db_path)
            found_entry, found_prefix = find_entry_and_prefix(db, args.file, repo_root)
            if found_entry:
                entry = found_entry
                host_prefix = found_prefix
                break
    
    if not entry:
        # Fallback: empty result
        print(json.dumps({"file": str(Path(args.file).resolve()), "includes": [], "missing": []}))
        return

    include_dirs = extract_includes(entry, repo_root, host_prefix)
    raw_headers = scan_file_headers(args.file)
    found, missing = resolve_headers(raw_headers, include_dirs)
    
    result = {
        "file": str(Path(args.file).resolve()),
        "includes": found,
        "missing": missing
    }
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
