
import os
import sys
import unittest
import shutil
import tempfile
from unittest.mock import MagicMock, patch

# Load projector package
TOOLS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../tools'))
if TOOLS_ROOT not in sys.path:
    sys.path.append(TOOLS_ROOT)

import projector.core.config
import projector.core.transport
from projector.commands.sync import do_pull, do_retract

class TestProjectorOverlay(unittest.TestCase):
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
        # do_pull uses load_config (sync.py) -> load_config (core.config)
        # do_pull uses run_command (sync.py) -> run_command (core.transport)
        # do_pull uses find_project_root (sync.py) -> find_project_root (core.config)
        
        # Since sync.py imports them:
        # from ..core.config import load_config...
        # We can try patching them at source if sync module isn't loaded yet, or patch at sync module.
        # Patching at source is safer if we import `projector.commands.sync` which binds them.
        
        self.config_patcher = patch('projector.commands.sync.load_config')
        self.run_patcher = patch('projector.commands.sync.run_command')
        self.call_patcher = patch('subprocess.check_call') # used in do_retract (subprocess calls)
        
        self.mock_conf = self.config_patcher.start()
        self.mock_run = self.run_patcher.start()
        self.mock_call = self.call_patcher.start()
        
    def tearDown(self):
        self.config_patcher.stop()
        self.run_patcher.stop()
        self.call_patcher.stop()
        os.chdir(self.old_cwd)
        shutil.rmtree(self.tmp_dir)

    def test_pull_hides_from_outside_wall(self):
        # Setup Config
        self.mock_conf.return_value = {"host_target": "test-host", "remote_root": "/remote"}
        
        # Setup Initial State: File in outside_wall
        rel_path = "src/foo.h"
        wall_path = os.path.join(self.outside_wall_dir, rel_path)
        os.makedirs(os.path.dirname(wall_path), exist_ok=True)
        with open(wall_path, "w") as f:
            f.write("base content")
            
        self.assertTrue(os.path.exists(wall_path))
        
        # Setup Mock: pull simulates rsync by creating the hologram file
        def side_effect_run(cmd, *args, **kwargs):
             # The real command: rsync -az -e ... host:path local_dest
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
            
            if "rsync" in cmd_str:
                dest = cmd[-1]
                if "hologram" in dest:
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with open(dest, "w") as f:
                        f.write("pulled content")
            return ""
            
        self.mock_run.side_effect = side_effect_run

        # execute PULL
        args = MagicMock()
        args.file = rel_path
        args.flags = None
        
        # We need to ensure HOLOGRAM_DIR / OUTSIDE_WALL_DIR are correct in sync module
        # They are imported constants. We can patch them or just rely on them being relative to CWD.
        # Since setUp sets CWD to temp dir, and constants are strings "hologram", "outside_wall"
        # it should just work.
        
        # BUT do_pull uses `load_config` which we patched.
        
        do_pull(args)
        
        # VERIFY:
        hologram_path = os.path.join(self.hologram_dir, rel_path)
        
        # 1. File should be in hologram
        self.assertTrue(os.path.exists(hologram_path))
        # 2. File should be GONE from outside_wall
        self.assertFalse(os.path.exists(wall_path), "File should be hidden (removed) from outside_wall after pull")

    def test_retract_restores_to_outside_wall(self):
        # Setup Config
        self.mock_conf.return_value = {"host_target": "test-host", "remote_root": "/remote"}
        
        # Setup Initial State: File in hologram, NOT in outside_wall
        rel_path = "src/foo.h"
        hologram_path = os.path.join(self.hologram_dir, rel_path)
        wall_path = os.path.join(self.outside_wall_dir, rel_path)
        
        os.makedirs(os.path.dirname(hologram_path), exist_ok=True)
        with open(hologram_path, "w") as f:
            f.write("overlay content")
            
        self.assertTrue(os.path.exists(hologram_path))
        self.assertFalse(os.path.exists(wall_path))
        
        # Mocking
        def side_effect_run(cmd, *args, **kwargs):
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
            if "rsync" in cmd_str and "outside_wall" in cmd_str:
                dest = cmd[-1] # Simplistic arg parsing
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "w") as f:
                    f.write("restored base content")
                return True 
            return ""
        
        self.mock_run.side_effect = side_effect_run
        
        # We need to patch find_project_root in sync module to return tmp_dir
        with patch('projector.commands.sync.find_project_root', return_value=self.tmp_dir):
            # Execute RETRACT
            args = MagicMock()
            args.file = hologram_path
            
            do_retract(args)
        
        # VERIFY:
        # 1. File should be GONE from hologram
        self.assertFalse(os.path.exists(hologram_path), "File should be removed from hologram")
        # 2. File should be RESTORED to outside_wall
        self.assertTrue(os.path.exists(wall_path), "File should be restored to outside_wall")

if __name__ == '__main__':
    unittest.main()
