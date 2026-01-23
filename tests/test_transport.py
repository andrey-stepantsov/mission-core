import unittest
from unittest.mock import patch, MagicMock, call
import subprocess
from projector.core.transport import RemoteHost

class TestRemoteHost(unittest.TestCase):
    def setUp(self):
        self.host = RemoteHost("user@remote", ssh_opts=["-o", "Option=Value"])
        self.local_host = RemoteHost("local", transport="local")

    @patch("projector.core.transport.subprocess.run")
    def test_run_ssh(self, mock_run):
        # Setup mock return
        mock_result = MagicMock()
        mock_result.stdout = "output\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        output = self.host.run("echo hello")
        
        self.assertEqual(output, "output")
        
        # Verify SSH command construction
        expected_cmd = ["ssh", "-o", "Option=Value", "user@remote", "unset HISTFILE; echo hello"]
        mock_run.assert_called_with(
            expected_cmd, 
            shell=False, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )

    @patch("projector.core.transport.subprocess.run")
    def test_run_local(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = "local output\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        output = self.local_host.run("ls -la")
        
        self.assertEqual(output, "local output")
        
        # Verify Local command (shell=True)
        expected_cmd = "unset HISTFILE; ls -la"
        mock_run.assert_called_with(
            expected_cmd,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

    @patch("projector.core.transport.subprocess.run")
    def test_rsync_pull_ssh(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        self.host.rsync_pull("/remote/path", "/local/path")

        expected_cmd = [
            "rsync", "-az", 
            "-e", "ssh -o Option=Value", 
            "user@remote:/remote/path", 
            "/local/path"
        ]
        # Check that the call args match standard rsync behavior
        args, kwargs = mock_run.call_args
        self.assertEqual(args[0], expected_cmd)

    @patch("projector.core.transport.subprocess.run")
    def test_rsync_push_ssh(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        self.host.rsync_push("/local/file", "/remote/dest")

        expected_cmd = [
            "rsync", "-az", 
            "-e", "ssh -o Option=Value", 
            "/local/file", 
            "user@remote:/remote/dest"
        ]
        args, kwargs = mock_run.call_args
        self.assertEqual(args[0], expected_cmd)
        
    @patch("projector.core.transport.subprocess.run")
    def test_rsync_local(self, mock_run):
        # Local to Local rsync
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        self.local_host.rsync_push("/src/file", "/dest/file")
        
        expected_cmd = ["rsync", "-az", "/src/file", "/dest/file"]
        args, kwargs = mock_run.call_args
        self.assertEqual(args[0], expected_cmd)

if __name__ == '__main__':
    unittest.main()
