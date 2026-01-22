import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Add tools/ to path
TOOLS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../tools'))
if TOOLS_ROOT not in sys.path:
    sys.path.append(TOOLS_ROOT)

from projector.internal.compile_db import rewrite_compile_flags

class TestCompileFlags(unittest.TestCase):
    def setUp(self):
        self.outside_wall = "/local/outside_wall"
        
    def test_rewrite_basic_include(self):
        # -I/path
        args = ["gcc", "-I/remote/path", "main.c"]
        with patch("os.path.exists", return_value=True):
            new_args = rewrite_compile_flags(args, self.outside_wall)
        
        expected_path = os.path.join(self.outside_wall, "remote/path")
        self.assertEqual(new_args, ["gcc", f"-I{expected_path}", "main.c"])

    def test_rewrite_separated_include(self):
        # -I /path
        args = ["gcc", "-I", "/remote/path", "main.c"]
        with patch("os.path.exists", return_value=True):
            new_args = rewrite_compile_flags(args, self.outside_wall)
        
        expected_path = os.path.join(self.outside_wall, "remote/path")
        self.assertEqual(new_args, ["gcc", "-I", expected_path, "main.c"])

    def test_rewrite_isystem(self):
        # -isystem /path
        args = ["gcc", "-isystem", "/remote/system", "main.c"]
        with patch("os.path.exists", return_value=True):
            new_args = rewrite_compile_flags(args, self.outside_wall)
            
        expected_path = os.path.join(self.outside_wall, "remote/system")
        self.assertEqual(new_args, ["gcc", "-isystem", expected_path, "main.c"])

    def test_ignore_relative_paths(self):
        # -I./local -I../parent
        args = ["gcc", "-I./local", "-I", "../parent", "main.c"]
        new_args = rewrite_compile_flags(args, self.outside_wall)
        
        # Should remain unchanged
        self.assertEqual(new_args, args)

    def test_ignore_non_path_flags(self):
        args = ["gcc", "-Wall", "-O3", "-c", "main.c"]
        new_args = rewrite_compile_flags(args, self.outside_wall)
        self.assertEqual(new_args, args)

    def test_path_with_spaces(self):
        # -I"/remote/path with spaces" 
        # Note: In argv list, quotes are gone, spaces are part of string
        args = ["gcc", "-I/remote/path with spaces", "main.c"]
        with patch("os.path.exists", return_value=True):
            new_args = rewrite_compile_flags(args, self.outside_wall)
            
        expected_path = os.path.join(self.outside_wall, "remote/path with spaces")
        self.assertEqual(new_args, ["gcc", f"-I{expected_path}", "main.c"])

    def test_rewrite_even_if_not_exists(self):
        # We should ALWAYS rewrite to outside_wall to avoid polluting context with local files
        args = ["gcc", "-I/remote/path", "main.c"]
        with patch("os.path.exists", return_value=False):
            new_args = rewrite_compile_flags(args, self.outside_wall)
        
        expected_path = os.path.join(self.outside_wall, "remote/path")
        self.assertEqual(new_args, ["gcc", f"-I{expected_path}", "main.c"])

if __name__ == '__main__':
    unittest.main()
