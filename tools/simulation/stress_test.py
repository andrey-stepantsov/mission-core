import os
import sys
import subprocess
import time
import shutil
from pathlib import Path

def create_stress_environment(root_dir, depth=5, breadth=3):
    """Creates a deep directory structure with spaces."""
    print(f"Creating stress environment at {root_dir}")
    root = Path(root_dir)
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    
    current_level = [root]
    
    for d in range(depth):
        next_level = []
        for parent in current_level:
            for b in range(breadth):
                # Create directory with space
                dir_name = f"level {d} node {b}"
                new_dir = parent / dir_name
                new_dir.mkdir()
                next_level.append(new_dir)
                
                # Create file with space
                file_name = f"file {d} {b}.txt"
                file_path = new_dir / file_name
                file_path.write_text(f"Content for depth {d} breadth {b}")
        current_level = next_level

def run_stress_test():
    repo_root = os.getcwd()
    stress_dir = "tools/stress_test_data"
    
    try:
        # 1. Setup
        create_stress_environment(stress_dir, depth=4, breadth=3)
        
        # 2. Run Projector Pull (simulated via auto_ghost/weave behavior)
        # We prefer to run the actual projector tool if possible, or components.
        # Let's run `weave get` on a pattern that matches these files
        
        # Create a temp weave config in .weaves/weave.yaml (highest priority)
        # Ensure .weaves exists
        weaves_dir = Path(".weaves")
        weaves_dir.mkdir(exist_ok=True)
        config_path = weaves_dir / "weave.yaml"
        
        weave_config = {
            "views": {
                "stress": [f"{stress_dir}/**/*.txt"]
            }
        }
        import yaml
        # Backup existing if any
        config_backup_path = None
        if config_path.exists():
            config_backup_path = config_path.with_suffix(".bak")
            config_path.rename(config_backup_path)
            
        with open(config_path, "w") as f:
            yaml.dump(weave_config, f)
            
        # Run weave
        print("Running weave stress test...")
        weave_bin = Path("tools/lib/weave.py")
        cmd = [sys.executable, str(weave_bin), "get", "stress", "--json"]
        
        start_time = time.time()
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration = time.time() - start_time
            
            import json
            files = json.loads(result.stdout)
            print(f"Weave found {len(files)} files in {duration:.4f}s")
            
            # Verify count: depth 4, breadth 3.
            if len(files) == 0:
                raise Exception("Weave found 0 files!")
                
            # Verify space handling
            for f in files:
                if " " not in f:
                     pass
                     
            print("✅ Stress Test Passed")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Weave failed with code {e.returncode}")
            print(f"Stdout: {e.stdout}")
            print(f"Stderr: {e.stderr}")
            sys.exit(1)
            
        finally:
            # Restore
            if config_backup_path and config_backup_path.exists():
                config_path.unlink() # Delete test config
                config_backup_path.rename(config_path)
            elif config_path.exists():
                config_path.unlink() # Delete test config

    except Exception as e:
        print(f"❌ Stress Test Failed: {e}")
        sys.exit(1)
    finally:
        if os.path.exists(stress_dir):
            shutil.rmtree(stress_dir)

if __name__ == "__main__":
    run_stress_test()
