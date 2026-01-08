# Mission Core (v0.2.0)

**Mission Core** is a portable, containerized "AI Developer Environment" that docks into any C/C++/Python repository. It provides a pre-configured suite of AI agents ("Personas") equipped with deep context awareness tools.

## 🚀 New in v0.2.0: The Context Engine

This release introduces **"Context X-Ray"** and **"Ghost Mounting"**, solving the "Hermetic Blindness" problem where containerized AI agents cannot see external dependencies.

### Key Capabilities

| Feature | Description |
| :--- | :--- |
| **Context X-Ray** | `weave` now automatically scans C/C++ files for `#include` directives and resolves them to physical paths using `compile_commands.json`. |
| **Ghost Mounting** | The launcher dynamically detects out-of-tree dependencies (e.g., `/opt/sdk`, `/tmp/lib`) and mounts them into the container at runtime. |
| **Split-Brain Fix** | Automatically remaps Host paths (e.g., `/repos/project`) to Container paths (`/repo`) so the AI can use host-generated compilation databases. |
| **Multi-DB Support** | Support for monorepos with multiple scattered `compile_commands.json` files. |

---

## 🛠 Usage

### 1. Installation
Mount the mission pack as a submodule in your project root:

```bash
git submodule add https://github.com/andrey-stepantsov/mission-core .mission
```

### 2. Launch
Start the dashboard (requires `tmux`):

```bash
./.mission/dash
```

Or launch the **Coder** persona directly:

```bash
./.mission/coder
```

### 3. The "Weave" Workflow
Inside the container, use `weave` to pull context. The AI will automatically receive all necessary headers, even if they are located outside the repository.

```text
/run weave get hal
# Output: drivers/hal/hal.c drivers/hal/hal.h /tmp/chaos_sdk/sdk_defs.h
```

---

## ⚙️ Configuration (`weave.yaml`)

By default, the system looks for `compile_commands.json` in the project root and `build/`. If your project has multiple databases (e.g., one for the app, one for drivers), list them in `.weaves/weave.yaml`:

```yaml
compilation_dbs:
  - "compile_commands.json"        # Host App
  - "drivers/hal/compile_commands.json" # Embedded Driver

views:
  hal:
    - "drivers/hal/*.c"
  core:
    - "app/core/*.cpp"
```

**Auto-Ghost** will scan *all* listed databases to ensure every external dependency is mounted into the container.

---

## 🏗 Architecture

### The "Ghost Mounting" Pattern
Standard containers blind the AI to external SDKs. Mission Core solves this by scanning the host before launch:

1.  **Scan:** `auto_ghost.py` reads all `compilation_dbs`.
2.  **Detect:** Finds absolute paths like `-I/opt/sdk/include`.
3.  **Inject:** Generates `-v /opt/sdk/include:/opt/sdk/include:ro` flags for Docker.
4.  **Result:** The AI sees the file at the exact same path as the compiler.

### The "C-Context" Tool
`tools/bin/c_context` is the bridge between the build system and the AI.

```bash
# Usage
c_context target_file.c --db compile_commands.json --root .
```

**Output:**
```json
{
  "file": "/repo/src/main.c",
  "defines": ["_GNU_SOURCE", "DEBUG"],
  "includes": [
    "/repo/src/main.h",
    "/opt/sdk/include/defs.h" 
  ],
  "system_includes": [],
  "missing": []
}
```
