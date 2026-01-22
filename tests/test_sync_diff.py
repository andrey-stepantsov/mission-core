import unittest
import os
import sys

# Add tools/ to path
TOOLS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../tools'))
if TOOLS_ROOT not in sys.path:
    sys.path.append(TOOLS_ROOT)

from projector.commands.sync import compute_candidate_diff

class TestSyncDiff(unittest.TestCase):
    def test_identical_candidates(self):
        c1 = {"command": "gcc -c main.c -I."}
        c2 = {"command": "gcc -c main.c -I."}
        diffs = compute_candidate_diff([c1, c2])
        
        self.assertEqual(len(diffs), 2)
        self.assertEqual(diffs[0], "(Identical to others)")
        self.assertEqual(diffs[1], "(Identical to others)")

    def test_distinct_flags(self):
        c1 = {"command": "gcc -c main.c -DDEBUG"}
        c2 = {"command": "gcc -c main.c -DRELEASE"}
        diffs = compute_candidate_diff([c1, c2])
        
        # Intersection is "gcc -c main.c"
        # c1 diff: -DDEBUG
        # c2 diff: -DRELEASE
        
        self.assertEqual(diffs[0], "-DDEBUG")
        self.assertEqual(diffs[1], "-DRELEASE")

    def test_superset_flags(self):
        c1 = {"command": "gcc -c main.c"}
        c2 = {"command": "gcc -c main.c -lextra"}
        diffs = compute_candidate_diff([c1, c2])
        
        self.assertEqual(diffs[0], "(Identical to others)")
        self.assertEqual(diffs[1], "-lextra")

    def test_quoted_flags(self):
        # shlex split should handle quotes
        c1 = {"command": "gcc -c main.c -DMSG=\"Hello World\""}
        c2 = {"command": "gcc -c main.c -DMSG=\"Hello Universe\""}
        diffs = compute_candidate_diff([c1, c2])
        
        # Diff matches exact strings
        # c1 has -DMSG="Hello World" (or shlex parsed version)
        # c2 has -DMSG="Hello Universe"
        
        self.assertIn("-DMSG=Hello World", diffs[0])
        self.assertIn("-DMSG=Hello Universe", diffs[1])

if __name__ == '__main__':
    unittest.main()
