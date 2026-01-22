import unittest
import os
import sys
import subprocess
import shutil

class TestRemoteConstraints(unittest.TestCase):
    def setUp(self):
        # Check if docker is available
        if shutil.which("docker") is None:
            self.skipTest("Docker not found. Skipping constraint verification.")
            
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.tools_bin = os.path.join(self.project_root, "tools/bin")
        self.tools_lib = os.path.join(self.project_root, "tools/lib")

    def run_in_docker(self, script_path, args=None, expected_returncode=0):
        """Runs the script in a python:3.8-slim-buster container."""
        # Mount the project root to /mission
        # script_path should be absolute path
        rel_script = os.path.relpath(script_path, self.project_root)
        
        container_script = f"/mission/{rel_script}"
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{self.project_root}:/mission",
            "-w", "/mission",
            "python:3.8-slim-buster",
            "python3", container_script
        ]
        
        if args:
            cmd.extend(args)
            
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != expected_returncode:
            print(f"\n--- Docker Execution Failed ---")
            print(f"Command: {cmd}")
            print(f"Stdout: {result.stdout}")
            print(f"Stderr: {result.stderr}")
            
        self.assertEqual(result.returncode, expected_returncode, 
                         f"Script {rel_script} failed in Docker (RC={result.returncode})")
        return result

    def test_auto_ghost_compatibility(self):
        """Verifies auto_ghost runs on Python 3.8 without external deps."""
        script = os.path.join(self.tools_bin, "auto_ghost")
        # Run with --help, expect passing
        self.run_in_docker(script, ["--help"], expected_returncode=0)

    def test_sys_headers_compatibility(self):
        """Verifies sys_headers.py runs on Python 3.8 without external deps."""
        script = os.path.join(self.tools_lib, "sys_headers.py")
        # sys_headers.py executes immediately.
        # It might fail if no compiler is found, but it shouldn't fail with ImportError.
        # If it runs, it prints includes.
        # If we run it in python:3.8-slim, gcc/clang likely missing.
        # We expect it to run and NOT crash with ImportError.
        # It might exit with non-zero if compiler not found?
        # Let's see code.
        
        # It imports os, sys, shutil, subprocess, json.
        # It calls main().
        # It checks for 'cc', 'gcc', 'clang'.
        # If not found, it might print nothing or fail?
        # In slim image, cc might be missing.
        # As long as it doesn't Import Error.
        
        # We can just check that stderr doesn't contain "ModuleNotFoundError".
        
        res = self.run_in_docker(script, expected_returncode=0) # Should exit cleaner with 0 even if no compiler
        
        # Check stderr for import errors
        self.assertNotIn("ModuleNotFoundError", res.stderr)
        self.assertNotIn("ImportError", res.stderr)

if __name__ == "__main__":
    unittest.main()
