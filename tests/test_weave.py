import unittest
import json
import os
import sys
import tempfile
import yaml
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add tools/lib to path
sys.path.append(str(Path(__file__).parent.parent / "tools" / "lib"))
import weave

class TestWeave(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.tmp_dir, "weave.yaml")
        
        # Create a real config file
        config = {
            "views": {
                "ghost": ["*.txt"]
            }
        }
        with open(self.config_path, "w") as f:
            yaml.dump(config, f)
            
        # Create dummy files
        Path(os.path.join(self.tmp_dir, "file1.txt")).touch()
        Path(os.path.join(self.tmp_dir, "file2.txt")).touch()
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir)

    def test_json_output(self):
        """Verify that weave get --json outputs a valid JSON array."""
        
        # We need to trick weave into finding our config.
        # weave.py looks in ['.weaves/weave.yaml', '.mission/weave.yaml', 'weave.yaml']
        # We can chdir to tmp_dir
        
        cwd = os.getcwd()
        os.chdir(self.tmp_dir)
        try:
            with patch('sys.stdout', new=MagicMock()) as mock_stdout, \
                 patch('argparse.ArgumentParser.parse_args') as mock_args:
                 
                # Setup args
                args = MagicMock()
                args.command = 'get'
                args.view_name = 'ghost'
                args.json = True
                args.expand = False
                mock_args.return_value = args
                
                weave.main()
                
                # Check output
                # print() calls write() multiple times (content + \n)
                # We need to join all calls
                output = "".join([call.args[0] for call in mock_stdout.write.call_args_list])
                try:
                    data = json.loads(output)
                    self.assertIsInstance(data, list)
                    # We might get absolute or relative paths depending on weave implementation
                    # Weave uses glob, which returns relative to CWD if pattern is relative key
                    self.assertTrue(any("file1.txt" in f for f in data))
                except json.JSONDecodeError:
                    self.fail("Output is not valid JSON")
                    
        finally:
            os.chdir(cwd)

if __name__ == '__main__':
    unittest.main()
