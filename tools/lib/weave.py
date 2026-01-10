import argparse
import json
import sys
import os
import yaml
import glob
import subprocess
from pathlib import Path

def find_db(file_path, root_path):
    file_dir = Path(file_path).parent
    candidate = file_dir / "compile_commands.json"
    if candidate.exists(): return candidate
    candidate = Path(root_path) / "compile_commands.json"
    if candidate.exists(): return candidate
    return None

def generate_context_card(macros, repo_root):
    """Generates a Markdown file listing active macros."""
    if not macros:
        return None
        
    gen_dir = Path(repo_root) / ".mission" / "gen"
    gen_dir.mkdir(parents=True, exist_ok=True)
    card_path = gen_dir / "active_context.md"
    
    content = [
        "# 🛡️ Active Build Context",
        "",
        "The following Preprocessor Definitions are ACTIVE for the current view.",
        "Use this information to interpret `#ifdef` blocks.",
        "",
        "| Macro | Status |",
        "| :--- | :--- |"
    ]
    
    for m in sorted(list(macros)):
        if m.startswith("!"):
            content.append(f"| `{m[1:]}` | **UNDEFINED** |")
        else:
            if "=" in m:
                key, val = m.split("=", 1)
                content.append(f"| `{key}` | `{val}` |")
            else:
                content.append(f"| `{m}` | DEFINED |")
                
    content.append("")
    
    with open(card_path, "w") as f:
        f.write("\n".join(content))
        
    return str(card_path.relative_to(repo_root))

def expand_c_context(file_list, repo_root, manual_macros=None):
    script_dir = Path(__file__).parent.resolve()
    c_context_bin = script_dir.parent / "bin" / "c_context"
    
    if not c_context_bin.exists():
        print(f"Warning: c_context binary not found at {c_context_bin}", file=sys.stderr)
        return file_list

    expanded_files = set(file_list)
    processed_files = set()
    collected_macros = set()
    
    # 0. Inject Manual Macros
    if manual_macros:
        for m in manual_macros:
            collected_macros.add(m)

    for file_path in list(expanded_files):
        if file_path in processed_files: continue
        if not file_path.endswith(('.c', '.cpp', '.cc', '.cxx')): continue

        db_path = find_db(file_path, repo_root)
        if not db_path: continue

        try:
            cmd = [
                str(c_context_bin),
                file_path,
                "--db", str(db_path),
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            # 1. Collect Includes
            for inc in data.get("includes", []):
                try:
                    p = Path(inc).relative_to(repo_root)
                    expanded_files.add(str(p))
                except ValueError:
                    expanded_files.add(inc)
            
            # 2. Collect Macros
            for m in data.get("macros", []):
                collected_macros.add(m)

        except subprocess.CalledProcessError:
            pass
        except json.JSONDecodeError:
            pass
            
        processed_files.add(file_path)
    
    # Generate the Card
    card = generate_context_card(collected_macros, repo_root)
    if card:
        expanded_files.add(card)
        print(f"🛡️  Context Card Generated: {card} ({len(collected_macros)} macros active)", file=sys.stderr)

    return sorted(list(expanded_files))

def main():
    parser = argparse.ArgumentParser(description="Weave: The Agentic Build Tool")
    subparsers = parser.add_subparsers(dest='command')

    subparsers.add_parser('hello', help='Prints a success message in JSON format.')
    subparsers.add_parser('list', help='List all available views.')

    parser_get = subparsers.add_parser('get', help='Get all files for a specific view.')
    parser_get.add_argument('view_name', help='The name of the view to get.')
    parser_get.add_argument('--expand', action='store_true', help='Expand context using C-Context analysis.')

    args = parser.parse_args()

    if args.command == 'hello':
        print(json.dumps({"status": "success", "message": "Hello Weave"}))
        return

    config_paths = ['.weaves/weave.yaml', '.mission/weave.yaml', 'weave.yaml']
    found_config_path = None
    for path in config_paths:
        if os.path.exists(path):
            found_config_path = path
            break

    if not found_config_path:
        print(f"Error: Configuration file not found.", file=sys.stderr)
        sys.exit(1)

    with open(found_config_path, 'r') as f:
        config = yaml.safe_load(f)

    if args.command == 'list':
        for view_name in config.get('views', {}):
            print(view_name)
    elif args.command == 'get':
        views = config.get('views', {})
        view_patterns = views.get(args.view_name)
        if view_patterns is None:
            print(f"Error: View '{args.view_name}' not found.", file=sys.stderr)
            sys.exit(1)

        initial_files = set()
        for pattern in view_patterns:
            for f in glob.glob(pattern, recursive=True):
                initial_files.add(f)
        
        # --- NEW: Extract Extra Defines ---
        extra_defines = []
        if "context_selector" in config:
            extra_defines = config["context_selector"].get("extra_defines", [])

        final_files = sorted(list(initial_files))
        if args.expand:
            repo_root = os.getcwd()
            # Pass manual macros to the expander
            final_files = expand_c_context(final_files, repo_root, manual_macros=extra_defines)

        print(" ".join(final_files))

if __name__ == "__main__":
    main()
