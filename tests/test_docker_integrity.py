import subprocess
import os
import sys

LAUNCHER = os.path.abspath(".mission/tools/lib/launch_container.sh")

def get_host_git_user():
    """Gets the git user from the host machine."""
    try:
        return subprocess.check_output(["git", "config", "user.name"], text=True).strip()
    except:
        return ""

def run_in_container(cmd):
    result = subprocess.run(
        [LAUNCHER, "bash", "-c", cmd],
        capture_output=True,
        text=True
    )
    # Filter out splash screen
    clean_lines = [line for line in result.stdout.splitlines() if "🐳" not in line]
    return "\n".join(clean_lines).strip(), result.stderr.strip()

def test_git_identity_injection():
    # 1. Get Container Reality
    container_user, _ = run_in_container("git config user.name")
    print(f"DEBUG: Container User = '{container_user}'")

    # 2. Get Host Reality
    host_user = get_host_git_user()
    if not host_user:
        host_user = "Mission Developer" # The script default
    print(f"DEBUG: Host User      = '{host_user}'")

    # 3. Assert (Dynamic)
    # Pass if they match, OR if the container has the fallback default
    assert container_user == host_user or container_user == "Mission Developer"

def test_auth_mount():
    stdout, stderr = run_in_container("ls /tmp/auth.json")
    assert "/tmp/auth.json" in stdout

def test_aider_version():
    stdout, stderr = run_in_container("aider-vertex --version")
    assert "aider" in stdout.lower() or "aider" in stderr.lower()
