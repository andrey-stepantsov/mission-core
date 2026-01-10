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
GIT_GREP = shutil.which("git") # git grep
COMPILE_DB = "compile_commands.json"

def get_repo_root():
    return os.getcwd()

def has_compile_db(root):
    return (Path(root) / COMPILE_DB).exists()

# --- TIER 1: Clang Query ---

def run_clang_query(query_str, root):
    """Executes a raw clang-query string."""
    if not CLANG_QUERY: return None
    
    # We must find at least one valid source file to anchor the query
    # clang-query requires a file arg even if the query is global
    # We'll read the DB to find a candidate
    try:
        with open(Path(root) / COMPILE_DB, 'r') as f:
            db = json.load(f)
            if not db: return None
            # Pick the first file that actually exists
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
        # Pass query via stdin
        process = subprocess.run(
            cmd,
            input=query_str,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        return process.stdout
    except Exception as e:
        return None

def parse_clang_output(raw_output):
    """Parses clang-query output format: /path/file.cpp:10:5: note: ..."""
    hits = set()
    for line in raw_output.splitlines():
        # Match standard file:line:col pattern
        match = re.match(r"^(.+?):(\d+):(\d+):", line)
        if match:
            # Normalize path relative to CWD if possible
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
        # Find calls where callee name is symbol
        q = f"m callExpr(callee(functionDecl(hasName(\"{symbol}\"))))"
    elif mode == "callees":
        # Find calls occurring INSIDE the function named symbol
        q = f"m callExpr(ancestor(functionDecl(hasName(\"{symbol}\"))))"
    elif mode == "defs":
        # Find function definitions
        q = f"m functionDecl(hasName(\"{symbol}\"), isDefinition())"
    
    if not q: return None

    print(f"🔍 [Clang] Querying AST for '{symbol}'...", file=sys.stderr)
    raw = run_clang_query(q, root)
    if raw:
        return parse_clang_output(raw)
    return None

# --- TIER 2: Git Grep (Fallback) ---

def query_grep(mode, symbol, root):
    hits = set()
    print(f"⚠️ [Grep] Fallback search for '{symbol}'...", file=sys.stderr)
    
    cmd = []
    if mode == "callers":
        # Literal search for "symbol("
        cmd = ["git", "grep", "-n", f"{symbol}("]
    elif mode == "callees":
        # Cannot reliably do callees with grep without parsing
        print("  [i] 'callees' not supported in grep mode.", file=sys.stderr)
        return []
    elif mode == "defs":
        # Try to match start of line or return type pattern
        # This is heuristics only
        cmd = ["git", "grep", "-n", f"^{symbol}("] 
        
    if not cmd: return []

    try:
        res = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        for line in res.stdout.splitlines():
            # file:line:content
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
    
    args = parser.parse_args()
    root = get_repo_root()
    
    results = []
    
    # Strategy: Try Clang -> Fail -> Try Grep
    if CLANG_QUERY and has_compile_db(root):
        results = query_clang(args.mode, args.symbol, root)
    
    if not results:
        if CLANG_QUERY and has_compile_db(root):
            print("  [i] Clang returned no results (or failed).", file=sys.stderr)
        
        # Fallback to Grep
        results = query_grep(args.mode, args.symbol, root)

    # Output
    if not results:
        print("No results found.")
    else:
        print(f"# Map: {args.mode} of '{args.symbol}'")
        for r in results[:20]:
            print(f"- {r}")
        if len(results) > 20:
            print(f"... ({len(results) - 20} more)")

if __name__ == "__main__":
    main()
