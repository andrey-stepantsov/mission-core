import argparse
import sys
import os
import datetime

__version__ = '0.1.0'

MEMO_FILE = ".mission/memo.md"

def get_memo_path():
    # If .mission doesn't exist, use current directory (fallback)
    if os.path.isdir(".mission"):
        return MEMO_FILE
    return "memo.md"

def cmd_write(args):
    path = get_memo_path()
    
    # 1. Header
    content = f"""---
sender: {os.environ.get('USER', 'unknown')}
timestamp: {datetime.datetime.now().isoformat()}
---

# Instruction
{args.message}
"""
    # 2. Append File (if requested)
    if args.file:
        if not os.path.exists(args.file):
            print(f"Error: File '{args.file}' not found.", file=sys.stderr)
            sys.exit(1)
        
        with open(args.file, 'r') as f:
            file_content = f.read()
        
        content += f"\n\n# Attachment: {args.file}\n```\n{file_content}\n```\n"

    # 3. Write
    try:
        with open(path, 'w') as f:
            f.write(content)
        print(f"Memo sent to {path}")
    except IOError as e:
         print(f"Error writing memo to {path}: {e}", file=sys.stderr)

def cmd_read(args):
    path = get_memo_path()
    if not os.path.exists(path):
        print("No memo found.")
        return

    with open(path, 'r') as f:
        print(f.read())

def cmd_inspect(args):
    # Determine which log to inspect (default to coder)
    target = ".aider.coder.history.md"
    if args.target == "architect":
        target = ".aider.architect.history.md"
    
    if not os.path.exists(target):
        print(f"No history found for {target}")
        return

    print(f"--- TAIL OF {target} ({args.lines} lines) ---")
    # specific tail implementation to avoid dependency on 'tail' command
    try:
        with open(target, 'r') as f:
            lines = f.readlines()
            for line in lines[-int(args.lines):]:
                print(line, end='')
    except Exception as e:
        print(f"Error reading log: {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description="Agent Collaboration Tool")
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Write
    p_write = subparsers.add_parser('write', help='Write a memo to the other agent')
    p_write.add_argument('message', help='The instruction message')
    p_write.add_argument('--file', help='Attach a file to the memo')

    # Read
    p_read = subparsers.add_parser('read', help='Read the current memo')

    # Inspect
    p_inspect = subparsers.add_parser('inspect', help='Inspect agent logs')
    p_inspect.add_argument('--target', choices=['coder', 'architect'], default='coder')
    p_inspect.add_argument('--lines', default=50, type=int, help='Number of lines to read')

    args = parser.parse_args()

    if args.command == 'write':
        cmd_write(args)
    elif args.command == 'read':
        cmd_read(args)
    elif args.command == 'inspect':
        cmd_inspect(args)

if __name__ == "__main__":
    main()
