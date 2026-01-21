
import os
import sys
import pytest
import shutil
import tempfile
import importlib.util
from unittest.mock import MagicMock, patch

# Load projector script as a module
PROJECTOR_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../tools/bin/projector"))
if not os.path.exists(PROJECTOR_PATH):
    raise FileNotFoundError(f"Projector not found at {PROJECTOR_PATH}")

from importlib.machinery import SourceFileLoader
projector = SourceFileLoader("projector", PROJECTOR_PATH).load_module()

class TestProjectorOverlay:
    @pytest.fixture
    def workspace(self):
        # Create a temp workspace
        tmp_dir = tempfile.mkdtemp()
        hologram_dir = os.path.join(tmp_dir, "hologram")
        outside_wall_dir = os.path.join(tmp_dir, "outside_wall")
        os.makedirs(hologram_dir)
        os.makedirs(outside_wall_dir)
        
        # Save CWD and switch to tmp_dir because projector assumes CWD is project root
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
             patch('subprocess.check_call') as mock_call:
            yield mock_conf, mock_run, mock_root, mock_call

    def test_pull_hides_from_outside_wall(self, workspace, mock_deps):
        mock_conf, mock_run, mock_root, mock_call = mock_deps
        
        # Setup Config & Root
        mock_conf.return_value = {"host_target": "test-host", "remote_root": "/remote"}
        mock_root.return_value = workspace
        
        # Setup Initial State: File in outside_wall
        rel_path = "src/foo.h"
        wall_path = os.path.join(workspace, "outside_wall", rel_path)
        os.makedirs(os.path.dirname(wall_path), exist_ok=True)
        with open(wall_path, "w") as f:
            f.write("base content")
            
        assert os.path.exists(wall_path)
        
        # Setup Mock: pull simulates rsync by creating the hologram file
        def side_effect_run(cmd, *args, **kwargs):
            # If rsyncing to hologram, create the file
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
            
            # The real command: rsync -az -e ... host:path local_dest
            # We check if local_dest is in hologram dir
            if "rsync" in cmd_str:
                dest = cmd[-1]
                if "hologram" in dest:
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with open(dest, "w") as f:
                        f.write("pulled content")
            return ""
            
        mock_run.side_effect = side_effect_run

        # execute PULL
        args = MagicMock()
        args.file = rel_path
        projector.do_pull(args)
        
        # VERIFY:
        hologram_path = os.path.join(workspace, "hologram", rel_path)
        
        # 1. File should be in hologram
        assert os.path.exists(hologram_path)
        # 2. File should be GONE from outside_wall
        assert not os.path.exists(wall_path), "File should be hidden (removed) from outside_wall after pull"

    def test_retract_restores_to_outside_wall(self, workspace, mock_deps):
        mock_conf, mock_run, mock_root, mock_call = mock_deps
        
        # Setup Config & Root
        mock_conf.return_value = {"host_target": "test-host", "remote_root": "/remote"}
        mock_root.return_value = workspace
        
        # Setup Initial State: File in hologram, NOT in outside_wall
        rel_path = "src/foo.h"
        hologram_path = os.path.join(workspace, "hologram", rel_path)
        wall_path = os.path.join(workspace, "outside_wall", rel_path)
        
        os.makedirs(os.path.dirname(hologram_path), exist_ok=True)
        with open(hologram_path, "w") as f:
            f.write("overlay content")
            
        assert os.path.exists(hologram_path)
        assert not os.path.exists(wall_path)
        
        # Mocking
        # do_retract calls subprocess.check_call to verify remote file.
        # It calls run_command to rsync back.
        
        def side_effect_run(cmd, *args, **kwargs):
            # If rsyncing to outside_wall, create the file
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
            if "rsync" in cmd_str and "outside_wall" in cmd_str:
                dest = cmd[-1] # Simplistic arg parsing
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "w") as f:
                    f.write("restored base content")
                return True # truthy return needed
            return ""
        
        mock_run.side_effect = side_effect_run

        # Execute RETRACT
        args = MagicMock()
        # Argument passed to retract is LOCAL path
        args.file = hologram_path # projector logic uses absolute or relative path
        
        projector.do_retract(args)
        
        # VERIFY:
        # 1. File should be GONE from hologram
        assert not os.path.exists(hologram_path), "File should be removed from hologram"
        # 2. File should be RESTORED to outside_wall
        assert os.path.exists(wall_path), "File should be restored to outside_wall"
        
        # 3. Permissions (Read Only)
        # We can't easily assert chmod 444 in temp, but we can verify chmod was called if we mocked os.chmod
        # But for now, existence is the key logic check.

