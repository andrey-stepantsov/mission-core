import sys
import os
import json
import shlex
from pathlib import Path

def get_external_paths(db_path, repo_root):
    """
    Scans compile_commands.json for absolute paths outside the repo.
    Returns a set of Path objects.
    """
    external_paths = set()
    repo_root = Path(repo_root).resolve()
    
    try:
        with open(db_path, 'r') as f:
            db = json.load(f)
    except Exception:
        return set()

    for entry in db:
        # Normalize args
        args = []
        if "arguments" in entry:
            args = entry["arguments"]
        elif "command" in entry:
            args = shlex.split(entry["command"])
        
        # Parse includes
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
                # If relative, resolve against the entry's directory
                if not p.is_absolute():
                    work_dir = Path(entry.get("directory", repo_root))
                    p = (work_dir / p).resolve()
                else:
                    p = p.resolve()
                
                # Check if external
                try:
                    p.relative_to(repo_root)
                    # It's internal, ignore
                except ValueError:
                    # It's external!
                    if p.exists():
                        external_paths.add(p)
            
            i += 1
            
    return external_paths

def main():
    repo_root = os.getcwd()
    db_paths = [
        Path(repo_root) / "compile_commands.json",
        Path(repo_root) / "build/compile_commands.json" # Common CMake location
    ]
    
    found_paths = set()
    
    for db in db_paths:
        if db.exists():
            found_paths.update(get_external_paths(db, repo_root))

    # Output as Docker flags
    # FIX: Do not wrap paths in quotes; Bash substitution handles tokens.
    flags = []
    for p in sorted(list(found_paths)):
        flags.append(f'-v {p}:{p}:ro,z')
        
    if flags:
        print(" ".join(flags))

if __name__ == "__main__":
    main()
