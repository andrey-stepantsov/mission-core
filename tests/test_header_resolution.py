import sys
import os
import json
import unittest
import tempfile
import shutil
from unittest.mock import MagicMock, patch

# Add tools/bin to path to import projector
TOOLS_BIN = os.path.abspath(os.path.join(os.path.dirname(__file__), '../tools/bin'))
sys.path.append(TOOLS_BIN)

import importlib.machinery
import importlib.util

PROJECTOR_PATH = os.path.join(TOOLS_BIN, "projector")
if not os.path.exists(PROJECTOR_PATH):
    PROJECTOR_PATH = os.path.abspath(os.path.join(os.getcwd(), ".mission/tools/bin/projector"))

if not os.path.exists(PROJECTOR_PATH):
    raise FileNotFoundError(f"Cannot find projector at {PROJECTOR_PATH}")

loader = importlib.machinery.SourceFileLoader("projector", PROJECTOR_PATH)
spec = importlib.util.spec_from_loader("projector", loader)
projector = importlib.util.module_from_spec(spec)
loader.exec_module(projector)

class TestHeaderResolution(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.hologram_dir = os.path.join(self.test_dir, "hologram")
        self.outside_wall_dir = os.path.join(self.test_dir, "outside_wall")
        os.makedirs(self.hologram_dir)
        os.makedirs(self.outside_wall_dir)
        
        # Mock constants
        projector.HOLOGRAM_DIR = "hologram"
        projector.OUTSIDE_WALL_DIR = "outside_wall"
        
        # Mock config
        self.mock_config = {
            "host_target": "dummy",
            "remote_root": "/remote",
            "system_includes": ["/usr/include", "/opt/lib"]
        }
        self.original_load_config = projector.load_config
        projector.load_config = MagicMock(return_value=self.mock_config)
        
        self.cwd_patcher = patch('os.getcwd', return_value=self.test_dir)
        self.mock_getcwd = self.cwd_patcher.start()

    def tearDown(self):
        projector.load_config = self.original_load_config
        self.cwd_patcher.stop()
        shutil.rmtree(self.test_dir)

    def test_parses_command_string_when_arguments_missing(self):
        """Regression test for dropped flags when c_context returns 'command' string but no 'arguments' list."""
        context = {
            "directory": "/remote/src",
            "file": "/remote/src/main.c",
            "command": "gcc -I/remote/include -isystem /usr/include -c main.c" # Single string
            # "arguments" missing
        }
        dependencies = []

        # Run
        projector.update_local_compile_db(context, dependencies)

        # Verify
        db_path = os.path.join(self.hologram_dir, "compile_commands.json")
        with open(db_path, 'r') as f:
            db = json.load(f)

        entry = db[0]
        args = entry["arguments"]
        
        # Arguments should be parsed from string and path-rewritten
        expected_proj = os.path.join(self.outside_wall_dir, "remote/include")
        expected_usr = os.path.join(self.outside_wall_dir, "usr/include")
        
        self.assertIn(f"-I{expected_proj}", args)
        # -isystem is split
        self.assertIn("-isystem", args)
        self.assertIn(expected_usr, args)

    def test_injects_system_includes_from_config(self):
        """Verifies that system includes stored in config (via repair-headers) are injected."""
        context = {
            "directory": "/remote/src",
            "file": "/remote/src/main.c",
            "arguments": ["gcc", "main.c"] # Missing system includes
        }
        
        # Run
        projector.update_local_compile_db(context, [])
        
        # Verify
        db_path = os.path.join(self.hologram_dir, "compile_commands.json")
        with open(db_path, 'r') as f:
            db = json.load(f)
            
        entry = db[0]
        args = entry["arguments"]
        
        expected_usr = os.path.join(self.outside_wall_dir, "usr/include")
        expected_opt = os.path.join(self.outside_wall_dir, "opt/lib")
        
        self.assertIn("-isystem", args)
        self.assertIn(expected_usr, args)
        self.assertIn(expected_opt, args)

if __name__ == '__main__':
    unittest.main()
