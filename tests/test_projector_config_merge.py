import unittest
import os
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock
import sys

# Setup path to import projector package
TOOLS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../tools'))
if TOOLS_ROOT not in sys.path:
    sys.path.append(TOOLS_ROOT)

from projector.commands.init import deploy_vscode_config

class TestProjectorConfigMerge(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.vscode_dir = os.path.join(self.test_dir, ".vscode")
        os.makedirs(self.vscode_dir)
        
        # Mock CWD to test_dir
        self.cwd_patcher = patch('os.getcwd', return_value=self.test_dir)
        self.mock_cwd = self.cwd_patcher.start()
        
        # Mock template source finding
        # We'll create a fake template dir
        self.template_dir = os.path.join(self.test_dir, ".mission/templates/vscode")
        os.makedirs(self.template_dir)

    def tearDown(self):
        self.cwd_patcher.stop()
        shutil.rmtree(self.test_dir)

    def test_merge_settings_json(self):
        # 1. Create Template
        template_settings = {
            "clangd.arguments": ["--log=verbose", "--background-index"],
            "python.analysis.extraPaths": ["tools"]
        }
        with open(os.path.join(self.template_dir, "settings.json"), "w") as f:
            json.dump(template_settings, f)
            
        # 2. Create Existing User Config
        user_settings = {
            "clangd.arguments": ["--header-insertion=never"], # User has one preference
            "editor.fontSize": 14
        }
        with open(os.path.join(self.vscode_dir, "settings.json"), "w") as f:
            json.dump(user_settings, f)
            
        # 3. Run Deploy with explicit template_dir
        deploy_vscode_config("/remote", template_dir=self.template_dir)
        
        # 4. Verify Merge
        with open(os.path.join(self.vscode_dir, "settings.json"), "r") as f:
            merged = json.load(f)
            
        # Check defaults preserved
        self.assertEqual(merged["editor.fontSize"], 14)
        
        # Check new keys added
        self.assertEqual(merged["python.analysis.extraPaths"], ["tools"])
        
        # Check list merge
        args = merged["clangd.arguments"]
        self.assertIn("--header-insertion=never", args) # User's
        self.assertIn("--log=verbose", args)          # Template's
        self.assertIn("--background-index", args)     # Template's
        self.assertEqual(len(args), 3)

    def test_merge_c_cpp_properties(self):
        # 1. Create Template
        template_props = {
            "configurations": [
                {"name": "Mission Config", "compilerPath": "/usr/bin/clang"}
            ],
            "version": 4
        }
        with open(os.path.join(self.template_dir, "c_cpp_properties.json"), "w") as f:
            json.dump(template_props, f)
            
        # 2. Create Existing User Config
        user_props = {
            "configurations": [
                {"name": "Mac Default", "compilerPath": "/usr/bin/gcc"}
            ],
            "version": 4
        }
        with open(os.path.join(self.vscode_dir, "c_cpp_properties.json"), "w") as f:
            json.dump(user_props, f)
            
        # 3. Run Deploy with explicit template_dir
        deploy_vscode_config("/remote", template_dir=self.template_dir)
        
        # 4. Verify Merge
        with open(os.path.join(self.vscode_dir, "c_cpp_properties.json"), "r") as f:
            merged = json.load(f)
            
        configs = merged["configurations"]
        names = [c["name"] for c in configs]
        
        self.assertIn("Mission Config", names)
        self.assertIn("Mac Default", names)
        # Check Mission Config was prepended (inserted at 0)
        self.assertEqual(configs[0]["name"], "Mission Config")

if __name__ == '__main__':
    unittest.main()
