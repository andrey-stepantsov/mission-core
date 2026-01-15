import argparse
import sys
import os
import datetime
from pathlib import Path

# --- DYNAMIC LOG RESOLUTION ---
def get_default_log_path():
    # Priority 1: Environment Variable
    if os.environ.get("MISSION_LOG_FILE"):
        return os.path.abspath(os.environ["MISSION_LOG_FILE"])

    # Priority 2: Standard Docker Mount
    # In the container, the repo is always mounted at /repo
    if os.path.exists("/repo/.mission-context"):
        return "/repo/.mission-context/mission_log.md"

    # Priority 3: Host Relative Path
    # Current file is in .mission/tools/lib/radio.py
    tool_lib = Path(__file__).resolve().parent
    repo_root = tool_lib.parent.parent.parent # .mission -> repo
    
    context_dir = repo_root / ".mission-context"
    if context_dir.exists():
        return str(context_dir / "mission_log.md")

    # Priority 4: Legacy Fallback
    mission_data = tool_lib.parent.parent / "data"
    mission_data.mkdir(parents=True, exist_ok=True)
    return str(mission_data / "mission_log.md")

DEFAULT_LOG = get_default_log_path()

def append_entry(sender, recipient, msg_type, content, attachment=None):
    # Ensure directory exists
    os.makedirs(os.path.dirname(DEFAULT_LOG), exist_ok=True)
    
    timestamp = datetime.datetime.now().isoformat(timespec='seconds')
    
    entry = f"\n### [{timestamp}] [{sender} -> {recipient}] [{msg_type}]\n{content}\n"
    if attachment:
        entry += f"\n<details>\n<summary>Attachment</summary>\n\n```\n{attachment}\n```\n\n</details>\n"
    entry += "\n---\n"
    
    try:
        with open(DEFAULT_LOG, "a", encoding="utf-8") as f:
            f.write(entry)
        print(f"📡 Transmitted {msg_type} to {DEFAULT_LOG}")
    except Exception as e:
        print(f"❌ Radio Write Error: {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)
    p_tx = subparsers.add_parser('tx')
    p_tx.add_argument('--from', dest='sender', required=True)
    p_tx.add_argument('--to', dest='recipient', required=True)
    p_tx.add_argument('--type', choices=['REQ', 'ACK', 'LOG', 'HALT'], required=True)
    p_tx.add_argument('--msg', required=True)
    
    args = parser.parse_args()
    if args.command == 'tx':
        append_entry(args.sender, args.recipient, args.type, args.msg)

if __name__ == "__main__":
    main()
