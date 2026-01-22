
import os
import sys

import shutil
import tempfile
import subprocess
from unittest.mock import MagicMock, patch, call

# Load projector package
TOOLS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../tools'))
if TOOLS_ROOT not in sys.path:
    sys.path.append(TOOLS_ROOT)

import projector.core.config
import projector.core.transport
import projector.main
from projector.commands.sync import do_retract, do_push
from projector.commands.misc import do_grep

import os
import sys
import unittest
import shutil
import tempfile
import subprocess
import io
from unittest.mock import MagicMock, patch, call

# Load projector package
TOOLS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../tools'))
if TOOLS_ROOT not in sys.path:
    sys.path.append(TOOLS_ROOT)

import projector.core.config
import projector.core.transport
import projector.main
from projector.commands.sync import do_retract, do_push
from projector.commands.misc import do_grep

class TestProjectorFeatures(unittest.TestCase):
    def setUp(self):
        # Create a temp workspace
        self.tmp_dir = tempfile.mkdtemp()
        self.hologram_dir = os.path.join(self.tmp_dir, "hologram")
        self.outside_wall_dir = os.path.join(self.tmp_dir, "outside_wall")
        os.makedirs(self.hologram_dir)
        os.makedirs(self.outside_wall_dir)
        
        # Save CWD and switch to tmp_dir
        self.old_cwd = os.getcwd()
        os.chdir(self.tmp_dir)
        
        # Patch dependencies
        self.config_patcher = patch('projector.core.config.load_config')
        self.run_patcher = patch('projector.core.transport.run_command')
        self.root_patcher = patch('projector.core.config.find_project_root')
        self.call_patcher = patch('subprocess.check_call')
        self.popen_patcher = patch('subprocess.Popen')
        
        # Also patch command modules usage of config/run if different?
        # do_retract uses load_config (core), find_project_root (core/cmds -> usually imported from core)
        # We need to match where inputs come from.
        # do_retract imports find_project_root from ..core.config
        # So we patch projector.commands.sync.find_project_root ?
        # Or projector.core.config.find_project_root? 
        # If do_retract does `from ..core.config import find_project_root`, it binds local name.
        # So we MUST patch `projector.commands.sync.find_project_root`.
        # Same for do_grep using find_project_root.
        
        # Let's start generic patches and refine if needed.
        self.mock_conf = self.config_patcher.start()
        self.mock_run = self.run_patcher.start()
        self.mock_root = self.root_patcher.start()
        self.mock_call = self.call_patcher.start()
        self.mock_popen = self.popen_patcher.start()
        
        # Need to patch local imports in commands modules too
        self.sync_root_patcher = patch('projector.commands.sync.find_project_root', return_value=self.tmp_dir)
        self.sync_conf_patcher = patch('projector.commands.sync.load_config')
        
        self.misc_root_patcher = patch('projector.commands.misc.find_project_root', return_value=self.tmp_dir)
        self.misc_conf_patcher = patch('projector.commands.misc.load_config')

        self.mock_sync_root = self.sync_root_patcher.start()
        self.mock_sync_conf = self.sync_conf_patcher.start()
        
        self.mock_misc_root = self.misc_root_patcher.start()
        self.mock_misc_conf = self.misc_conf_patcher.start()
        
        # Also do_push uses run_command from ..core.transport
        # So patch projector.commands.sync.run_command
        self.sync_run_patcher = patch('projector.commands.sync.run_command')
        self.mock_sync_run = self.sync_run_patcher.start()
        
    def tearDown(self):
        self.config_patcher.stop()
        self.run_patcher.stop()
        self.root_patcher.stop()
        self.call_patcher.stop()
        self.popen_patcher.stop()
        self.sync_root_patcher.stop()
        self.sync_conf_patcher.stop()
        self.misc_root_patcher.stop()
        self.misc_conf_patcher.stop()
        self.sync_run_patcher.stop()
        
        os.chdir(self.old_cwd)
        shutil.rmtree(self.tmp_dir)

    def test_retract_all(self):
        self.mock_sync_conf.return_value = {"host_target": "test-host", "remote_root": "/remote"}
        self.mock_sync_root.return_value = self.tmp_dir
        
        # Setup: Create multiple files in hologram
        files = ["src/a.c", "src/b.c", "docs/note.md"]
        for f in files:
            p = os.path.join(self.hologram_dir, f)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as fp: fp.write("content")
            
        # Also create config file (should remain)
        with open(os.path.join(self.hologram_dir, ".hologram_config"), "w") as f:
            f.write("{}")

        # Mock remote existence check (check_call succeeds)
        self.mock_call.return_value = 0
        
        # Mock run_command to simulate verify restoration
        self.mock_sync_run.return_value = ""

        # Execute
        args = MagicMock()
        args.all = True
        args.file = None
        do_retract(args)
        
        # Verify
        # 1. Content files are gone
        for f in files:
            p = os.path.join(self.hologram_dir, f)
            assert not os.path.exists(p), f"{f} should be retracted"
            
        # 2. Config should remain
        config_p = os.path.join(self.hologram_dir, ".hologram_config")
        assert os.path.exists(config_p), "Config file should remain"
        
        # 3. Verify loop calls to restore
        assert self.mock_sync_run.call_count >= len(files)

    def test_grep_remote_execution(self):
        self.mock_misc_conf.return_value = {"host_target": "user@host", "remote_root": "/remote"}
        self.mock_misc_root.return_value = self.tmp_dir
        
        # Mock Popen for grep output
        process_mock = MagicMock()
        # Mock behavior: return regex output line then None (EOF)
        process_mock.stdout.readline.side_effect = [
            "/remote/src/main.c:10: int main() {\n",
            "" 
        ]
        process_mock.returncode = 0
        self.mock_popen.return_value = process_mock
        
        # Execute
        args = MagicMock()
        args.pattern = "main"
        args.path = None
        
        do_grep(args)
        
        # Verify Command
        args_list = self.mock_popen.call_args[0][0]
        cmd_str = args_list[-1]
        
        self.assertIn("unset HISTFILE", cmd_str)
        self.assertIn("rg --line-number", cmd_str)
        self.assertIn("/remote", cmd_str)

    def test_grep_path_rewriting(self):
        self.mock_misc_conf.return_value = {"host_target": "user@host", "remote_root": "/remote"}
        self.mock_misc_root.return_value = self.tmp_dir
        
        process_mock = MagicMock()
        process_mock.stdout.readline.side_effect = [
            "/remote/src/main.c:10: match\n",
            "" 
        ]
        process_mock.returncode = 0
        self.mock_popen.return_value = process_mock
        
        args = MagicMock()
        args.pattern = "match"
        args.path = None
        
        # Capture stdout
        held_stdout = io.StringIO()
        with patch('sys.stdout', held_stdout):
            do_grep(args)
        
        output = held_stdout.getvalue()
        
        # Expected: /remote replaced by hologram path (workspace/hologram)
        expected_path = os.path.join(self.tmp_dir, "hologram", "src/main.c")
        self.assertIn(expected_path, output)

    def test_history_hygiene_do_push(self):
        self.mock_sync_conf.return_value = {"host_target": "user@host", "remote_root": "/remote"}
        self.mock_sync_root.return_value = self.tmp_dir
        
        # Create a local file to push
        p = os.path.join(self.hologram_dir, "test.c")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f: f.write("x")
            
        args = MagicMock()
        args.file = p
        args.trigger = False
        
        do_push(args)
        
        # Check run_command calls
        # Expected: mkdir -p call with unset HISTFILE
        mkdir_called_with_unset = False
        for call_obj in self.mock_sync_run.call_args_list:
            cmd_args = call_obj[0][0]
            cmd_str = str(cmd_args)
            if "mkdir -p" in cmd_str:
                if "unset HISTFILE" in cmd_str:
                    mkdir_called_with_unset = True
                    
        self.assertTrue(mkdir_called_with_unset, "mkdir command in do_push should have unset HISTFILE")

if __name__ == '__main__':
    unittest.main()
