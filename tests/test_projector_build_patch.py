
import os
import sys
import json
import unittest
import tempfile
import shutil
from unittest.mock import MagicMock, patch

TOOLS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../tools'))
if TOOLS_ROOT not in sys.path:
    sys.path.append(TOOLS_ROOT)

from projector.commands.build import do_build

class TestProjectorBuildPatch(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.hologram_dir = os.path.join(self.tmp_dir, "hologram")
        self.ddd_dir = os.path.join(self.hologram_dir, ".ddd")
        os.makedirs(self.ddd_dir)
        
        self.config_path = os.path.join(self.ddd_dir, "config.json")
        self.initial_config = {
            "targets": {
                "dev": {
                    "build": {"cmd": "make"},
                    "verify": {"cmd": "test"}
                }
            }
        }
        with open(self.config_path, "w") as f:
            json.dump(self.initial_config, f)
            
        self.old_cwd = os.getcwd()
        os.chdir(self.tmp_dir)
        
        # Patching
        self.root_patcher = patch('projector.commands.build.find_project_root', return_value=self.tmp_dir)
        self.conf_patcher = patch('projector.commands.build.load_config', return_value={"host_target": "test", "remote_root": "/r"})
        self.push_patcher = patch('projector.commands.sync.do_push')
        self.trigger_patcher = patch('projector.commands.build.trigger_build')
        self.context_patcher = patch('projector.commands.build.find_build_context', return_value=None)
        
        self.mock_root = self.root_patcher.start()
        self.mock_conf = self.conf_patcher.start()
        self.mock_push = self.push_patcher.start()
        self.mock_trigger = self.trigger_patcher.start()
        self.mock_context = self.context_patcher.start()

    def tearDown(self):
        self.root_patcher.stop()
        self.conf_patcher.stop()
        self.push_patcher.stop()
        self.trigger_patcher.stop()
        self.context_patcher.stop()
        
        os.chdir(self.old_cwd)
        shutil.rmtree(self.tmp_dir)

    def test_build_flag_patching(self):
        args = MagicMock()
        args.build = "echo 'New Build'"
        args.verify = None
        args.context_from = None
        args.sync = None
        args.path = None
        args.wait = False
        
        do_build(args)
        
        # Verify Config Update
        with open(self.config_path, "r") as f:
            new_config = json.load(f)
            
        self.assertEqual(new_config['targets']['dev']['build']['cmd'], "echo 'New Build'")
        self.assertEqual(new_config['targets']['dev']['verify']['cmd'], "test") # Unchanged
        
        # Verify Push
        self.assertTrue(self.mock_push.called)
        push_args = self.mock_push.call_args[0][0]
        self.assertEqual(push_args.file, self.config_path)
        
        # Verify Trigger
        self.assertTrue(self.mock_trigger.called)

    def test_verify_flag_patching(self):
        args = MagicMock()
        args.build = None
        args.verify = "pytest specific_test.py"
        args.context_from = None
        args.sync = None
        args.path = None
        args.wait = False
        
        do_build(args)
        
        with open(self.config_path, "r") as f:
            new_config = json.load(f)
            
        self.assertEqual(new_config['targets']['dev']['build']['cmd'], "make") # Unchanged
        self.assertEqual(new_config['targets']['dev']['verify']['cmd'], "pytest specific_test.py")

        self.assertTrue(self.mock_push.called)
        self.assertTrue(self.mock_trigger.called)

    def test_both_flags_patching(self):
        args = MagicMock()
        args.build = "gcc main.c"
        args.verify = "./a.out"
        args.context_from = None
        args.sync = None
        args.path = None
        args.wait = False
        
        do_build(args)
        
        with open(self.config_path, "r") as f:
            new_config = json.load(f)
            
        self.assertEqual(new_config['targets']['dev']['build']['cmd'], "gcc main.c")
        self.assertEqual(new_config['targets']['dev']['verify']['cmd'], "./a.out")
        
        self.assertTrue(self.mock_push.called)

    def test_path_flag_patching(self):
        # Create a subdir in hologram
        subdir = os.path.join(self.hologram_dir, "tests")
        os.makedirs(subdir)
        
        args = MagicMock()
        args.build = None
        args.verify = "pytest"
        args.context_from = None
        args.sync = None
        args.path = subdir
        args.wait = False
        
        # We need mock_context to return None so that it thinks we are in Root Context
        # But we pass subdir as path.
        # find_build_context(hologram, subdir) -> None (defaults to root)
        
        do_build(args)
        
        with open(self.config_path, "r") as f:
            new_config = json.load(f)
            
        # Expect prepended cd
        self.assertEqual(new_config['targets']['dev']['verify']['cmd'], "cd tests && pytest")
        self.assertTrue(self.mock_push.called)

if __name__ == '__main__':
    unittest.main()
