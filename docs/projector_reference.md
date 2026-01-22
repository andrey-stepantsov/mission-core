# Projector CLI Reference

The `projector` agent enables "Remote Brain" workflows, allowing you to edit code locally ("Hologram") while building and running it on a remote host ("Oracle").

## atomic Workflow

The recommended workflow for autonomous agents and users is the **Atomic Cycle**.

### 1. Pull (Edit)
Retrieve a file from the remote host to the local hologram.
```bash
projector pull <remote_absolute_path>
```
*   **Overlay**: Hides the file from `outside_wall` (if present) to ensure the Hologram version takes precedence.
*   **Auto-Ghost**: Automatically detects and pulls implicit dependencies (headers, etc.) to `outside_wall/`.
*   **LSP Configuration**: Automatically updates `compile_commands.json` with correct include paths (`-I` and `-isystem`) pointing to the local `outside_wall`, enabling full `clangd` support.
*   **System Headers**: Does not pull standard headers by default (e.g. `/usr/include`). Use `projector repair-headers` to sync them.
*   **Context Selection**: If multiple build contexts exist for the file (e.g. different macros), use `--flags` to specify which one to use.
    ```bash
    projector pull src/main.c --flags "-DDEBUG -O0"
    ```
    If ambiguous and no flags are provided, `projector` will warn and list options.


### 2. Build & Verify (Atomic)
Sync the file, trigger the remote build, and **wait** for the result.
```bash
projector build --sync <local_file_path> --wait
```
*   **Syncs**: Pushes the file to the remote host.
*   **Triggers**: Notifies the remote `dd-daemon` to run the build.
*   **Waits**: Streams the remote log (`.ddd/run/build.log`) until completion.
*   **Result**: Returns Exit Code `0` (Success) or `1` (Failure).

### 3. Log Retrieval (Manual)
If you need to check the logs without triggering a build:
```bash
projector log [-n lines]
```

### 4. Remote Ripgrep (Search)
Search the remote codebase using `ripgrep` (must be installed on remote). The results are mapped to local hologram paths for VSCode clickability.
```bash
projector grep "pattern" [optional/path]
```
*   **Context**: Maps the remote path (e.g., `/repos/project/...`) to the local `hologram/...` path.
*   **Clean History**: All remote commands, including grep, run with `unset HISTFILE` to prevent polluting the remote shell history.

### 5. Run (Execute)
Execute any command on the remote host within the project environment (useful for scripts, tests, etc).
```bash
projector run "make test"
```
*   **Environment**: Automatically loads the project context (cd to root).
*   **Interactive**: Supports interactive tools via pseudo-terminal allocation (-t).


### 5. Focus (Clangd Context)
Generate a dynamic `.clangd` configuration for the workspace based on a specific source file's compilation flags.
```bash
projector focus <source_file>
```
*   **Purpose**: Clangd cannot infer context for header files (`.h`) in isolation. By "focusing" on a source file (`.c`) that includes the header, you apply its flags (macros, includes) to the entire workspace.
*   **Result**: Generates a `.clangd` file in the hologram root.
*   **Best Practice**: Run this when switching between files with different build configurations (e.g. different chips).

### 6. Pull (Edit) Refinement
When multiple compilation contexts exist for a file:
*   **Interactive Selection**: `projector` prompts you to choose the correct build target.
*   **Smart Flag Display**: The prompt automatically hides common flags (intersection) and shows only the **differentiating flags** for each candidate, correcting visual clutter.

### AI Introspection
To help AI agents understand the active compilation flags for a file (macros, includes, language standard), use the context command:
```bash
projector context <local_file_path>
```
Output is valid YAML, making it easy to parse. This is critical for resolving conditional compilation paths (`#ifdef`).


### 5. Retract (Cleanup)
Remove the file from the local hologram and restore the base layer.
```bash
projector retract <local_file_path>
# OR
projector retract --all
```
*   **Restore**: If the file exists on the remote host (base layer), it is restored to `outside_wall` as Read-Only.
*   **--all**: recursively removes ALL files from the hologram and checks for restoration. Use this to reset your workspace.

### 6. Repair Headers (One-time)
Sync system headers (e.g. from `/usr/include`, `/opt/toolchain/...`) from the remote host to the local `outside_wall`. This is critical for `clangd` to resolve standard library and toolchain headers.
```bash
projector repair-headers
```
*   **Syncs**: Queries the remote compiler for default include paths and `rsync`s them locally.
*   **Updates**: Automatically refreshes `compile_commands.json` to include these system paths.

## Live Mode (Human)
For interactive human use, you can enable the continuous "Synapse".
```bash
projector live [--auto-build]
```
*   **Reflex**: Watches for local file changes and syncs them instantly.
*   **Radio**: Streams remote build logs to your terminal.

## Configuration
Stored in `.hologram_config` at the project root.
```json
{
    "host_target": "user@host",
    "remote_root": "/path/to/remote/repo"
}
```
Initialized via:
```bash
projector init user@host --remote-root /path/to/repo
# OR (Shorthand)
projector init user@host:/path/to/repo
```
*   **Recommendation**: Always specify the remote root path to avoid defaulting to the home directory.


## IDE Setup (VSCode)
For the best experience, use **clangd**.
1. Install Extension: `llvm-vs-code-extensions.vscode-clangd`.
2. Disable Microsoft C/C++ IntelliSense (to avoid conflicts).
3. Configure `clangd` arguments in `.vscode/settings.json`:
```json
"clangd.arguments": [
    "--compile-commands-dir=${workspaceFolder}/hologram",
    "--background-index",
    "--header-insertion=never"
]
```
## Cookbook: Common Scenarios

### 0. VSCode Integration (Tasks)
If you are using VSCode with the deployed configuration, you can use **Tasks** instead of the CLI for common operations. Press `Cmd+Shift+P` -> `Run Task` to see:
*   **Projector Pull**: Prompts for a remote path and pulls it.
*   **Projector Push (Sync)**: Syncs the currently open file.
*   **Projector Retract**: Retracts the currently open file.
*   **Projector Log**: Shows the remote build log.


### 1. Creating a New Module
You can create new files and directories directly in the local `hologram/` folder. The agent will handle the remote creation.

```bash
# 1. Create local struture
mkdir -p hologram/src/new_module
echo 'void new_feature() {}' > hologram/src/new_module/feature.c

# 2. Sync and Build
# The agent will execute 'mkdir -p' on the remote host automatically.
projector build --sync hologram/src/new_module/feature.c --wait
```

### 2. Updating Build Configuration
You can edit `CMakeLists.txt` or `Makefile` just like source code.

```bash
# 1. Pull the build file
projector pull src/CMakeLists.txt

# 2. Edit locally
# (e.g., adding the new_module we just created)

# 3. Sync and Verify
projector build --sync hologram/src/CMakeLists.txt --wait
```

### 3. Editing Documentation
Antigravity can pull and update markdown documentation to keep the remote repo in sync.

```bash
# 1. Pull existing docs
projector pull docs/architecture.md

# 2. Create new docs locally
echo "# New Design" > hologram/docs/new_design.md

# 3. Sync
projector push hologram/docs/new_design.md
```
*   **Note**: `projector push` is the underlying mechanics of `build --sync`. Use it if you just want to update a file (like a doc) without triggering a compiler build.
