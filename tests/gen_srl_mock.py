import os
import json
import stat
from pathlib import Path

# Configuration
MOCK_ROOT = Path("/repos/mock-repo/srl-x/srl-repo")
SDK_ROOT = MOCK_ROOT / "asic/sdk1"
OUT_OF_TREE = Path("/repos/mock-out-of-tree")

def write_script(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    st = os.stat(path)
    os.chmod(path, st.st_mode | stat.S_IEXEC)

def create_mock():
    print(f"🔨 Generating SRL Mock at {MOCK_ROOT}...")

    # --- 1. Root Build System (Docker Wrapper) ---
    # Simulates ./rmk which calls docker
    write_script(MOCK_ROOT / "rmk", f"""#!/bin/bash
    if [ "$1" == "--test" ]; then
        echo "[RMK-DOCKER] Running Tests... PASS"
    else
        echo "[RMK-DOCKER] Building Application in Container..."
        # Simulate compilation artifact
        mkdir -p app1
        echo "binary_data" > app1/main.o
    fi
    """)
    
    # Root compile_commands.json (As produced by the builder)
    (MOCK_ROOT / "app1").mkdir(parents=True, exist_ok=True)
    (MOCK_ROOT / "app1/main.cpp").write_text("// App Main\nint main(){}")
    
    with open(MOCK_ROOT / "compile_commands.json", "w") as f:
        json.dump([{
            "directory": str(MOCK_ROOT),
            "command": "/usr/bin/clang++ -c app1/main.cpp",
            "file": str(MOCK_ROOT / "app1/main.cpp")
        }], f, indent=2)


    # --- 2. SDK Subtree System (Host Native) ---
    # Simulates ./lmk using custom GCC
    write_script(SDK_ROOT / "lmk", f"""#!/bin/bash
    echo "[LMK-HOST] Building SDK with Devtoolset-11..."
    echo "gcc -I{OUT_OF_TREE}/include -c src/driver.c"
    """)

    write_script(SDK_ROOT / "test/run.sh", f"""#!/bin/bash
    echo "[SDK-TEST] Running Python Runners... PASS"
    """)

    # Out-of-tree Headers
    (OUT_OF_TREE / "include").mkdir(parents=True, exist_ok=True)
    (OUT_OF_TREE / "include/hardware_defs.h").write_text("#define REG_X 0x01")

    # SDK Source
    (SDK_ROOT / "src").mkdir(parents=True, exist_ok=True)
    (SDK_ROOT / "src/driver.c").write_text('#include "hardware_defs.h"\nvoid drive(){}')

    # SDK compile_commands.json (Captured by bear)
    # CRITICAL: References the OUT_OF_TREE path for weave-view testing
    with open(SDK_ROOT / "compile_commands.json", "w") as f:
        json.dump([{
            "directory": str(SDK_ROOT),
            "command": f"/opt/rh/devtoolset-11/root/usr/bin/gcc -I{OUT_OF_TREE}/include -c src/driver.c",
            "file": str(SDK_ROOT / "src/driver.c")
        }], f, indent=2)

    print("✅ Mock generation complete.")

if __name__ == "__main__":
    create_mock()
