import sys
import os
import json
import unittest
import tempfile
import shutil
from unittest.mock import MagicMock, patch

# Add tools/ to path
TOOLS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../tools'))
if TOOLS_ROOT not in sys.path:
    sys.path.append(TOOLS_ROOT)

import projector.core.config
from projector.internal.compile_db import update_local_compile_db

class TestProjectorLSP(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.hologram_dir = os.path.join(self.test_dir, "hologram")
        self.outside_wall_dir = os.path.join(self.test_dir, "outside_wall")
        os.makedirs(self.hologram_dir)
        os.makedirs(self.outside_wall_dir)
        
        # Mock constants in core.config module
        # We need to patch them for the duration of the test
        self.hologram_patcher = patch('projector.internal.compile_db.HOLOGRAM_DIR', 'hologram')
        self.wall_patcher = patch('projector.internal.compile_db.OUTSIDE_WALL_DIR', 'outside_wall')
        # Also need to patch usage of os.getcwd in compile_db to return test_dir
        self.cwd_patcher = patch('os.getcwd', return_value=self.test_dir)
        
        self.hologram_patcher.start()
        self.wall_patcher.start()
        self.mock_getcwd = self.cwd_patcher.start()
        
        # Mock load_config
        self.mock_config = {
            "host_target": "dummy",
            "remote_root": "/remote/root"
        }
        # compile_db imports load_config from core.config, so we patch it there
        self.config_patcher = patch('projector.internal.compile_db.load_config', return_value=self.mock_config)
        self.config_patcher.start()
        
    def tearDown(self):
        self.hologram_patcher.stop()
        self.wall_patcher.stop()
        self.cwd_patcher.stop()
        self.config_patcher.stop()
        shutil.rmtree(self.test_dir)

    def test_update_local_compile_db_injects_includes(self):
        # Setup
        context = {
            "directory": "/remote/root/src",
            "file": "/remote/root/src/main.c",
            "arguments": ["gcc", "-c", "main.c"]
        }
        dependencies = [
            "/remote/root/include/my_header.h", 
            "/usr/include/stdio.h",             
            "/usr/local/include/lib.h",         
            "/opt/lib/other.h"                  
        ]
        
        # Run
        update_local_compile_db(context, dependencies)
        
        # Verify
        db_path = os.path.join(self.hologram_dir, "compile_commands.json")
        self.assertTrue(os.path.exists(db_path))
        
        with open(db_path, 'r') as f:
            db = json.load(f)
            
        entry = db[0]
        args = entry["arguments"]
        
        # Verify normal includes (-I)
        expected_project_inc = os.path.join(self.outside_wall_dir, "remote/root/include")
        self.assertIn(f"-I{expected_project_inc}", args)
        
        # Verify system includes (-isystem)
        expected_usr_inc = os.path.join(self.outside_wall_dir, "usr/include")
        self.assertIn("-isystem", args)
        
        expected_opt_inc = os.path.join(self.outside_wall_dir, "opt/lib")
        # Check that -isystem and path are adjacent
        indices = [i for i, x in enumerate(args) if x == "-isystem"]
        found_usr = False
        found_opt = False
        for idx in indices:
            if idx + 1 < len(args):
                if args[idx+1] == expected_usr_inc: found_usr = True
                if args[idx+1] == expected_opt_inc: found_opt = True
        
        self.assertTrue(found_usr, f"Could not find -isystem followed by {expected_usr_inc}")
        self.assertTrue(found_opt, f"Could not find -isystem followed by {expected_opt_inc}")

    def test_update_local_compile_db_rewrites_existing_flags(self):
        # Setup
        context = {
            "directory": "/remote/root/src",
            "file": "/remote/root/src/main.c",
            "arguments": ["gcc", "-I/usr/include", "-I/remote/root/include", "main.c"]
        }
        
        update_local_compile_db(context, [])
        
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
