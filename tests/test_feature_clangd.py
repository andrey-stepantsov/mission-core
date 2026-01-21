
import os
import json
import unittest
import io
from unittest.mock import patch, MagicMock
import sys
import tempfile
import shutil

# Add tools/bin to path to import projector
# usage: python3 tests/test_feature_clangd.py
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_BIN = os.path.join(PROJECT_ROOT, "tools", "bin")
sys.path.insert(0, TOOLS_BIN)

# Import projector module
# Since it has no .py extension, we use SourceFileLoader
from importlib.machinery import SourceFileLoader
projector = SourceFileLoader("projector", os.path.join(TOOLS_BIN, "projector")).load_module()
sys.modules["projector"] = projector

class TestProjectorClangd(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.hologram_dir = os.path.join(self.test_dir, "hologram")
        os.makedirs(self.hologram_dir)
        
        # Mock finding project root to return test_dir
        self.patcher_root = patch('projector.find_project_root', return_value=self.test_dir)
        self.mock_find_root = self.patcher_root.start()
        
        # Mock constants in projector if needed
        # We can't easily mock module-level constants if they are used at import time or global scope,
        # but projector.HOLOGRAM_DIR is likely used inside functions.
        projector.HOLOGRAM_DIR = "hologram"

    def tearDown(self):
        self.patcher_root.stop()
        shutil.rmtree(self.test_dir)

    def create_compile_db(self, entries):
        db_path = os.path.join(self.hologram_dir, "compile_commands.json")
        with open(db_path, "w") as f:
            json.dump(entries, f)
        return db_path

    def test_focus_generates_clangd(self):
        """Test 'focus' command generates .clangd with correct flags."""
        source_file = os.path.join(self.hologram_dir, "src", "main.c")
        
        db_entries = [
            {
                "directory": self.hologram_dir,
                "file": source_file,
                "arguments": [
                    "/usr/bin/gcc",
                    "-DDEBUG",
                    "-I/usr/include",
                    "-isystem", "/usr/local/include",
                    "-std=c99",
                    "-o", "main.o",
                    "-c", source_file
                ]
            }
        ]
        self.create_compile_db(db_entries)
        
        # Run focus
        args = MagicMock()
        args.file = source_file
        
        # Capture stdout to avoid clutter
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            projector.do_focus(args)
            
        # Verify .clangd exists
        clangd_path = os.path.join(self.hologram_dir, ".clangd")
        self.assertTrue(os.path.exists(clangd_path))
        
        with open(clangd_path, "r") as f:
            content = f.read()
            
        # Verify content
        expected_flags = [
            "-DDEBUG",
            "-I/usr/include",
            "-isystem", "/usr/local/include",
            "-std=c99"
        ]
        
        self.assertIn("CompileFlags:", content)
        self.assertIn("Add:", content)
        for flag in expected_flags:
            self.assertIn(flag, content)
            
        # Verify excluded flags
        self.assertNotIn("-o", content)
        self.assertNotIn("main.o", content)
        self.assertNotIn("-c", content)

    def test_focus_fails_missing_db(self):
        """Test 'focus' fails gracefully if compile_commands.json is missing."""
        args = MagicMock()
        args.file = "foo.c"
        
        with self.assertRaises(SystemExit) as cm:
             with patch('sys.stdout', new=io.StringIO()) as fake_out:
                projector.do_focus(args)
        
        self.assertEqual(cm.exception.code, 1)

    def test_focus_fails_missing_entry(self):
        """Test 'focus' fails if file not in DB."""
        self.create_compile_db([])
        
        args = MagicMock()
        args.file = os.path.join(self.hologram_dir, "unknown.c")
        
        with self.assertRaises(SystemExit) as cm:
             with patch('sys.stdout', new=io.StringIO()) as fake_out:
                projector.do_focus(args)
                
        self.assertEqual(cm.exception.code, 1)

if __name__ == '__main__':
    unittest.main()
