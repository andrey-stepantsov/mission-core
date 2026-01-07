import argparse
import sys
import os
import datetime

# __version__ removed for simulation

MEMO_FILE = ".mission/memo.md"

def get_memo_path():
    if os.path.isdir(".mission"):
        return MEMO_FILE
    return "memo.md"

def cmd_write(args):
    path = get_memo_path()
    content = f"""---
sender: {os.environ.get('USER', 'unknown')}
timestamp: {datetime.datetime.now().isoformat()}
---

# Instruction
{args.message}
"""
    if args.file:
        if not os.path.exists(args.file):
            print(f"Error: File '{args.file}' not found.", file=sys.stderr)
            sys.exit(1)
        with open(args.file, 'r') as f:
            file_content = f.read()
        content += f"\n\n# Attachment: {args.file}\n```\n{file_content}\n```\n"

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
    target = ".aider.coder.history.md"
    if args.target == "architect":
        target = ".aider.architect.history.md"
    
    if not os.path.exists(target):
        print(f"No history found for {target}")
        return

    print(f"--- TAIL OF {target} ({args.lines} lines) ---")
    try:
        with open(target, 'r') as f:
            lines = f.readlines()
            for line in lines[-int(args.lines):]:
                print(line, end='')
    except Exception as e:
        print(f"Error reading log: {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description="Agent Collaboration Tool")
    # Version flag removed for simulation
    subparsers = parser.add_subparsers(dest='command', required=True)

    p_write = subparsers.add_parser('write', help='Write a memo')
    p_write.add_argument('message', help='The instruction message')
    p_write.add_argument('--file', help='Attach a file')

    p_read = subparsers.add_parser('read', help='Read the memo')

    p_inspect = subparsers.add_parser('inspect', help='Inspect logs')
    p_inspect.add_argument('--target', choices=['coder', 'architect'], default='coder')
    p_inspect.add_argument('--lines', default=50, type=int)

    args = parser.parse_args()

    if args.command == 'write':
        cmd_write(args)
    elif args.command == 'read':
        cmd_read(args)
    elif args.command == 'inspect':
        cmd_inspect(args)

if __name__ == "__main__":
    main()
