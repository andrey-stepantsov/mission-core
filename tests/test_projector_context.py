import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os
import json
import logging
import io

# Setup path to import projector
TOOLS_BIN = os.path.abspath(os.path.join(os.path.dirname(__file__), '../tools/bin'))
sys.path.append(TOOLS_BIN)

# Dynamically load projector module
import importlib.machinery
import importlib.util

PROJECTOR_PATH = os.path.join(TOOLS_BIN, "projector")
if not os.path.exists(PROJECTOR_PATH):
     # Fallback
     PROJECTOR_PATH = os.path.abspath(os.path.join(os.getcwd(), ".mission/tools/bin/projector"))

loader = importlib.machinery.SourceFileLoader("projector", PROJECTOR_PATH)
spec = importlib.util.spec_from_loader("projector", loader)
projector = importlib.util.module_from_spec(spec)
loader.exec_module(projector)

class TestProjectorContext(unittest.TestCase):
    def setUp(self):
        # Create temp dir
        import tempfile
        import shutil
        self.test_dir = tempfile.mkdtemp()
        
        # Capture stdout
        self.held_stdout = io.StringIO()
        self.stdout_patcher = patch('sys.stdout', self.held_stdout)
        self.stdout_patcher.start()
        
        # Mock load_config
        self.mock_config = {
            "host_target": "dummy_host",
            "remote_root": "/remote/root"
        }
        self.config_patcher = patch.object(projector, 'load_config', return_value=self.mock_config)
        self.config_patcher.start()
        
        # Mock run_command
        self.run_command_patcher = patch.object(projector, 'run_command')
        self.mock_run_command = self.run_command_patcher.start()
        
        # Mock update_local_compile_db
        self.update_db_patcher = patch.object(projector, 'update_local_compile_db')
        self.mock_update_db = self.update_db_patcher.start()

    def tearDown(self):
        self.stdout_patcher.stop()
        self.config_patcher.stop()
        self.run_command_patcher.stop()
        self.update_db_patcher.stop()
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_pull_ambiguous_context_warning(self):
        """
        Verifies that when auto_ghost returns multiple candidates,
        projector warns the user and defaults to the first one.
        """
        # Mock Args
        args = MagicMock()
        args.file = "test.c"
        args.flags = None # No flags provided
        
        # Mock auto_ghost response
        # It detects 2 candidates
        candidates = [
            {
                "cmd_str": "gcc -DVARIANT_A -c test.c",
                "entry": {"directory": "/build/a", "command": "gcc -DVARIANT_A -c test.c", "file": "test.c"},
                "score": 0
            },
            {
                "cmd_str": "gcc -DVARIANT_B -c test.c",
                "entry": {"directory": "/build/b", "command": "gcc -DVARIANT_B -c test.c", "file": "test.c"},
                "score": 0
            }
        ]
        
        mock_response = {
            "dependencies": ["/remote/root/dep.h"],
            "compile_context": {
                "candidates": candidates,
                # Legacy fields might still be populated by updated tool, effectively "best match"
                "directory": "/build/a",
                "command": "gcc -DVARIANT_A -c test.c",
                "file": "test.c"
            }
        }
        
        # Setup run_command to return this JSON when auto_ghost is called
        # The first call is usually ssh test -f, second is rsync...
        # We need to target the specific call that runs auto_ghost
        def side_effect(cmd, **kwargs):
            cmd_str = " ".join(cmd)
            if "auto_ghost" in cmd_str:
                return json.dumps(mock_response)
            return ""
            
        self.mock_run_command.side_effect = side_effect
        
        # Run do_pull
        projector.do_pull(args)
        
        # Check Output for Warning
        output = self.held_stdout.getvalue()
        self.assertIn("⚠️  Ambiguous compilation context", output)
        self.assertIn("DVARIANT_A", output) # Should list options
        self.assertIn("DVARIANT_B", output)
        self.assertIn("Defaulting to Candidate #1", output)
        
        # Verify update_local_compile_db was called with the first candidate
        self.mock_update_db.assert_called()
        context_arg = self.mock_update_db.call_args[0][0]
        self.assertEqual(context_arg["directory"], "/build/a")

    def test_pull_with_flags_propagates_to_remote(self):
        """
        Verifies that --flags is passed to the remote auto_ghost command.
        """
        args = MagicMock()
        args.file = "test.c"
        args.flags = "-DVARIANT_B"
        
        # When flags are provided, we expect the remote tool to return just the winner (or sorted list)
        # But crucially we just want to check the command line invocation.
        
        mock_response = {
            "dependencies": [],
            "compile_context": {
                "candidates": [
                    {
                        "cmd_str": "gcc -DVARIANT_B -c test.c",
                        "entry": {"directory": "/build/b", "command": "gcc -DVARIANT_B -c test.c", "file": "test.c"},
                        "score": 10
                    }
                ]
            }
        }
        
        def side_effect(cmd, **kwargs):
            cmd_list = cmd if isinstance(cmd, list) else []
            # Check arguments in the ssh command string
            # The structure is ["ssh", ..., "host", "unset HISTFILE; ... auto_ghost ..."]
            full_cmd = cmd_list[-1] 
            
            if "auto_ghost" in full_cmd:
                # ASSERTION: Check flags are present
                # Accept both quoted and unquoted forms just in case
                if "--flags '-DVARIANT_B'" not in full_cmd and '--flags "-DVARIANT_B"' not in full_cmd and '--flags -DVARIANT_B' not in full_cmd and "--flags=-DVARIANT_B" not in full_cmd:
                     # Raise error to fail test inside side_effect isn't ideal but works
                     raise ValueError(f"Flags not found in command: {full_cmd}")
                     
                return json.dumps(mock_response)
            return ""
            
        self.mock_run_command.side_effect = side_effect
        
        projector.do_pull(args)
        
        # Verify no warning since it filtered successfully (mocked response has 1 candidate)
        output = self.held_stdout.getvalue()
        self.assertNotIn("Ambiguous compilation context", output)
        self.mock_update_db.assert_called()

    def test_context_command_output(self):
        """
        Verifies that projector context prints correct YAML output from compile_commands.json.
        """
        args = MagicMock()
        args.file = os.path.join(self.test_dir, "hologram/src/main.c")
        
        # Setup Fake Hologram
        hologram_dir = os.path.join(self.test_dir, "hologram")
        os.makedirs(os.path.join(hologram_dir, "src"), exist_ok=True)
        db_path = os.path.join(hologram_dir, "compile_commands.json")
        
        # Write Mock DB
        mock_db = [
            {
                "directory": hologram_dir,
                "file": args.file,
                "command": "gcc -DDEBUG -I/outside/include -isystem /usr/include -std=c99 -c main.c -o main.o"
            }
        ]
        with open(db_path, 'w') as f:
            json.dump(mock_db, f)

        # Mock find_project_root to return test_dir
        with patch.object(projector, 'find_project_root', return_value=self.test_dir):
            # Run do_context
            try:
                projector.do_context(args)
            except SystemExit:
                 pass # It shouldn't exit on success, but just in case
        
        # Verify Output
        output = self.held_stdout.getvalue()
        self.assertIn("File: hologram/src/main.c", output)
        self.assertIn("Standard: c99", output)
        self.assertIn("- DEBUG", output)
        self.assertIn("- /outside/include", output)
        self.assertIn("- /usr/include", output)

if __name__ == '__main__':
    unittest.main()
