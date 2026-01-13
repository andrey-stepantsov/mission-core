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

# --- TIER 2: Grep / Ripgrep (UPGRADED) ---
def query_grep(mode, symbol, root):
    import shutil
    hits = set()
    
    # 1. Detect Tool (rg > git grep)
    RG = shutil.which("rg")
    tool_bin = RG if RG else "git"
    
    print(f"⚠️ [{tool_bin}] Fallback search for '{symbol}'...", file=sys.stderr)

    # 2. Build Regex
    pattern = ""
    if mode == "callers":
        pattern = f"\\b{symbol}\\b"
    elif mode == "defs":
        # Regex Breakdown:
        # #define\s+{symbol}\b          -> Macros
        # | \b{symbol}\s*\(              -> Functions
        # | \}\s*{symbol}\s*;            -> Compact Typedefs: "} my_type;"
        # | ^\s*{symbol}\s*;             -> Dangling Typedefs: "    my_type;" (NEW)
        # | typedef\s+.*\b{symbol}\s*;   -> Simple Typedefs
        # | (struct|enum|union)\s+{symbol}\s*\{  -> Tag Defs
        pattern = f"(#define\\s+{symbol}\\b|\\b{symbol}\\s*\\(|\\}}\\s*{symbol}\\s*;|^\\s*{symbol}\\s*;|typedef\\s+.*\\b{symbol}\\s*;|(struct|enum|union)\\s+{symbol}\\s*\\{{)"
    elif mode == "callees":
        return []

    # 3. Build Command
    cmd = []
    if RG:
        cmd = [RG, "-n", "--no-heading", pattern]
    else:
        cmd = ["git", "grep", "-n", "-E", pattern]

    try:
        res = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        for line in res.stdout.splitlines():
            parts = line.split(":", 2)
            if len(parts) >= 2:
                hits.add(f"{parts[0]}:{parts[1]}")
    except Exception as e:
        print(f"Search failed: {e}", file=sys.stderr)
        pass

    # 4. SORTING LOGIC (Name Affinity > Headers > Source)
    def score(hit):
        path_str = hit.split(":", 1)[0]
        p_obj = Path(path_str)
        fname = p_obj.stem.lower().replace("_", "")
        sym_clean = symbol.lower().replace("_", "")
        
        # Tier 1: Filename matches symbol (e.g., zassert.h for z_assert)
        if sym_clean == fname:
            prio = 0
        # Tier 2: Headers
        elif p_obj.suffix in (".h", ".hpp", ".hh", ".hxx"):
            prio = 1
        # Tier 3: Everything else
        else:
            prio = 2
            
        return (prio, hit)

        
    return sorted(list(hits), key=score)



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
        print(f"# Map: {args.mode} of '{args.symbol}'")
        
        # Deduplicate files while preserving sorted order
        seen_files = set()
        unique_ordered = []
        for r in results:
            # Split "path/to/file:123" -> "path/to/file"
            if ":" in r:
                fpath = r.rsplit(":", 1)[0]
            else:
                fpath = r
            
            if fpath not in seen_files:
                seen_files.add(fpath)
                unique_ordered.append(fpath)
        
        # Print top 20 unique files (Clean Paths)
        for f in unique_ordered[:20]:
            print(f"- {f}")
            
        if len(unique_ordered) > 20:
            print(f"... ({len(unique_ordered) - 20} more files)")
            
        # Hint Output (Rich)
        if args.hint:
            file_list_str = " ".join(unique_ordered)
            print("\n# 📋 Quick Read:")
            print(f"/read {file_list_str}")
if __name__ == "__main__":
    main()
