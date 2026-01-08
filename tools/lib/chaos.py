import os
import sys
import yaml
import json
import stat
from pathlib import Path

# --- Configuration Constants ---
APP_COMPILER = "/usr/bin/x86_64-linux-gnu-g++-14"
APP_FLAGS = [
    "-DGTEST_DONT_DEFINE_FAIL=1", "-DGTEST_HAS_PTHREAD=1",
    "-fPIC", "-fstack-check", "-fstack-protector-strong",
    "-O0", "-march=corei7", "-std=c++23", "-Wall", "-Werror",
    "-D_GNU_SOURCE", "-DASIC_BCM"
]

DRIVER_COMPILER = "/opt/rh/devtoolset-11/root/usr/bin/gcc"
DRIVER_FLAGS = [
    "-DVPRN_DEMO_EN", "-DTPI_NEG_ENABLED", "-std=gnu99",
    "-g", "-Werror", "-Wall", "-Wextra", "-Wformat=2",
    "-fno-strict-aliasing", "-fcommon",
    "-DSW_CHIP_ALL", "-DCFG_ZSDK_LAYER_API"
]

def make_executable(path):
    st = os.stat(path)
    os.chmod(path, st.st_mode | stat.S_IEXEC)

def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)

def write_file(path, content):
    ensure_dir(os.path.dirname(path))
    with open(path, "w") as f:
        f.write(content)

def generate_source_content(name, component, style):
    """Generates C or C++ content based on style."""
    is_cpp = "cpp" in style
    
    content = [f"// Source: {name}", "#include <stdio.h>"]
    if is_cpp:
        content.append("#include <iostream>")
        content.append("#include <vector>")
    
    base = os.path.splitext(name)[0]
    # Include own header
    if f"{base}.h" in component.get("headers", []):
        content.append(f'#include "{base}.h"')
    
    content.append("\n")
    
    # Body
    if name.startswith("main"):
        content.append("int main() {")
        if is_cpp:
            content.append('    std::cout << "Chaos App Running" << std::endl;')
        else:
            content.append('    printf("Chaos App Running\\n");')
        content.append("    return 0;")
        content.append("}")
    else:
        func_name = base.replace("/", "_")
        content.append(f"void {func_name}() {{")
        if is_cpp:
             content.append(f'    std::cout << "Function {func_name} called" << std::endl;')
        else:
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

    target_root = plan.get("root", ".")
    root_dir = Path(target_root).resolve()
    
    print(f"💥 Initializing Chaos in: {root_dir}")
    if not root_dir.exists():
        root_dir.mkdir(parents=True)

    root_compile_commands = []
    
    for comp in plan.get("components", []):
        comp_path = resolve_path(root_dir, comp["path"])
        print(f"   -> Component: {comp['name']} ({comp_path})")
        style = comp.get("style", "driver_c_legacy")
        
        # Sources
        c_files = comp.get("sources", [])
        for src in c_files:
            write_file(comp_path / src, generate_source_content(src, comp, style))
        for hdr in comp.get("headers", []):
            write_file(comp_path / hdr, generate_header(hdr))

        # --- Build Flags Construction ---
        includes = []
        includes.append(f"-I{comp_path}") # Local
        for inc in comp.get("includes", []):
            abs_inc = (comp_path / inc).resolve()
            includes.append(f"-I{abs_inc}")
        for ext in comp.get("external_includes", []):
            includes.append(f"-I{ext}")

        local_compile_commands = []
        
        # --- Artifact Generation Logic ---
        for src in c_files:
            out_obj = f"{src}.o"
            abs_src = str(comp_path / src)
            abs_out = str(comp_path / out_obj)

            if style == "app_modern_cpp":
                # FLAVOR 1: 'command' string, C++, App Flags
                full_flags = APP_FLAGS + includes
                # Construct the command string
                cmd_str = f"{APP_COMPILER} {' '.join(full_flags)} -o {out_obj} -c {abs_src}"
                
                entry = {
                    "directory": str(comp_path),
                    "command": cmd_str,
                    "file": abs_src,
                    "output": abs_out
                }
            
            else: 
                # FLAVOR 2: 'arguments' list, C, Driver Flags
                # Note: Arguments list usually starts with the compiler
                args_list = [DRIVER_COMPILER] + DRIVER_FLAGS + includes + ["-c", "-o", out_obj, src]
                
                entry = {
                    "directory": str(comp_path),
                    "arguments": args_list,
                    "file": abs_src,
                    "output": abs_out
                }

            local_compile_commands.append(entry)

        # DB Placement
        db_location = comp.get("compile_db", "root")
        if db_location == "root":
            root_compile_commands.extend(local_compile_commands)
        elif db_location == "local":
            with open(comp_path / "compile_commands.json", "w") as f:
                json.dump(local_compile_commands, f, indent=2)

        # LMK Script (Simple approximation for verifying build flow)
        # We assume 'cc' is present just to test the script execution logic,
        # even if the compile_commands point to specific cross-compilers.
        lmk_content = ["#!/bin/bash", "set -e"]
        for src in c_files:
             lmk_content.append(f"echo 'Compiling {src}...'")
             # Dummy compilation to satisfy "verify" step
             lmk_content.append(f"touch {src}.o")
        
        write_file(comp_path / "lmk", "\n".join(lmk_content))
        make_executable(comp_path / "lmk")
        
        # Test Stub
        write_file(comp_path / "test/run.sh", "#!/bin/bash\necho 'Test Passed'")
        make_executable(comp_path / "test/run.sh")

    # Write Root DB
    if root_compile_commands:
        with open(root_dir / "compile_commands.json", "w") as f:
            json.dump(root_compile_commands, f, indent=2)

    # Configs
    ddd_root = root_dir / ".ddd"
    ensure_dir(ddd_root)
    if not (ddd_root / "config.json").exists():
        ddd_config = plan.get("ddd_config", {})
        with open(ddd_root / "config.json", "w") as f:
            json.dump(ddd_config, f, indent=2)
            
    # Gitignore
    with open(root_dir / ".gitignore", "a") as f:
        f.write("\n*.o\n*.out\ncompile_commands.json\n.ddd/")

    print("✅ Chaos Generated Successfully.")

if __name__ == "__main__":
    main()