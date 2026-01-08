# Chaos Generator Specification

## Synopsis

The **Chaos Generator** (`tools/bin/chaos`) is a testing utility designed to create "Perfectly Broken" C/C++ repositories. It generates complex, fractured build environments to test how context tools (`ctx-tool`, `weave`) handle edge cases like Out-of-Tree headers, conflicting compilation databases, and sibling dependencies.

## Usage

```bash
# Run from the mission pack
./.mission/tools/bin/chaos chaos_plan.yaml
```

## The Chaos Plan (`chaos_plan.yaml`)

The generator is driven by a YAML configuration file.

### Schema Reference

```yaml
root: .  # Target directory (default: current dir)

components:
  - name: my_component
    path: app/core          # Relative path in repo
    type: executable        # 'executable' or 'library'
    
    # --- Compilation Style ---
    # 'app_modern_cpp': Uses g++, C++23, root compile_commands.json logic
    # 'driver_c_legacy': Uses gcc, gnu99, local compile_commands.json logic
    style: app_modern_cpp   
    
    # --- Files ---
    sources: [main.cpp]
    headers: [logic.h]
    
    # --- Dependencies ---
    # Smart Includes: The generator will resolve these paths and 
    # automatically inject #include directives into the source files.
    includes:
      - ../../lib/math      # Sibling dependency
    external_includes:
      - /tmp/chaos_sdk      # Absolute Out-of-Tree dependency

    # --- Compilation Database Placement ---
    # 'root': Appends entry to the root compile_commands.json
    # 'local': Writes a dedicated compile_commands.json in the component dir
    # 'none': Does not track compilation (good for external SDKs)
    compile_db: root

ddd_config:
  targets:
    dev:
      build: { cmd: "./app/core/lmk", filter: "gcc_make" }
      verify: { cmd: "./app/core/test/run.sh", filter: "raw" }
```

## Key Capabilities

### 1. Dual-Style Compilation
The generator simulates a "Fractured Truth" environment common in embedded monorepos:
* **App Style:** Simulates modern host tooling (C++, high optimization).
* **Driver Style:** Simulates legacy/embedded tooling (C, cross-compilers, specific hardware flags).

### 2. Smart Includes
You do not need to manually write `#include` directives. The generator analyzes the `includes` and `external_includes` paths. If it finds a header in the target directory (e.g., `sdk_defs.h` in `/tmp/chaos_sdk`), it automatically adds `#include "sdk_defs.h"` to the generated source files.

### 3. Out-of-Tree Simulation
Support for absolute paths allows you to generate components outside the repository (e.g., `/tmp/sdk`) and reference them. This verifies that tools can correctly resolve paths that do not start with the repository root.

### 4. Hermetic & Safe
* **Hermetic:** Runs entirely within the Mission Pack's Python environment.
* **Safe:** Does **not** recursively delete the target directory. It safely overwrites files and appends to `.gitignore` idempotently.