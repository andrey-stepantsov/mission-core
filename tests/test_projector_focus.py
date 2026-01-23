import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import os
import json

from projector.commands.build import do_focus

class TestProjectorFocus(unittest.TestCase):
    def setUp(self):
        # Mock Args
        self.args = MagicMock()
        self.args.file = "/abs/path/to/src/main.c"

        # Mock File System Scaffolding
        self.project_root = "/fake/project"
        self.hologram_dir = os.path.join(self.project_root, ".hologram")
        self.db_path = os.path.join(self.hologram_dir, "compile_commands.json")
        self.clangd_path = os.path.join(self.hologram_dir, ".clangd")

    @patch('projector.commands.build.find_project_root')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    def test_focus_success(self, mock_json_load, mock_file, mock_exists, mock_find_root):
        # 1. Setup Environment
        mock_find_root.return_value = self.project_root
        
        # mock exists calls: 
        # 1. db_path check -> True
        def exists_side_effect(path):
            if str(path).endswith("compile_commands.json"): return True
            return False
        mock_exists.side_effect = exists_side_effect

        # 2. Setup Compile DB Content
        mock_db = [
            {
                "directory": self.hologram_dir,
                "file": "/abs/path/to/src/main.c",
                "command": "gcc -DDEBUG -I/include -c main.c -o main.o"
            }
        ]
        mock_json_load.return_value = mock_db

        # 3. Run Command
        with patch('sys.stdout', new=MagicMock()) as fake_out:
            do_focus(self.args)

        # 4. Verify .clangd content
        # We expect it to write to self.clangd_path
        handle = mock_file()
        
        # Check that we opened the clangd file for writing
        # Note: multiple opens might happen (read db, write clangd)
        # We need to find the write call to clangd_path
        write_call_found = False
        written_content = ""
        
        for call in mock_file.mock_calls:
            if call[0] == '().write':
                written_content += call[1][0]
                
        # Simple verification of content
        self.assertIn("CompileFlags:", written_content)
        self.assertIn('  Add:', written_content)
        self.assertIn('    - "-DDEBUG"', written_content)
        self.assertIn('    - "-I/include"', written_content)
        
        # Verify it filtered out the input/output args (-o main.o, -c)
        self.assertNotIn('    - "-c"', written_content)
        self.assertNotIn('    - "-o"', written_content)
        self.assertNotIn('    - "main.o"', written_content)

    @patch('projector.commands.build.find_project_root')
    def test_focus_no_hologram(self, mock_find_root):
        mock_find_root.return_value = None
        
        with patch('sys.stdout', new=MagicMock()) as fake_out:
            with self.assertRaises(SystemExit) as cm:
                do_focus(self.args)
            self.assertEqual(cm.exception.code, 1)

    @patch('projector.commands.build.find_project_root')
    @patch('os.path.exists')
    def test_focus_no_db(self, mock_exists, mock_find_root):
        mock_find_root.return_value = self.project_root
        mock_exists.return_value = False # DB not found
        
        with patch('sys.stdout', new=MagicMock()) as fake_out:
            with self.assertRaises(SystemExit) as cm:
                do_focus(self.args)
            self.assertEqual(cm.exception.code, 1)

if __name__ == '__main__':
    unittest.main()
