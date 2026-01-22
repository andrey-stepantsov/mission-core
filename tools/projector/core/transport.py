import subprocess
import sys

def run_command(cmd, shell=False, capture_stderr=True):
    """Runs a shell command and returns stdout."""
    try:
        stderr_dest = subprocess.PIPE if capture_stderr else sys.stderr
        result = subprocess.run(cmd, shell=shell, check=True, stdout=subprocess.PIPE, stderr=stderr_dest, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        # Check if stderr is just noise (warnings)
        err_msg = e.stderr if e.stderr else ""
        lines = err_msg.splitlines()
        real_errors = [l for l in lines if not (l.startswith("Warning:") or "setlocale" in l)]
        
        if real_errors:
            print(f"Error running command: {cmd}")
            print(f"Stderr: {err_msg}")
        elif not capture_stderr:
             # If we weren't capturing, typically means interactive or we don't care about output unless failed
            print(f"Command failed with exit code {e.returncode}: {cmd}")
            
        raise e  # Re-raise so caller handles flow

class RemoteHost:
    def __init__(self, host, transport='ssh', ssh_opts=None):
        self.host = host
        self.transport = transport
        self.ssh_opts = ssh_opts or ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]

    def run(self, cmd_str, capture_stderr=True, shell=True):
        if self.transport == 'ssh':
            full_cmd = ["ssh"] + self.ssh_opts + [self.host, f"unset HISTFILE; {cmd_str}"]
            return run_command(full_cmd, shell=False, capture_stderr=capture_stderr)
        else:
            # Local Mode: just run the command directly
            return run_command(f"unset HISTFILE; {cmd_str}", shell=True, capture_stderr=capture_stderr)

    def rsync_pull(self, remote_path, local_path, recursive=False, files_from=None):
        cmd = ["rsync", "-az"]
        if recursive: cmd.append("-r")
        
        if self.transport == 'ssh':
            cmd.extend(["-e", f"ssh {' '.join(self.ssh_opts)}"])
            if files_from:
                cmd.extend(["--files-from", files_from, f"{self.host}:/", local_path])
            else:
                cmd.extend([f"{self.host}:{remote_path}", local_path])
        else:
            # Local rsync
            if files_from:
                cmd.extend(["--files-from", files_from, "/", local_path])
            else:
                cmd.extend([remote_path, local_path])
        
        return run_command(cmd)

    def rsync_push(self, local_path, remote_path):
        cmd = ["rsync", "-az"]
        if self.transport == 'ssh':
            cmd.extend(["-e", f"ssh {' '.join(self.ssh_opts)}", local_path, f"{self.host}:{remote_path}"])
        else:
            cmd.extend([local_path, remote_path])
        
        return run_command(cmd)
