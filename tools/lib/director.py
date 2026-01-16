import os
import sys
import time
import re
import json
from datetime import datetime
from litellm import completion

# --- Configuration ---
LOG_FILE = os.environ.get("MISSION_JOURNAL", ".mission-context/mission_log.md")
MODEL = os.environ.get("MODEL", "vertex_ai/gemini-1.5-pro")

# Color Codes
BLUE = "\033[1;34m"
GREEN = "\033[1;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
RESET = "\033[0m"

def extract_timestamp(line):
    match = re.search(r"\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\]", line)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return None
    return None

def write_request(command):
    now = datetime.now()
    timestamp_str = now.strftime("%Y-%m-%dT%H:%M:%S")
    entry = f"\n### [{timestamp_str}] [Director -> LocalSmith] [REQ] {command}\n"
    
    with open(LOG_FILE, "a") as f:
        f.write(entry)
    
    print(f"{YELLOW}>> Signal Sent: {command}{RESET}")
    return now

def wait_for_ack(start_time):
    print(f"{BLUE}... Waiting for LocalSmith (timeout: 45s) ...{RESET}")
    start_time_seconds = start_time.timestamp()
    
    for _ in range(45):
        if not os.path.exists(LOG_FILE):
            time.sleep(1)
            continue
            
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
            
        for line in reversed(lines):
            if "[LocalSmith -> Director]" in line and ("[ACK]" in line or "[ERR]" in line):
                msg_time = extract_timestamp(line)
                if msg_time and msg_time.timestamp() >= (start_time_seconds - 1):
                    color = GREEN if "[ACK]" in line else RED
                    print(f"{color}<< Signal Received: {line.strip()}{RESET}")
                    return True
        time.sleep(1)
        
    print(f"{RED}[!] Timeout waiting for ACK.{RESET}")
    return False

def get_llm_action(user_input, history):
    system_prompt = """
    You are the Mission Director. Control 'LocalSmith' via commands.
    
    Commands:
    - `backup <file>`
    - `set <key> to <value>`
    - `run verification`
    - `echo <message>`
    
    PROTOCOL INSTRUCTION:
    To execute a command, your output must contain: CMD: <command>
    Example: "I will run the check. CMD: run verification"
    """
    
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": user_input}]
    
    try:
        response = completion(model=MODEL, messages=messages)
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

def main():
    print(f"{GREEN}🤖 Director Online (v3: Robust Parsing){RESET}")
    print(f"{BLUE}📡 Radio Frequency: {LOG_FILE}{RESET}")
    print("---------------------------------------------------")

    history = []

    while True:
        try:
            user_input = input("\nDirector> ")
            if user_input.lower() in ["exit", "quit"]:
                break
                
            response = get_llm_action(user_input, history)
            
            # Regex to find CMD: anywhere in the response
            match = re.search(r"CMD:\s*(.*)", response, re.IGNORECASE)
            
            if match:
                # We found a command!
                # If there was chat text before it, print that first
                prefix = response[:match.start()].strip()
                if prefix:
                    print(prefix)
                    
                command = match.group(1).strip()
                # Clean up any trailing quotes or periods if the LLM got messy
                command = command.strip()
                
                request_time = write_request(command)
                wait_for_ack(request_time)
                
                history.append({"role": "user", "content": user_input})
                history.append({"role": "assistant", "content": f"Executed: {command}"})
            else:
                print(f"{response}")
                history.append({"role": "user", "content": user_input})
                history.append({"role": "assistant", "content": response})
                
        except KeyboardInterrupt:
            print("\n[!] Shutting down.")
            break

if __name__ == "__main__":
    main()
