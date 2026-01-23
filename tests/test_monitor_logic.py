import unittest
import json
from unittest.mock import patch, call
from projector.internal.monitor import parse_log_line

class TestMonitorLogic(unittest.TestCase):
    def test_radio_start(self):
        line = '[RADIO] {"event": "BUILD_START", "message": "Starting build...", "timestamp": "12:00:00"}'
        with patch('builtins.print') as mock_print:
            result = parse_log_line(line)
            self.assertEqual(result, "BUILD_START")
            mock_print.assert_any_call('\n🚀 [MISSION START] 12:00:00', flush=True)

    def test_radio_success(self):
        line = '[RADIO] {"event": "BUILD_SUCCESS", "message": "Build finished.", "timestamp": "12:01:00"}'
        with patch('builtins.print') as mock_print:
            result = parse_log_line(line)
            self.assertEqual(result, "BUILD_SUCCESS")
            mock_print.assert_any_call('✅ [MISSION COMPLETE] 12:01:00', flush=True)

    def test_radio_failure(self):
        line = '[RADIO] {"event": "BUILD_FAILURE", "message": "Build failed.", "timestamp": "12:02:00"}'
        with patch('builtins.print') as mock_print:
            result = parse_log_line(line)
            self.assertEqual(result, "BUILD_FAILURE")
            mock_print.assert_any_call('❌ [MISSION FAILED] 12:02:00', flush=True)

    def test_radio_corrupt(self):
        line = '[RADIO] {corrupt_json'
        with patch('builtins.print') as mock_print:
            result = parse_log_line(line)
            self.assertIsNone(result)
            mock_print.assert_called_with('⚠️  [RADIO CORRUPT] [RADIO] {corrupt_json', flush=True)

    def test_legacy_success(self):
        line = "[*] Pipeline Complete."
        with patch('builtins.print') as mock_print:
            result = parse_log_line(line)
            self.assertEqual(result, "BUILD_SUCCESS")
            mock_print.assert_any_call('✅ [MISSION COMPLETE] (Legacy Signal)', flush=True)

    def test_legacy_failure(self):
        line = "[-] BUILD Failed (Exit: 1)"
        with patch('builtins.print') as mock_print:
            result = parse_log_line(line)
            self.assertEqual(result, "BUILD_FAILURE")
            mock_print.assert_any_call('❌ [MISSION FAILED] (Legacy Signal)', flush=True)

    def test_fallback_stats(self):
        line = "--- 📊 Build Stats ---"
        with patch('builtins.print') as mock_print:
            result = parse_log_line(line)
            # Should map to success if not explicitly failed
            self.assertEqual(result, "BUILD_SUCCESS") 
            mock_print.assert_any_call('✅ [MISSION COMPLETE] (Stats Detected)', flush=True)

if __name__ == '__main__':
    unittest.main()
