import sys
import subprocess
from ..core.config import load_config

def do_run(args):
    """
    Executes a command on the remote host in the project environment.
    Proxies the command via SSH.
    """
    config = load_config()
    if not config:
        print("Error: Hologram not initialized. Run 'projector init' first.")
        sys.exit(1)

    host = config['host_target']
    remote_root = config.get('remote_root', '.')
    
    # We want to run the command inside the project root
    # And potentially sourced with environment if needed (future proofing)
    
    if args.command:
        # Join the command parts; this allows `projector run ls -la` without quotes
        # But `projector run "ls -la"` is safer for complex args.
        # argparse nargs='+' gives a list.
        cmd_to_run = " ".join(args.command)
    else:
        # If no command, just shell?
        print("Error: No command specified.")
        sys.exit(1)
    
    # Use -t to force pseudo-terminal allocation, enabling interactive commands like top, vim, etc.
    ssh_opts = ["-t"] 
    
    # Construct the ssh command
    # We cd to remote_root first
    full_remote_cmd = f"cd {remote_root} && {cmd_to_run}"
    
    if host == 'local':
        ssh_cmd = ["/bin/sh", "-c", full_remote_cmd]
    else:
        ssh_cmd = ["ssh"] + ssh_opts + [host, full_remote_cmd]
    
    try:
        # Check=False allows us to pass through the exit code without python raising exception
        result = subprocess.run(ssh_cmd)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        # SSH handles the signal usually, but if python catches it, just exit
        sys.exit(130)
    except Exception as e:
        print(f"Error running command: {e}")
        sys.exit(1)
