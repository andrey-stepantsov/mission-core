import time
import os
import sys
import re
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "lib")
sys.path.insert(0, LIB_DIR)
import radio

MODEL = os.environ.get("DIRECTOR_MODEL") or "vertex_ai/gemini-2.5-pro"
POLL_INTERVAL = 1.0
MY_NAME = "Director"

SYSTEM_PROMPT = """You are the Strategic Director.
Goal: Create a detailed technical plan based on the request.
Output: STRICT MARKDOWN ONLY. Start with '# Plan: <Title>'.
"""

def get_log_path():
    return radio.DEFAULT_LOG

def parse_line(line):
    match = re.search(r"### \[.*\] \[(.*) -> (.*)\] \[(.*)\]", line)
    if match:
        return match.group(1), match.group(2), match.group(3)
    return None, None, None

def generate_plan(request, sender):
    print(f"🤔 Thinking... (Model: {MODEL})")
    try:
        import litellm
    except ImportError:
        return "Error: 'litellm' library not installed."

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Request from {sender}: {request}"}
    ]
    try:
        response = litellm.completion(
            model=MODEL, 
            messages=messages,
            timeout=15 
        )
        print("   [Debug] API Call Returned Success")
        return response.choices[0].message.content
    except Exception as e:
        print(f"   [Debug] API Call Failed: {e}")
        return f"Plan Generation Failed: {e}"

def main():
    if "--help" in sys.argv:
        print(f"Director Agent (Model: {MODEL})")
        sys.exit(0)

    log_path = get_log_path()
    print(f"👀 Director watching: {log_path}")
    print(f"🤖 Active Model: {MODEL}")
    
    last_pos = 0
    if os.path.exists(log_path):
        last_pos = os.path.getsize(log_path)

    while True:
        try:
            if os.path.exists(log_path):
                current_size = os.path.getsize(log_path)
                
                if current_size > last_pos:
                    with open(log_path, 'r') as f:
                        f.seek(last_pos)
                        new_lines = f.readlines()
                        last_pos = f.tell()

                    for line in new_lines:
                        sender, recipient, msg_type = parse_line(line)
                        if recipient == MY_NAME and msg_type == "REQ":
                            print(f"⚡️ Activated by {sender}")
                            plan_content = generate_plan("Analyze requirements", sender)
                            
                            # --- CORE SMITH RULE ENFORCEMENT ---
                            # Plans must go to .mission-context, NOT .mission
                            
                            plan_name = f"plan_{int(time.time())}.md"
                            
                            # Resolve Repo Root (3 levels up from tools/lib)
                            repo_root = Path(CURRENT_DIR).parent.parent.parent
                            
                            # Priority 1: .mission-context/plans
                            plan_dir = repo_root / ".mission-context" / "plans"
                            
                            # Fallback: Current Dir/plans (if not installed as submodule)
                            if not plan_dir.parent.exists():
                                plan_dir = Path("plans")
                                
                            plan_dir.mkdir(parents=True, exist_ok=True)
                            
                            try:
                                with open(plan_dir / plan_name, "w") as p:
                                    p.write(plan_content)
                                radio.append_entry(MY_NAME, sender, "ACK", f"Plan saved: {plan_dir}/{plan_name}")
                            except Exception as e:
                                radio.append_entry(MY_NAME, sender, "LOG", f"Write Error: {e}")
                
                elif current_size < last_pos:
                    last_pos = 0
                    
        except Exception as e:
            print(f"Error in loop: {e}")
            
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
