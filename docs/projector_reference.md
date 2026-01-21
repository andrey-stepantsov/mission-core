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

### 5. Retract (Cleanup)
Remove the file from the local hologram and restore the base layer.
```bash
projector retract <local_file_path>
# OR
projector retract --all
```
*   **Restore**: If the file exists on the remote host (base layer), it is restored to `outside_wall` as Read-Only.
*   **--all**: recursively removes ALL files from the hologram and checks for restoration. Use this to reset your workspace.

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
```
```bash
projector init user@host --remote-root /path/to/repo
```

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
