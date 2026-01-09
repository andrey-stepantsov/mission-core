import sys
import os
import json
import shlex
import yaml
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

def get_compile_command(fpath, db_paths, required_flags=None):
    """
    Finds the best matching compile command and generates disambiguation stats.
    Returns: (best_entry, stats_dict)
    """
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

        for entry in db:
            entry_file = Path(entry.get("file", "")).resolve()
            if entry_file == abs_fpath:
                cmd_str = ""
                if "command" in entry:
                    cmd_str = entry["command"]
                elif "arguments" in entry:
                    cmd_str = " ".join(entry["arguments"])
                
                candidates.append({
                    "entry": entry,
                    "cmd_str": cmd_str,
                    "score": 0
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
            score = 0
            for flag in required_flags:
                if flag in cand["cmd_str"]:
                    score += 1
            cand["score"] = score
            
        # Find the max score
        max_score = max(c["score"] for c in candidates)
        stats["score"] = max_score
        
        # Filter for winners (ties)
        winners = [c for c in candidates if c["score"] == max_score]
        
        # --- GENERATE WARNINGS ---
        
        # CASE A: Too Tight (No flags matched)
        if max_score == 0:
             stats["warnings"].append(
                 f"⚠️  TOO TIGHT: Found {total_candidates} entries, but NONE matched your selectors {required_flags}. Defaulting to first entry."
             )
        
        # CASE B: Too Loose (Ambiguous Ties)
        elif len(winners) > 1:
             stats["warnings"].append(
                 f"⚠️  TOO LOOSE: Found {total_candidates} entries. {len(winners)} matched your selectors equally well (Score: {max_score}). Random winner selected."
             )
        
        # CASE C: Goldilocks (Perfect)
        elif len(winners) == 1:
            pass # Perfect match
            
        best_match = winners[0]["entry"]
        stats["selected"] = len(winners)
        
    else:
        # No selectors provided, pick the first one
        best_match = candidates[0]["entry"]
        stats["selected"] = total_candidates
        if total_candidates > 1:
             stats["warnings"].append(
                 f"ℹ️  AMBIGUOUS: Found {total_candidates} entries and no selectors defined. Picking the first one."
             )

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
    
    db_paths = []
    if "--db" in sys.argv:
        db_paths = [sys.argv[sys.argv.index("--db") + 1]]
    else:
        db_paths = ["compile_commands.json", "build/compile_commands.json"]
        if "compilation_dbs" in config:
            db_paths.extend(config["compilation_dbs"])

    required_flags = []
    if "context_selector" in config:
        required_flags = config["context_selector"].get("required_flags", [])

    entry, stats = get_compile_command(target_file, db_paths, required_flags)
    
    # Print warnings to Stderr so the user sees them in logs
    for w in stats["warnings"]:
        print(w, file=sys.stderr)

    if entry:
        includes = extract_includes(entry, repo_root)
        print(json.dumps({
            "file": target_file,
            "found": True,
            "includes": includes,
            "selected_command": entry.get("command", "")[:100] + "...",
            "stats": stats 
        }, indent=2))
    else:
        print(json.dumps({
            "file": target_file,
            "found": False,
            "includes": [],
            "stats": stats
        }, indent=2))

if __name__ == "__main__":
    main()
