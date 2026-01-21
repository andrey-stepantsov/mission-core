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

# Import projector as a module
# Since it doesn't have .py extension, we use importlib machinery or just rename/symlink
# Simplified: use run_path or exec?
# But we need to test functions.
# Let's try to load it.
import importlib.machinery
import importlib.util

PROJECTOR_PATH = os.path.join(TOOLS_BIN, "projector")
if not os.path.exists(PROJECTOR_PATH):
    # Fallback for when running from root
    PROJECTOR_PATH = os.path.abspath(os.path.join(os.getcwd(), ".mission/tools/bin/projector"))

if not os.path.exists(PROJECTOR_PATH):
    raise FileNotFoundError(f"Cannot find projector at {PROJECTOR_PATH}")

loader = importlib.machinery.SourceFileLoader("projector", PROJECTOR_PATH)
spec = importlib.util.spec_from_loader("projector", loader)
projector = importlib.util.module_from_spec(spec)
loader.exec_module(projector)

class TestProjectorLSP(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.hologram_dir = os.path.join(self.test_dir, "hologram")
        self.outside_wall_dir = os.path.join(self.test_dir, "outside_wall")
        os.makedirs(self.hologram_dir)
        os.makedirs(self.outside_wall_dir)
        
        # Mock constants in projector module
        projector.HOLOGRAM_DIR = "hologram"
        projector.OUTSIDE_WALL_DIR = "outside_wall"
        
        # Mock load_config
        self.mock_config = {
            "host_target": "dummy",
            "remote_root": "/remote/root"
        }
        self.original_load_config = projector.load_config
        projector.load_config = MagicMock(return_value=self.mock_config)
        
        # Mock os.getcwd to return test_dir
        self.cwd_patcher = patch('os.getcwd', return_value=self.test_dir)
        self.mock_getcwd = self.cwd_patcher.start()
        
    def tearDown(self):
        projector.load_config = self.original_load_config
        self.cwd_patcher.stop()
        shutil.rmtree(self.test_dir)

    def test_update_local_compile_db_injects_includes(self):
        # Setup
        context = {
            "directory": "/remote/root/src",
            "file": "/remote/root/src/main.c",
            "arguments": ["gcc", "-c", "main.c"]
        }
        dependencies = [
            "/remote/root/include/my_header.h", # Project header
            "/usr/include/stdio.h",             # System header
            "/usr/local/include/lib.h",         # System header
            "/opt/lib/other.h"                  # System header
        ]
        
        # Run
        projector.update_local_compile_db(context, dependencies)
        
        # Verify
        db_path = os.path.join(self.hologram_dir, "compile_commands.json")
        self.assertTrue(os.path.exists(db_path))
        
        with open(db_path, 'r') as f:
            db = json.load(f)
            
        entry = db[0]
        args = entry["arguments"]
        
        # Verify normal includes (-I)
        # /remote/root/include -> outside_wall/remote/root/include
        expected_project_inc = os.path.join(self.outside_wall_dir, "remote/root/include")
        self.assertIn(f"-I{expected_project_inc}", args)
        
        # Verify system includes (-isystem)
        # /usr/include -> outside_wall/usr/include
        expected_usr_inc = os.path.join(self.outside_wall_dir, "usr/include")
        self.assertIn(f"-isystem{expected_usr_inc}", args)
        
        # /opt/lib -> outside_wall/opt/lib
        expected_opt_inc = os.path.join(self.outside_wall_dir, "opt/lib")
        self.assertIn(f"-isystem{expected_opt_inc}", args)

    def test_update_local_compile_db_rewrites_existing_flags(self):
        # Setup
        context = {
            "directory": "/remote/root/src",
            "file": "/remote/root/src/main.c",
            "arguments": ["gcc", "-I/usr/include", "-I/remote/root/include", "main.c"]
        }
        
        projector.update_local_compile_db(context, [])
        
        # Verify
        db_path = os.path.join(self.hologram_dir, "compile_commands.json")
        with open(db_path, 'r') as f:
            db = json.load(f)
            
        entry = db[0]
        args = entry["arguments"]
        
        # Check rewriting
        expected_usr = os.path.join(self.outside_wall_dir, "usr/include")
        expected_proj = os.path.join(self.outside_wall_dir, "remote/root/include")
        
        self.assertIn(f"-I{expected_usr}", args)
        self.assertIn(f"-I{expected_proj}", args)
        
        # Verify original flags are NOT present (rewritten)
        self.assertNotIn("-I/usr/include", args)


if __name__ == '__main__':
    unittest.main()
