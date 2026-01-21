import sys
import os
import json
import shlex
import yaml
import re
from pathlib import Path

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
                    return yaml.safe_load(f) or {}
            except Exception:
                pass
    return {}

def extract_macros(cmd_str):
    """Extracts -D definitions from a command string."""
    macros = []
    # Simple tokenization to handle quoted strings safely
    try:
        args = shlex.split(cmd_str)
        for arg in args:
            if arg.startswith("-D"):
                macros.append(arg[2:])
            elif arg.startswith("-U"):
                macros.append(f"!{arg[2:]}") # Mark undefs
    except Exception:
        # Fallback regex if shlex fails on complex make lines
        macros = re.findall(r'-D([a-zA-Z0-9_=\(\)]+)', cmd_str)
    return sorted(list(set(macros)))

def get_compile_command(fpath, db_paths, required_flags=None):
    repo_root = Path(os.getcwd())
    abs_fpath = Path(fpath).resolve()
    
    candidates = []

    # 1. Harvest all candidates
    for db_path in db_paths:
        if not os.path.exists(db_path):
            continue
            
        try:
            with open(db_path, 'r') as f:
                db = json.load(f)
        except:
            continue

        for i, entry in enumerate(db):
            entry_file_str = entry.get("file", "")
            
            # 1. Try exact string match (normalized)
            is_match = False
            is_sibling = False
            
            if entry_file_str == str(abs_fpath):
                 is_match = True
            
            # 2. Try resolved path comparison if not matched yet
            if not is_match:
                 try:
                     entry_file_p = Path(entry_file_str).resolve()
                     if entry_file_p == abs_fpath:
                         is_match = True
                 except:
                     pass

            # 3. Header Fallback: If target is header, look for sibling source
            if not is_match and abs_fpath.suffix in ['.h', '.hh', '.hpp']:
                 try:
                     entry_file_p = Path(entry_file_str).resolve()
                     if entry_file_p.parent == abs_fpath.parent and \
                        entry_file_p.stem == abs_fpath.stem and \
                        entry_file_p.suffix in ['.c', '.cc', '.cpp', '.cxx']:
                             is_sibling = True
                 except:
                     pass

            if is_match or is_sibling:
                cmd_str = ""
                if "command" in entry:
                    cmd_str = entry["command"]
                elif "arguments" in entry:
                    cmd_str = " ".join(entry["arguments"])
                
                # Clone entry to avoid mutating original DB
                # Override 'file' to match target header so valid DB entry is created
                final_entry = entry.copy()
                final_entry["file"] = str(abs_fpath)
                
                candidates.append({
                    "entry": final_entry,
                    "cmd_str": cmd_str,
                    "score": 100 if is_match else 50,
                    "type": "exact" if is_match else "sibling"
                })


    total_candidates = len(candidates)
    stats = {
        "found": False,
        "total": total_candidates,
        "selected": 0,
        "score": 0,
        "warnings": []
    }

    if not candidates:
        return None, stats

    stats["found"] = True

    # 2. Score Candidates
    if required_flags:
        for cand in candidates:
            score = cand["score"] # Start with base score
            for flag in required_flags:
                if flag in cand["cmd_str"]:
                    score += 10 # Flags are important, but exact match is king? 
                                # Actually, if exact match lacks flags, do we prefer sibling with flags?
                                # Probably not. Exact match is usually correct file.
                                # So let's make exact match worth 100, flags worth 1.
                                # Wait, I set base_score to 100 or 50.
                    score += 1     
            cand["score"] = score
            
        max_score = max(c["score"] for c in candidates)
        stats["score"] = max_score
        
        winners = [c for c in candidates if c["score"] == max_score]
        
        if max_score == 0:
             stats["warnings"].append(
                 f"⚠️  TOO TIGHT: Found {total_candidates} entries, but NONE matched your selectors {required_flags}. Defaulting to first entry."
             )
        elif len(winners) > 1:
             stats["warnings"].append(
                 f"⚠️  TOO LOOSE: Found {total_candidates} entries. {len(winners)} matched your selectors equally well (Score: {max_score}). Random winner selected."
             )
            
        best_match = winners[0]
        stats["selected"] = len(winners)
    else:
        best_match = candidates[0]
        stats["selected"] = total_candidates
        if total_candidates > 1:
             stats["warnings"].append(
                 f"ℹ️  AMBIGUOUS: Found {total_candidates} entries and no selectors defined. Picking the first one."
             )

    # Always expose candidates for downstream analysis
    stats["candidates"] = candidates
    
    return best_match, stats

