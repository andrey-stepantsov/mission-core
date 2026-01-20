import os
import datetime
import time

# Configuration
# We wrap this in abspath to satisfy the strict infrastructure tests
DEFAULT_LOG = os.path.abspath(os.environ.get("MISSION_JOURNAL") or ".mission-context/mission_log.md")

def get_timestamp():
    return datetime.datetime.now().isoformat(timespec='seconds')

def append_entry(sender, recipient, msg_type, content):
    """
    Writes a structured log entry to the mission journal.
    Format: ### [TIMESTAMP] [Sender -> Recipient] [TYPE] Content
    """
    timestamp = get_timestamp()
    
    # Ensure directory exists
    log_dir = os.path.dirname(DEFAULT_LOG)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
        
    # The fix from ID 056: Ensure {content} is actually written
    entry = f"\n### [{timestamp}] [{sender} -> {recipient}] [{msg_type}] {content}\n"
    
    try:
        with open(DEFAULT_LOG, "a") as f:
            f.write(entry)
        print(f"📡 Transmitted {msg_type} to {DEFAULT_LOG}")
        return True
    except Exception as e:
        print(f"❌ Radio Error: {e}")
        return False

def read_latest(limit=5):
    """Reads the last N lines from the log."""
    if not os.path.exists(DEFAULT_LOG):
        return []
    with open(DEFAULT_LOG, "r") as f:
        lines = f.readlines()
        return lines[-limit:]
