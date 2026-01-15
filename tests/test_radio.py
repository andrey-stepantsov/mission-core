import unittest
import os
import sys
from pathlib import Path

# Add tools/lib to path
current_dir = Path(__file__).resolve().parent
mission_dir = current_dir.parent
lib_dir = mission_dir / "tools" / "lib"
sys.path.insert(0, str(lib_dir))

import radio

class TestRadioInfrastructure(unittest.TestCase):
    def test_log_path_resolution(self):
        """Ensure the radio finds the correct log file based on environment."""
        log_path = radio.DEFAULT_LOG
        print(f"\n   [Debug] Resolved Log Path: {log_path}")

        # Check 1: Must be absolute path
        self.assertTrue(os.path.isabs(log_path), "Log path must be absolute")

        # Check 2: Must point to .mission-context if it exists
        if os.path.exists("/repo/.mission-context"):
            # We are likely in the container
            self.assertIn("/repo/.mission-context", log_path)
        elif os.path.exists(".mission-context"):
            # We are on the host
            self.assertIn(".mission-context", log_path)
        else:
            # Fallback
            self.assertIn(".mission/data", log_path)

    def test_append_creates_entry(self):
        """Test writing a dummy entry (clean up after)."""
        test_msg = "UNIT_TEST_PING_" + str(os.getpid())
        radio.append_entry("TestRunner", "Null", "LOG", test_msg)
        
        with open(radio.DEFAULT_LOG, "r") as f:
            content = f.read()
            self.assertIn(test_msg, content)

if __name__ == '__main__':
    unittest.main()
