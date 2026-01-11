import sys
import os
import shutil
import subprocess
import argparse
import re
import json
from pathlib import Path

# --- Configuration ---
CLANG_QUERY = shutil.which("clang-query")
GIT_GREP = shutil.which("git")
COMPILE_DB = "compile_commands.json"

def get_repo_root():
    return os.getcwd()

def has_compile_db(root):
    return (Path(root) / COMPILE_DB).exists()

# --- TIER 1: Clang Query ---
def run_clang_query(query_str, root):
    if not CLANG_QUERY: return None
    try:
        with open(Path(root) / COMPILE_DB, 'r') as f:
            db = json.load(f)
            if not db: return None
            candidate = None
            for entry in db:
                fpath = Path(entry['directory']) / entry['file']
                if fpath.exists():
                    candidate = str(fpath)
                    break
            if not candidate: return None
    except:
        return None

    cmd = [CLANG_QUERY, "-p", root, candidate]
    try:
        process = subprocess.run(
            cmd,
            input=query_str,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        return process.stdout
    except Exception:
        return None

def parse_clang_output(raw_output):
    hits = set()
    for line in raw_output.splitlines():
        match = re.match(r"^(.+?):(\d+):(\d+):", line)
        if match:
            fpath = match.group(1)
            try:
                fpath = str(Path(fpath).relative_to(os.getcwd()))
            except ValueError:
                pass
            hits.add(f"{fpath}:{match.group(2)}")
    return sorted(list(hits))

def query_clang(mode, symbol, root):
    q = ""
    if mode == "callers":
        q = f"m callExpr(callee(functionDecl(hasName(\"{symbol}\"))))"
    elif mode == "callees":
        q = f"m callExpr(ancestor(functionDecl(hasName(\"{symbol}\"))))"
    elif mode == "defs":
        q = f"m functionDecl(hasName(\"{symbol}\"), isDefinition())"
    
    if not q: return None

    print(f"🔍 [Clang] Querying AST for '{symbol}'...", file=sys.stderr)
    raw = run_clang_query(q, root)
    if raw:
        return parse_clang_output(raw)
    return None

# --- TIER 2: Git Grep ---
def query_grep(mode, symbol, root):
    hits = set()
    print(f"⚠️ [Grep] Fallback search for '{symbol}'...", file=sys.stderr)
    cmd = []
    if mode == "callers":
        cmd = ["git", "grep", "-n", f"{symbol}("]
    elif mode == "callees":
        print("  [i] 'callees' not supported in grep mode.", file=sys.stderr)
        return []
    elif mode == "defs":
        cmd = ["git", "grep", "-n", f"^{symbol}("] 
        
    if not cmd: return []

    try:
        res = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        for line in res.stdout.splitlines():
            parts = line.split(":", 2)
            if len(parts) >= 2:
                hits.add(f"{parts[0]}:{parts[1]}")
    except:
        pass
    return sorted(list(hits))

# --- Main ---
def main():
    parser = argparse.ArgumentParser(description="Adaptive Code Map")
    parser.add_argument("mode", choices=["callers", "callees", "defs"], help="Query mode")
    parser.add_argument("symbol", help="Function or Type name")
    # We use -H because -h is reserved for --help
    parser.add_argument("-H", "--hint", action="store_true", help="Show copy-paste friendly /read command")
    
    args = parser.parse_args()
    root = get_repo_root()
    
    results = []
    
    if CLANG_QUERY and has_compile_db(root):
        results = query_clang(args.mode, args.symbol, root)
    
    if not results:
        if CLANG_QUERY and has_compile_db(root):
            print("  [i] Clang returned no results (or failed).", file=sys.stderr)
        results = query_grep(args.mode, args.symbol, root)

    # --- Output ---
    if not results:
        print("No results found.")
    else:
        # Standard Output (Clean)
        print(f"# Map: {args.mode} of '{args.symbol}'")
        for r in results[:20]:
            print(f"- {r}")
        if len(results) > 20:
            print(f"... ({len(results) - 20} more)")
            
        # Hint Output (Rich)
        if args.hint:
            unique_files = set()
            for r in results:
                if ":" in r:
                    fpath = r.rsplit(":", 1)[0]
                    unique_files.add(fpath)
                else:
                    unique_files.add(r)
            
            file_list_str = " ".join(sorted(list(unique_files)))
            
            print("\n# 📋 Quick Read:")
            print(f"/read {file_list_str}")

if __name__ == "__main__":
    main()
