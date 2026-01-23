
import os
import sys
import pytest
import subprocess
import shutil

class TestDevboxIntegration:
    """Verifies that the Devbox environment is correctly configured."""

    def test_devbox_python_version(self):
        """Checks if running inside Devbox provides Python 3.8."""
        # This test assumes it's being run via `devbox run` or inside the shell.
        # But if we run it from outside, we need to invoke devbox.
        # To be safe, let's invoke `devbox run python --version` from the chaos root.
        
        # Assume CWD is chaos root or we can find it
        chaos_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        
        if os.environ.get("DEVBOX_SHELL_ENABLED"):
             assert sys.version_info[:2] == (3, 8), f"Expected Python 3.8 inside devbox, got {sys.version}"
             return

        if not os.path.exists(os.path.join(chaos_root, "devbox.json")):
             pytest.skip("devbox.json not found in chaos root")

        cmd = ["devbox", "run", "--", "python", "--version"]
        result = subprocess.run(cmd, cwd=chaos_root, capture_output=True, text=True)
        
        # Validates that we can run python and it is 3.8
        assert result.returncode == 0, f"devbox run python failed: {result.stderr}"
        assert "Python 3.8" in result.stdout or "Python 3.8" in result.stderr

    def test_projector_availability(self):
        """Checks if projector is in the PATH inside devbox."""
        chaos_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        
        if os.environ.get("DEVBOX_SHELL_ENABLED"):
             pytest.skip("Skipping nested devbox invocation check")

        # We try to run `projector --help`
        cmd = ["devbox", "run", "--", "projector", "--help"]
        result = subprocess.run(cmd, cwd=chaos_root, capture_output=True, text=True)
        
        assert result.returncode == 0, f"devbox run projector failed: {result.stderr}"
        assert "usage: projector" in result.stdout

    def test_rsync_availability(self):
        """Checks if rsync is available inside devbox."""
        chaos_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        
        if os.environ.get("DEVBOX_SHELL_ENABLED"):
             pytest.skip("Skipping nested devbox invocation check")

        cmd = ["devbox", "run", "--", "rsync", "--version"]
        result = subprocess.run(cmd, cwd=chaos_root, capture_output=True, text=True)
        
        assert result.returncode == 0
        assert "rsync" in result.stdout

    def test_ssh_availability(self):
        """Checks if ssh is available inside devbox."""
        chaos_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        
        if os.environ.get("DEVBOX_SHELL_ENABLED"):
             pytest.skip("Skipping nested devbox invocation check")

        cmd = ["devbox", "run", "--", "ssh", "-V"]
        result = subprocess.run(cmd, cwd=chaos_root, capture_output=True, text=True)
        
        # ssh -V writes to stderr usually
        assert result.returncode == 0
        assert "OpenSSH" in result.stderr
