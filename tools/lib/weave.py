import argparse
import json
import sys
import os
import yaml
import glob
import subprocess
from pathlib import Path

def find_db(file_path, root_path):
    """
    Locates the appropriate compile_commands.json.
    Priority 1: Directory of the source file (e.g., drivers/hal/compile_commands.json)
    Priority 2: Repository Root (e.g., ./compile_commands.json)
    """
    file_dir = Path(file_path).parent
    
    # Check 1: Local
    candidate = file_dir / "compile_commands.json"
    if candidate.exists():
        return candidate
        
    # Check 2: Root
    candidate = Path(root_path) / "compile_commands.json"
    if candidate.exists():
        return candidate
        
    return None

def expand_c_context(file_list, repo_root):
    """
    Runs c_context on C/C++ files to find hidden header dependencies.
    """
    # Resolve c_context binary location (sibling to this script -> up to tools -> bin)
    # tools/lib/weave.py -> tools/bin/c_context
    script_dir = Path(__file__).parent.resolve()
    c_context_bin = script_dir.parent / "bin" / "c_context"
    
    if not c_context_bin.exists():
        # Fallback if running purely from lib
        print(f"Warning: c_context binary not found at {c_context_bin}", file=sys.stderr)
        return file_list

    expanded_files = set(file_list)
    processed_files = set()

    # Iterate over a static copy of the list so we can append to the set safely
    for file_path in list(expanded_files):
        if file_path in processed_files: 
            continue
            
        # Only process C/C++ source files (not headers, usually headers don't have DB entries)
        if not file_path.endswith(('.c', '.cpp', '.cc', '.cxx')):
            continue

        # Find DB
        db_path = find_db(file_path, repo_root)
        if not db_path:
            continue

        try:
            # Run c_context
            # cmd: c_context <file> --db <db> --root <root>
            cmd = [
                str(c_context_bin),
                file_path,
                "--db", str(db_path),
                "--root", str(repo_root)
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            data = json.loads(result.stdout)
            
            # Add discovered includes to the set
            for inc in data.get("includes", []):
                # Ensure we return relative paths if they are inside the repo, 
                # because Aider prefers relative paths for readability.
                try:
                    p = Path(inc).relative_to(repo_root)
                    expanded_files.add(str(p))
                except ValueError:
                    # External path (e.g. /tmp/chaos_sdk), keep absolute
                    expanded_files.add(inc)

        except subprocess.CalledProcessError:
            # If c_context fails (e.g. file not in DB), just ignore silently
            pass
        except json.JSONDecodeError:
            pass
            
        processed_files.add(file_path)

    return sorted(list(expanded_files))

def main():
    parser = argparse.ArgumentParser(description="Weave: The Agentic Build Tool")
    subparsers = parser.add_subparsers(dest='command')

    # 'hello' command
    subparsers.add_parser('hello', help='Prints a success message in JSON format.')

    # 'list' command
    subparsers.add_parser('list', help='List all available views.')

    # 'get' command
    parser_get = subparsers.add_parser('get', help='Get all files for a specific view.')
    parser_get.add_argument('view_name', help='The name of the view to get.')

    args = parser.parse_args()

    # Handle 'hello'
    if args.command == 'hello':
        print(json.dumps({"status": "success", "message": "Hello Weave"}))
        return

    # Load Configuration
    config_paths = [
        '.weaves/weave.yaml',
        '.mission/weave.yaml',
        'weave.yaml',
    ]

    found_config_path = None
    for path in config_paths:
        if os.path.exists(path):
            found_config_path = path
            break

    if not found_config_path:
        print(f"Error: Configuration file not found. Searched in: {', '.join(config_paths)}", file=sys.stderr)
        sys.exit(1)

    with open(found_config_path, 'r') as f:
        config = yaml.safe_load(f)

    if not config or 'views' not in config:
        print("Error: 'views' key not found in weave.yaml.", file=sys.stderr)
        sys.exit(1)

    views = config.get('views', {})

    if args.command == 'list':
        for view_name in views:
            print(view_name)
    elif args.command == 'get':
        view_patterns = views.get(args.view_name)
        if view_patterns is None:
            print(f"Error: View '{args.view_name}' not found in weave.yaml.", file=sys.stderr)
            sys.exit(1)

        # 1. Glob Files
        initial_files = set()
        for pattern in view_patterns:
            for f in glob.glob(pattern, recursive=True):
                initial_files.add(f)

        # 2. Expand Context (C/C++ Awareness)
        repo_root = os.getcwd()
        final_files = expand_c_context(list(initial_files), repo_root)

        # 3. Output
        print(" ".join(final_files))

if __name__ == "__main__":
    main()
