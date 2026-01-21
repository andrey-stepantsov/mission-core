
import os
import sys
import pytest
import shutil
import tempfile
import subprocess
from unittest.mock import MagicMock, patch, call

# Load projector script as a module
PROJECTOR_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../tools/bin/projector"))
if not os.path.exists(PROJECTOR_PATH):
    raise FileNotFoundError(f"Projector not found at {PROJECTOR_PATH}")

from importlib.machinery import SourceFileLoader
projector = SourceFileLoader("projector", PROJECTOR_PATH).load_module()

class TestProjectorFeatures:
    @pytest.fixture
    def workspace(self):
        # Create a temp workspace
        tmp_dir = tempfile.mkdtemp()
        hologram_dir = os.path.join(tmp_dir, "hologram")
        outside_wall_dir = os.path.join(tmp_dir, "outside_wall")
        os.makedirs(hologram_dir)
        os.makedirs(outside_wall_dir)
        
        # Save CWD and switch to tmp_dir
        old_cwd = os.getcwd()
        os.chdir(tmp_dir)
        
        yield tmp_dir
        
        # Restore CWD and cleanup
        os.chdir(old_cwd)
        shutil.rmtree(tmp_dir)

    @pytest.fixture
    def mock_deps(self):
        with patch('projector.load_config') as mock_conf, \
             patch('projector.run_command') as mock_run, \
             patch('projector.find_project_root') as mock_root, \
             patch('subprocess.check_call') as mock_call, \
             patch('subprocess.Popen') as mock_popen:
            yield mock_conf, mock_run, mock_root, mock_call, mock_popen

    def test_retract_all(self, workspace, mock_deps):
        mock_conf, mock_run, mock_root, mock_call, mock_popen = mock_deps
        
        mock_conf.return_value = {"host_target": "test-host", "remote_root": "/remote"}
        mock_root.return_value = workspace
        
        # Setup: Create multiple files in hologram
        files = ["src/a.c", "src/b.c", "docs/note.md"]
        for f in files:
            p = os.path.join(workspace, "hologram", f)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as fp: fp.write("content")
            
        # Also create config file (should remain)
        with open(os.path.join(workspace, "hologram", ".hologram_config"), "w") as f:
            f.write("{}")

        # Mock remote existence check (check_call succeeds)
        mock_call.return_value = 0
        
        # Mock run_command to simulate verify restoration
        mock_run.return_value = ""

        # Execute
        args = MagicMock()
        args.all = True
        args.file = None
        projector.do_retract(args)
        
        # Verify
        # 1. Content files are gone
        for f in files:
            p = os.path.join(workspace, "hologram", f)
            assert not os.path.exists(p), f"{f} should be retracted"
            
        # 2. Config should remain (or at least we didn't explicitly delete it in logic, 
        #    but os.walk usually hits everything. 
        #    Logic check: `if f == "compile_commands.json" or f == ".hologram_config": continue`
        config_p = os.path.join(workspace, "hologram", ".hologram_config")
        assert os.path.exists(config_p), "Config file should remain"
        
        # 3. Verify loop calls to restore
        # Should call chmod/rsync for each file. 
        # Check run_command calls for restoration
        assert mock_run.call_count >= len(files)

    def test_grep_remote_execution(self, workspace, mock_deps):
        mock_conf, mock_run, mock_root, mock_call, mock_popen = mock_deps
        
        mock_conf.return_value = {"host_target": "user@host", "remote_root": "/remote"}
        mock_root.return_value = workspace
        
        # Mock Popen for grep output
        process_mock = MagicMock()
        # Mock behavior: return regex output line then None (EOF)
        process_mock.stdout.readline.side_effect = [
            "/remote/src/main.c:10: int main() {\n",
            "" 
        ]
        process_mock.returncode = 0
        mock_popen.return_value = process_mock
        
        # Execute
        args = MagicMock()
        args.pattern = "main"
        args.path = None
        
        # Capture print output? 
        # We can just verify the command SENT to Popen.
        projector.do_grep(args)
        
        # Verify Command
        args_list = mock_popen.call_args[0][0]
        cmd_str = args_list[-1]
        
        assert "unset HISTFILE" in cmd_str
        assert "rg --line-number" in cmd_str
        assert "/remote" in cmd_str

    def test_grep_path_rewriting(self, workspace, mock_deps, capsys):
        mock_conf, mock_run, mock_root, mock_call, mock_popen = mock_deps
        
        mock_conf.return_value = {"host_target": "user@host", "remote_root": "/remote"}
        mock_root.return_value = workspace
        
        process_mock = MagicMock()
        process_mock.stdout.readline.side_effect = [
            "/remote/src/main.c:10: match\n",
            "" 
        ]
        process_mock.returncode = 0
        mock_popen.return_value = process_mock
        
        args = MagicMock()
        args.pattern = "match"
        args.path = None
        
        projector.do_grep(args)
        
        # Capture stdout
        captured = capsys.readouterr()
        
        # Expected: /remote replaced by hologram path (workspace/hologram)
        expected_path = os.path.join(workspace, "hologram", "src/main.c")
        assert expected_path in captured.out

    def test_history_hygiene_do_push(self, workspace, mock_deps):
        mock_conf, mock_run, mock_root, mock_call, mock_popen = mock_deps
        
        mock_conf.return_value = {"host_target": "user@host", "remote_root": "/remote"}
        mock_root.return_value = workspace
        
        # Create a local file to push
        p = os.path.join(workspace, "hologram", "test.c")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f: f.write("x")
            
        args = MagicMock()
        args.file = p
        args.trigger = False
        
        projector.do_push(args)
        
        # Check run_command calls
        # Expected: mkdir -p call with unset HISTFILE
        # rsync call (rsync uses -e ssh, which we didn't inject unset HISTFILE into, 
        # but mkdir does).
        
        mkdir_called_with_unset = False
        for call_obj in mock_run.call_args_list:
            cmd_args = call_obj[0][0]
            cmd_str = str(cmd_args)
            if "mkdir -p" in cmd_str:
                if "unset HISTFILE" in cmd_str:
                    mkdir_called_with_unset = True
                    
        assert mkdir_called_with_unset, "mkdir command in do_push should have unset HISTFILE"