def extract_includes(entry, repo_root):
    includes = []
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
            work_dir = Path(entry.get("directory", repo_root))
            full_path = (work_dir / val).resolve()
            includes.append(str(full_path))
        i += 1
        
    return includes

def main():
    if len(sys.argv) < 2:
        print("Usage: c_context.py <file> [--db <path>]")
        sys.exit(1)

    target_file = sys.argv[1]
    repo_root = os.getcwd()
    config = load_config(repo_root)
    
    # Simple CLI parsing (avoid argparse for minimal deps if desired, but we used shlex/json already)
    db_paths = []
    provided_flags = []
    
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--db" and i + 1 < len(sys.argv):
            db_paths.append(sys.argv[i+1])
            i += 2
        elif arg == "--flags" and i + 1 < len(sys.argv):
            # Flags passed as single string e.g. "-DTEST -O2"
            raw_flags = sys.argv[i+1]
            # Split by space
            provided_flags = shlex.split(raw_flags)
            i += 2
        else:
             i += 1

    if not db_paths:
        # Search upwards for compile_commands.json
        current_dir = Path(os.getcwd())
        root_markers = [".git", ".mission", "compile_commands.json"]
        
        search_paths = []
        # Walk up until root
        while True:
            candidate = current_dir / "compile_commands.json"
            if candidate.exists():
                search_paths.append(str(candidate))
                search_paths.append(str(current_dir / "build" / "compile_commands.json"))
                break # Found the likely root
            
            parent = current_dir.parent
            if parent == current_dir: # Reached filesystem root
                break 
            current_dir = parent
            
        # Fallback to CWD if nothing found
        if not search_paths:
             search_paths = ["compile_commands.json", "build/compile_commands.json"]
             
        db_paths = search_paths
        
        if "compilation_dbs" in config:
            db_paths.extend(config["compilation_dbs"])

    required_flags = []
    # Merge Config Flags with CLI Flags
    # CLI flags take precedence or add to them? 
    # Usually CLI specific flags are more important for disambiguation.
    # Let's use Union.
    config_flags = config.get("context_selector", {}).get("required_flags", [])
    required_flags = list(set(config_flags + provided_flags))

    # Debug


    match, stats = get_compile_command(target_file, db_paths, required_flags)
    
    for w in stats["warnings"]:
        print(w, file=sys.stderr)

    if match:
        entry = match["entry"]
        cmd_str = match["cmd_str"]
        includes = extract_includes(entry, repo_root)
        macros = extract_macros(cmd_str)
        
        # Prepare full info
        args = []
        if "arguments" in entry:
            args = entry["arguments"]
        elif "command" in entry:
            import shlex
            args = shlex.split(entry["command"])

        print(json.dumps({
            "file": target_file,
            "found": True,
            "includes": includes,
            "macros": macros,
            "arguments": args, # Full arguments for re-execution
            "directory": entry.get("directory", repo_root),
            "candidates": stats.get("candidates", []), # Expose all candidates
            "stats": stats 
        }, indent=2))
    else:
        print(json.dumps({
            "file": target_file,
            "found": False,
            "includes": [],
            "macros": [],
            "stats": stats
        }, indent=2))

if __name__ == "__main__":
    main()
