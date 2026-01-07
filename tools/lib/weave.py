import argparse
import json
import sys
import os
import yaml

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

    # CRITICAL FIX: Handle 'hello' BEFORE loading config
    if args.command == 'hello':
        print(json.dumps({"status": "success", "message": "Hello Weave"}))
        return

    # Load Configuration
    if not os.path.exists('weave.yaml'):
        print("Error: weave.yaml not found in the current directory.", file=sys.stderr)
        sys.exit(1)

    with open('weave.yaml', 'r') as f:
        config = yaml.safe_load(f)

    if not config or 'views' not in config:
        print("Error: 'views' key not found in weave.yaml.", file=sys.stderr)
        sys.exit(1)

    views = config.get('views', {})

    if args.command == 'list':
        for view_name in views:
            print(view_name)
    elif args.command == 'get':
        view_files = views.get(args.view_name)
        # (Stub for get implementation)
        print(f"Getting view: {args.view_name}")

if __name__ == "__main__":
    main()
