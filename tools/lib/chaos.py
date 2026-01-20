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
    "-DDEMO_EN", "-DCACHE_ENABLED", "-std=gnu99",
    "-g", "-Werror", "-Wall", "-Wextra", "-Wformat=2",
    "-fno-strict-aliasing", "-fcommon"
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

def resolve_path(root_dir, path_str):
    if os.path.isabs(path_str):
        return Path(path_str)
    return Path(root_dir) / path_str

def generate_source_content(name, component, style, header_map, root_dir):
    """Generates C/C++ content with smart includes."""
    is_cpp = "cpp" in style
    
    content = [f"// Source: {name}", "#include <stdio.h>"]
    if is_cpp:
        content.append("#include <iostream>")
        content.append("#include <vector>")
    
    base = os.path.splitext(name)[0]
    
    # 1. Include own header
    if f"{base}.h" in component.get("headers", []):
        content.append(f'#include "{base}.h"')

    # 2. Include headers from dependencies (Logic Injection)
    comp_path = resolve_path(root_dir, component["path"])
    all_include_paths = []
    
    for inc in component.get("includes", []):
        all_include_paths.append((comp_path / inc).resolve())
        
    for ext in component.get("external_includes", []):
        # Resolve external includes to absolute paths for consistency
        abs_ext = resolve_path(root_dir, ext).resolve()
        all_include_paths.append(abs_ext)

    # Check map
    for inc_path in all_include_paths:
        path_str = str(inc_path)
        if path_str in header_map:
            for h in header_map[path_str]:
                content.append(f'#include "{h}"')

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

    # --- Pass 0: Build Header Map ---
    # Used to verify if an include path actually contains headers we know about
    header_map = {}
    for comp in plan.get("components", []):
        comp_path = resolve_path(root_dir, comp["path"]).resolve()
        headers = comp.get("headers", [])
        if headers:
            header_map[str(comp_path)] = headers

    root_compile_commands = []
    
    # --- Pass 1: Generate Components ---
    for comp in plan.get("components", []):
        comp_path = resolve_path(root_dir, comp["path"])
        print(f"   -> Component: {comp['name']} ({comp_path})")
        style = comp.get("style", "driver_c_legacy")
        
        # Sources
        c_files = comp.get("sources", [])
        for src in c_files:
            content = generate_source_content(src, comp, style, header_map, root_dir)
            write_file(comp_path / src, content)
            
        for hdr in comp.get("headers", []):
            write_file(comp_path / hdr, generate_header(hdr))

        # --- Build Flags Construction ---
        includes = []
        includes.append(f"-I{comp_path}") # Local
        for inc in comp.get("includes", []):
            abs_inc = (comp_path / inc).resolve()
            includes.append(f"-I{abs_inc}")
        
        # FIX: Force absolute paths for external includes
        for ext in comp.get("external_includes", []):
            abs_ext = resolve_path(root_dir, ext).resolve()
            includes.append(f"-I{abs_ext}")

        local_compile_commands = []
        
        # --- Artifact Generation Logic ---
        for src in c_files:
            out_obj = f"{src}.o"
            abs_src = str(comp_path / src)
            abs_out = str(comp_path / out_obj)

            if style == "app_modern_cpp":
                full_flags = APP_FLAGS + includes
                cmd_str = f"{APP_COMPILER} {' '.join(full_flags)} -o {out_obj} -c {abs_src}"
                entry = {
                    "directory": str(comp_path),
                    "command": cmd_str,
                    "file": abs_src,
                    "output": abs_out
                }
            else: 
                args_list = [DRIVER_COMPILER] + DRIVER_FLAGS + includes + ["-c", "-o", out_obj, src]
                entry = {
                    "directory": str(comp_path),
                    "arguments": args_list,
                    "file": abs_src,
                    "output": abs_out
                }
            local_compile_commands.append(entry)

        # DB Placement
        # DB Placement
        db_location = comp.get("compile_db", "root")
        if db_location == "root":
            root_compile_commands.extend(local_compile_commands)
        elif db_location == "local":
            with open(comp_path / "compile_commands.json", "w") as f:
                json.dump(local_compile_commands, f, indent=2)
        elif db_location == "both":
            root_compile_commands.extend(local_compile_commands)
            with open(comp_path / "compile_commands.json", "w") as f:
                json.dump(local_compile_commands, f, indent=2)

        # LMK Script
        lmk_content = ["#!/bin/bash", "set -e"]
        for src in c_files:
             lmk_content.append(f"echo 'Compiling {src}...'")
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
            
    # FIXED: Idempotent Gitignore Update
    gitignore_path = root_dir / ".gitignore"
    ignores = ["*.o", "*.out", "compile_commands.json", ".ddd/"]
    
    existing_content = ""
    if gitignore_path.exists():
        with open(gitignore_path, "r") as f:
            existing_content = f.read()

    missing_ignores = []
    for ig in ignores:
        if ig not in existing_content:
            missing_ignores.append(ig)

    if missing_ignores:
        with open(gitignore_path, "a") as f:
            if existing_content and not existing_content.endswith("\n"):
                f.write("\n")
            f.write("\n".join(missing_ignores) + "\n")

    print("✅ Chaos Generated Successfully.")

if __name__ == "__main__":
    main()
