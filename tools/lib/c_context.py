import sys
import os
import json
import argparse
import re
import shlex
from pathlib import Path

def normalize_path(path_str, root):
    """Resolves a path to absolute."""
    p = Path(path_str)
    if not p.is_absolute():
        p = (Path(root) / p).resolve()
    else:
        p = p.resolve()
    return p

def is_system_path(path, repo_root):
    """
    Determines if a path is a 'System' path (Noise) vs 'Project' path (Signal).
    
    Heuristic:
    1. If it is inside the Repo Root, it is USER (Signal).
    2. If it is in standard system locations (/usr, /opt), it is SYSTEM (Noise).
    3. If it is elsewhere (e.g. /tmp/sdk, ../sibling), treat as USER (Signal).
    """
    try:
        # Check if inside repo
        path.relative_to(repo_root)
        return False
    except ValueError:
        pass

    # Check for hard system paths
    as_str = str(path)
    if as_str.startswith("/usr") or as_str.startswith("/System") or as_str.startswith("/opt/rh"):
        return True
    
    # Assume external user library (sibling or out-of-tree SDK)
    return False

def extract_flags(entry):
    """
    Extracts -I, -isystem, and -D flags from a DB entry.
    Handles both 'command' (string) and 'arguments' (list) formats.
    """
    includes = []
    defines = []
    
    # Normalize to a list of arguments
    args = []
    if "arguments" in entry:
        args = entry["arguments"]
    elif "command" in entry:
        # Use shlex to split command string correctly handling quotes
        args = shlex.split(entry["command"])
    
    # Parse args
    i = 0
    while i < len(args):
        arg = args[i]
        
        # Includes
        if arg.startswith("-I"):
            val = arg[2:]
            if not val: # Handle "-I path"
                if i + 1 < len(args):
                    val = args[i+1]
                    i += 1
            if val: includes.append(val)
            
        elif arg == "-isystem":
            if i + 1 < len(args):
                includes.append(args[i+1])
                i += 1
                
        # Defines
        elif arg.startswith("-D"):
            val = arg[2:]
            if not val:
                if i + 1 < len(args):
                    val = args[i+1]
                    i += 1
            if val: defines.append(val)
            
        i += 1
        
    return includes, defines

def scan_includes(file_path):
    """
    Scans a file for #include directives.
    Returns list of tuples: (raw_path, is_system_bracket)
    """
    includes = []
    # Regex for #include "foo" or #include <foo>
    # Group 1: "foo"
    # Group 2: <foo>
    regex = re.compile(r'^\s*#\s*include\s+(?:"([^"]+)"|<([^>]+)>)')
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                m = regex.match(line)
                if m:
                    if m.group(1):
                        includes.append((m.group(1), False)) # Quote
                    elif m.group(2):
                        includes.append((m.group(2), True))  # Bracket
    except Exception as e:
        sys.stderr.write(f"Error reading {file_path}: {e}\n")
        
    return includes

def resolve_header(filename, source_dir, search_paths):
    """
    Attempts to find 'filename' in search_paths.
    Returns (ResolvedPath, FoundBoolean)
    """
    # 1. Check relative to source (implicitly first for quotes, sometimes for brackets too depending on compiler)
    candidate = source_dir / filename
    if candidate.exists():
        return candidate.resolve(), True
        
    # 2. Check search paths
    for path in search_paths:
        candidate = path / filename
        if candidate.exists():
            return candidate.resolve(), True
            
    return None, False

def main():
    parser = argparse.ArgumentParser(description="C-Context Resolution Tool")
    parser.add_argument("target", help="Target source file")
    parser.add_argument("--db", default="compile_commands.json", help="Path to compilation database")
    parser.add_argument("--root", default=os.getcwd(), help="Repository root")
    
    args = parser.parse_args()
    
    root_path = Path(args.root).resolve()
    target_path = Path(args.target).resolve()
    db_path = Path(args.db).resolve()
    
    if not db_path.exists():
        print(json.dumps({"error": f"Database not found: {db_path}"}))
        sys.exit(1)
        
    try:
        with open(db_path, 'r') as f:
            db = json.load(f)
    except Exception as e:
        print(json.dumps({"error": f"Failed to parse DB: {e}"}))
        sys.exit(1)
        
    # 1. Find Entry
    entry = None
    # normalize DB file paths for comparison
    target_str = str(target_path)
    
    for item in db:
        # DB paths might be relative or absolute. Resolve them.
        # Directory field in DB is the working dir for the command
        work_dir = Path(item["directory"]).resolve()
        
        file_p = Path(item["file"])
        if not file_p.is_absolute():
            file_p = (work_dir / file_p).resolve()
            
        if str(file_p) == target_str:
            entry = item
            entry["directory_resolved"] = work_dir
            break
            
    if not entry:
        print(json.dumps({"error": f"File not found in DB: {target_str}"}))
        sys.exit(1)
        
    # 2. Extract Flags
    raw_includes, defines = extract_flags(entry)
    
    # Resolve include paths to absolute Path objects
    search_paths = []
    work_dir = entry["directory_resolved"]
    
    for inc in raw_includes:
        p = Path(inc)
        if not p.is_absolute():
            p = (work_dir / p).resolve()
        if p.exists():
            search_paths.append(p)
            
    # 3. Scan & Resolve
    raw_found = scan_includes(target_path)
    
    output = {
        "file": str(target_path),
        "defines": defines,
        "includes": [],
        "system_includes": [],
        "missing": []
    }
    
    source_dir = target_path.parent
    
    for fname, is_bracket in raw_found:
        resolved, found = resolve_header(fname, source_dir, search_paths)
        
        if found:
            if is_system_path(resolved, root_path):
                output["system_includes"].append(str(resolved))
            else:
                output["includes"].append(str(resolved))
        else:
            output["missing"].append(fname)
            
    # Deduplicate lists
    output["includes"] = sorted(list(set(output["includes"])))
    output["system_includes"] = sorted(list(set(output["system_includes"])))
    output["missing"] = sorted(list(set(output["missing"])))
    
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    main()
