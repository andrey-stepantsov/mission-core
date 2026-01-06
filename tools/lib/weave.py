#!/usr/bin/python3

import argparse
import sys
import yaml

def main():
    """Main function for the weave tool."""
    parser = argparse.ArgumentParser(description="A tool to manage and display file views based on a YAML configuration.")
    subparsers = parser.add_subparsers(dest='command', required=True)

    # 'list' command
    subparsers.add_parser('list', help='List all available views.')

    # 'get' command
    parser_get = subparsers.add_parser('get', help='Get all files for a specific view.')
    parser_get.add_argument('view_name', help='The name of the view to get.')

    args = parser.parse_args()

    try:
        with open('weave.yaml', 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print("Error: weave.yaml not found in the current directory.", file=sys.stderr)
        sys.exit(1)

    if not config or 'views' not in config:
        print("Error: 'views' key not found in weave.yaml.", file=sys.stderr)
        sys.exit(1)

    views = config.get('views', {})

    if args.command == 'list':
        for view_name in views:
            print(view_name)
    elif args.command == 'get':
        view_files = views.get(args.view_name)
        if view_files:
            for file_path in view_files:
                print(file_path)
        else:
            print(f"Error: View '{args.view_name}' not found.", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
