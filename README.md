# Mission Core (v1.3.1)

**Mission Core** is a portable, containerized "AI Developer Environment" that docks into any C/C++/Python repository. It provides a pre-configured suite of AI agents ("Personas") equipped with deep context awareness and build-system integration.

## 🚀 New in v1.3.1: The Context Engine

This release completes the "Context Engine," a toolset designed for massive monorepos and embedded development.

### Key Capabilities

| Feature | Description |
| :--- | :--- |
| **Nuclear Strategy** | `sync_ignore` allows you to **ignore everything (`*`)** by default and whitelist only your active task. Essential for 1M+ LOC repos. |
| **Target Selector** | `weave` now resolves ambiguous compilation targets (e.g., ARM vs x86) by filtering for specific flags in `compile_commands.json`. |
| **Auto-Ghost** | The launcher dynamically detects external dependencies (e.g., `/auto/swtools`) and mounts them via NFS-safe, read-only volumes. |
| **Parasitic Mode** | The AI runs in a container but drives the **Host Build System** via the "Dead Drop Daemon" (`.ddd`), enabling verification without moving toolchains. |

---

## 🛠 Usage

### 1. Installation
Mount the mission pack as a submodule in your project root:

```bash
git submodule add [https://github.com/andrey-stepantsov/mission-core](https://github.com/andrey-stepantsov/mission-core) .mission
```

### 2. Configuration (`weave.yaml`)
Create a `weave.yaml` in your root to define your context logic.

```yaml
# 1. Sources: Where to find compile commands
compilation_dbs:
  - "compile_commands.json"

# 2. Selectors: Resolve ambiguity (e.g., Pick the ASIC V3 build)
context_selector:
  required_flags: ["-D_TARGET_ASIC_V3"]

# 3. Nuclear Strategy: Ignore everything, whitelist the HAL
ignores: ["*"]
views:
  hal: ["drivers/hal/**"]
```

### 3. Launch
Start the **Coder** persona. The system will automatically sync ignores and mount external paths.

```bash
./.mission/coder
```

---

## 🧠 Advanced Workflows

### The Context Engine
For a deep dive on handling ambiguous targets and defining Nuclear exclusion rules, see the guide:
👉 **[Context Engine Documentation](docs/context_engine.md)**

### Parasitic Mode (Build & Verify)
To let the AI run builds on your host machine (without moving your compiler into Docker):
1.  Run `dd-daemon` on your host.
2.  Configure `.ddd/config.json`.
3.  The AI will use the "Doctor" hooks to verify its own code.

👉 **[Parasitic Mode Documentation](PARASITIC_MODE.md)**

---

## 🏗 Architecture

### The "Ghost Mounting" Pattern
Standard containers blind the AI to external SDKs. Mission Core solves this by scanning the host before launch:

1.  **Scan:** `auto_ghost.py` reads all `compilation_dbs`.
2.  **Filter:** Removes redundant child paths and disables SELinux relabeling (`:z`) for NFS safety.
3.  **Inject:** Generates `-v /opt/sdk:/opt/sdk:ro` flags for Docker.

### The "C-Context" Disambiguator
`c_context.py` acts as a smart filter for compilation databases.

```bash
# Usage
c_context driver.c --db compile_commands.json
```

**Output (Ambiguity Resolution):**
```json
{
  "file": "driver.c",
  "found": true,
  "selected_command": "gcc -c driver.c -D_TARGET_ASIC_V3 ...",
  "stats": {
    "total": 5,
    "selected": 1,
    "warnings": []
  }
}
```

---

## 📚 Documentation

* **[Operator Manual](docs/operator_manual.md):** The user guide for Dash, Shell, and Weave.
* **[Context Engine](docs/context_engine.md):** Deep dive into Monorepo strategy and Auto-Ghosting.
* **[Parasitic Mode](docs/parasitic_mode.md):** Running AI on Host Build Systems.
