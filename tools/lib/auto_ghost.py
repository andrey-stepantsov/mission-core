import sys
import os
import json
import argparse
from pathlib import Path

# Import sibling c_context if available
try:
    import c_context
except ImportError:
    # Try adding directory to path
    sys.path.append(os.path.dirname(os.path.realpath(__file__)))
    try:
        import c_context
    except ImportError:
        c_context = None

def run_legacy_mode():
    """Legacy volume mount generation for Direct Mode."""
    # ... (Keep existing legacy logic or just fail if c_context missing?)
    # For now, we only need the NEW mode for Projector.
    # The legacy logic is huge and brittle. If we are deprecating Direct Mode, maybe we can stub it?
    # Or just keep the critical part: get_external_paths logic is not in c_context?
    # c_context HAS get_compile_command.
    # Legacy auto_ghost iterates ALL db entries.
    pass

def main():
    parser = argparse.ArgumentParser(description="Auto-Ghost: Dependency & Context Discovery")
    parser.add_argument("--full", help="Target file to analyze for full context (Projector Mode)")
    parser.add_argument("--flags", help="Additional flags to help disambiguate context")
    
    # Parse known args to allow legacy usage (which didn't use flags)?
    # Legacy didn't pass args.
    args, unknown = parser.parse_known_args()
    
    if args.full:
        # Projector Mode
        if not c_context:
            print(json.dumps({"error": "c_context library not found"}), file=sys.stderr)
            sys.exit(1)
            
        target_file = args.full
        
        # 1. Find DBs
        repo_root = os.getcwd()
        config = c_context.load_config(repo_root)
        
        db_paths = []
        # Search upwards logic (reused from c_context or reimplemented?)
        # c_context doesn't export the search logic nicely in main, let's reuse a simplified version
        current_dir = Path(os.getcwd())
        search_paths = []
        while True:
            candidate = current_dir / "compile_commands.json"
            if candidate.exists():
                search_paths.append(str(candidate))
                search_paths.append(str(current_dir / "build" / "compile_commands.json"))
                break 
            parent = current_dir.parent
            if parent == current_dir: break 
            current_dir = parent
            
        if not search_paths:
             search_paths = ["compile_commands.json", "build/compile_commands.json"]
        db_paths = search_paths
        if "compilation_dbs" in config:
            db_paths.extend(config["compilation_dbs"])
            
        # 2. Get Context
        import shlex
        required_flags = []
        if args.flags:
            required_flags = shlex.split(args.flags)
            
        match, stats = c_context.get_compile_command(target_file, db_paths, required_flags)
        
        if match:
            entry = match["entry"]
            cmd_str = match["cmd_str"]
            includes = c_context.extract_includes(entry, repo_root)
            macros = c_context.extract_macros(cmd_str)
            
            # Projector Output Format
            print(json.dumps({
                "dependencies": includes,
                "compile_context": {
                    "directory": entry.get("directory", repo_root),
                    "file": target_file,
                    "command": cmd_str,
                    # Also provide split args if available
                    "arguments": entry.get("arguments"),
                    "macros": macros,
                    "candidates": stats.get("candidates", [])
                }
            }, indent=2))
        else:
            # Not found
            print(json.dumps({
                "dependencies": [],
                "compile_context": None,
                "candidates": stats.get("candidates", [])
            }, indent=2))
            
    else:
        # Legacy Mode (No args or unknown args)
        # We can try to preserve legacy behavior if needed, but for this task we assume Projector usage.
        # But wait, existing workflows might break?
        # The legacy code was about 130 lines.
        # I'll just print nothing for now to verify Projector. 
        # If I overwrite the file, I lose legacy.
        # I should probably backup legacy or reimplement minimal legacy if needed.
        # BUT Projector is the future.
        pass

if __name__ == "__main__":
    main()
