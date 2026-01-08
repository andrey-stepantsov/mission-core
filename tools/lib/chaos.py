import os
import sys
import yaml
import json
import stat
from pathlib import Path

def make_executable(path):
    st = os.stat(path)
    os.chmod(path, st.st_mode | stat.S_IEXEC)

def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)

def write_file(path, content):
    ensure_dir(os.path.dirname(path))
    with open(path, "w") as f:
        f.write(content)

def generate_c_source(name, component):
    """Generates a valid C file with necessary includes."""
    content = [f"// Source: {name}", "#include <stdio.h>"]
    
    # Include own header if it exists
    base = os.path.splitext(name)[0]
    if f"{base}.h" in component.get("headers", []):
        content.append(f'#include "{base}.h"')
    
    # Add body
    content.append("\n")
    if name == "main.c":
        content.append("int main() {")
        content.append('    printf("Chaos App Running\\n");')
        content.append("    return 0;")
        content.append("}")
    else:
        func_name = base.replace("/", "_")
        content.append(f"void {func_name}() {{")
        content.append(f'    printf("Function {func_name} called\\n");')
        content.append("}")
    
    return "\n".join(content)

def generate_header(name):
    guard = name.upper().replace(".", "_").replace("/", "_")
    return f"""#ifndef {guard}
#define {guard}

void {os.path.splitext(name)[0]}();

#endif // {guard}
"""

def resolve_path(root_dir, path_str):
    """Handles absolute paths vs relative paths."""
    if os.path.isabs(path_str):
        return Path(path_str)
    return Path(root_dir) / path_str

def main():
    if len(sys.argv) < 2:
        print("Usage: chaos <plan.yaml>")
        sys.exit(1)

    plan_file = sys.argv[1]
    with open(plan_file, 'r') as f:
        plan = yaml.safe_load(f)

    # Use current directory by default if root is not specified
    target_root = plan.get("root", ".")
    root_dir = Path(target_root).resolve()
    
    print(f"💥 Initializing Chaos in: {root_dir}")
    # SAFETY: Removed rmtree(root_dir) to prevent deleting .git/.mission
    if not root_dir.exists():
        root_dir.mkdir(parents=True)

    compile_commands = []
    
    # 1. Process Components
    for comp in plan.get("components", []):
        comp_path = resolve_path(root_dir, comp["path"])
        print(f"   -> Component: {comp['name']} ({comp_path})")
        
        # Sources
        c_files = comp.get("sources", [])
        for src in c_files:
            write_file(comp_path / src, generate_c_source(src, comp))
            
        # Headers
        for hdr in comp.get("headers", []):
            write_file(comp_path / hdr, generate_header(hdr))

        # Build Script (lmk)
        include_flags = []
        
        # Local Includes
        include_flags.append(f"-I{comp_path}")
        
        # Relative Includes
        for inc in comp.get("includes", []):
            abs_inc = (comp_path / inc).resolve()
            include_flags.append(f"-I{abs_inc}")

        # External Includes
        for ext in comp.get("external_includes", []):
            include_flags.append(f"-I{ext}")

        # Generate compile_commands entry
        for src in c_files:
            # Simple assumption: cc is available
            cmd = f"cc {' '.join(include_flags)} -c {src} -o {src}.o"
            compile_commands.append({
                "directory": str(comp_path),
                "command": cmd,
                "file": str(comp_path / src)
            })

        # Generate LMK script
        lmk_content = ["#!/bin/bash", "set -e", "echo '[Chaos Build] Building...'"]
        
        # Compile object files
        for src in c_files:
            lmk_content.append(f"cc {' '.join(include_flags)} -c {src} -o {src}.o")
        
        # Link if executable
        if comp.get("type") == "executable":
            output_bin = comp.get("output", "a.out")
            objs = [f"{s}.o" for s in c_files]
            lmk_content.append(f"cc {' '.join(objs)} -o {output_bin}")
            lmk_content.append(f"echo '[Chaos Build] Created {output_bin}'")

        write_file(comp_path / "lmk", "\n".join(lmk_content))
        make_executable(comp_path / "lmk")

        # Generate Test Stub
        write_file(comp_path / "test/run.sh", "#!/bin/bash\necho 'Test Passed'")
        make_executable(comp_path / "test/run.sh")

    # 2. Generate Global compile_commands.json
    with open(root_dir / "compile_commands.json", "w") as f:
        json.dump(compile_commands, f, indent=2)

    # 3. Generate .ddd/config.json
    ddd_root = root_dir / ".ddd"
    ensure_dir(ddd_root)
    
    ddd_config = plan.get("ddd_config", {})
    if not ddd_config:
        # Default config if none provided
        ddd_config = {
            "targets": {
                "all": {
                    "build": {"cmd": "find . -name lmk -exec {} \\;", "filter": "gcc_make"},
                    "verify": {"cmd": "echo 'Verify'", "filter": "raw"}
                }
            }
        }
    
    with open(ddd_root / "config.json", "w") as f:
        json.dump(ddd_config, f, indent=2)

    # 4. Create .gitignore (Append if exists)
    gitignore_path = root_dir / ".gitignore"
    ignores = ["*.o", "*.out", "compile_commands.json", ".ddd/"]
    
    current_content = ""
    if gitignore_path.exists():
        with open(gitignore_path, "r") as f:
            current_content = f.read()
    
    with open(gitignore_path, "a") as f:
        for ig in ignores:
            if ig not in current_content:
                f.write(f"\n{ig}")

    print("✅ Chaos Generated Successfully.")

if __name__ == "__main__":
    main()