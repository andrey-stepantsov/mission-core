#!/usr/bin/env python3
import subprocess
import sys
import re
import os

def get_compiler_includes(compiler_cmd):
    """
    Runs the compiler with -E -Wp,-v to get default include paths.
    Returns a list of absolute paths.
    """
    cmd = f"echo | {compiler_cmd} -x c++ -E -Wp,-v -"
    try:
        # Run command, capture stderr (where verbose output goes)
        result = subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        output = result.stderr
        
        includes = []
        parsing = False
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("#include <...> search starts here:"):
                parsing = True
                continue
            if line.startswith("End of search list."):
                parsing = False
                continue
            
            if parsing:
                # Valid path?
                # Resolve paths (remove ..)
                if os.path.exists(line):
                     resolved = os.path.abspath(line)
                     if os.path.isdir(resolved):
                        includes.append(resolved)
                    
        return includes
    except Exception as e:
        sys.stderr.write(f"Error querying compiler: {e}\n")
        return []

def main():
    # Heuristic: Try to find the compiler used in the repo or fall back to system gcc
    # Ideally, we'd parse compile_commands.json, but for now, let's look for common ones
    # or use the one we found earlier: /opt/rh/devtoolset-11/root/usr/bin/g++
    
    compilers = [
        "/opt/rh/devtoolset-11/root/usr/bin/g++", # Common in this legacy env
        "g++",
        "gcc",
        "clang++"
    ]
    
    found_includes = []
    
    for comp in compilers:
        # Check if compiler exists
        try:
            subprocess.run(f"which {comp.split()[0]}", shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            found_includes = get_compiler_includes(comp)
            if found_includes:
                break
        except subprocess.CalledProcessError:
            continue
            
    # Output unique sorted paths
    for p in sorted(list(set(found_includes))):
        print(p)

if __name__ == "__main__":
    main()
