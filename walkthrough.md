# Remote Brain Provisioning Walkthrough

We have consolidated the "Remote Brain" infrastructure into the standard provisioning workflow. This allows any remote host to be provisioned with `bear`, `clang`, and the necessary compilation database tooling (`auto_ghost`, `c_context`) to support high-fidelity remote development.

## 1. Updated Provisioning Script
The `provision_remote` tool has been upgraded to:
-   **Deploy via Git**: Now pulls from `feature/remote-brain` (or current branch) instead of `rsync`.
-   **Clones DDD**: Ensures the `ddd` toolchain is present.
-   **Installs System Deps**: `bear`, `clang`, `build-essential`, `python3-pip`, `python3-venv`.
-   **Install Python Deps**: Installs requirements for `dd-daemon`.

## 2. Updated Projector & Auto-Ghost
-   **Auto-Ghost**: Now supports `--full` flag to return both dependency list and compilation context (flags, directory).
-   **Projector**:
    -   Uses `auto_ghost --full` during `pull`.
    -   **Unified Compile DB**: Generates and maintains a single `compile_commands.json` in the `hologram/` root.
    -   **Path Rewriting**: Automatically rewrites remote `-I` paths to point to locally synced `outside_wall` paths, enabling seamless LSP integration (Go to Definition works for dependencies!).

## 3. Verification
We verified the workflow in the `mission-sim` environment:
1.  **Provisioning**: Ran `provision_remote` to setup `mission-host`.
2.  **Scaffolding**: Ran `setup_realistic_host.sh` to create `Project0` and generate a `Makefile`.
3.  **Compiling**: Ran `make` on remote to generate the initial `compile_commands.json` (via `bear`).
4.  **Projector Pull**:
    -   Ran `projector pull src/main.cpp`.
    -   Verified `src/main.cpp` was synced to `hologram/`.
    -   Verified **185** implicit dependencies (including system headers like `<stdio.h>`) were synced to `outside_wall/`.
    -   Verified `hologram/compile_commands.json` was created with correct local paths.

```json
[
  {
    "directory": "/Users/.../.mission/hologram/.",
    "file": "/Users/.../.mission/hologram/src/main.cpp",
    "arguments": [
      "/usr/bin/g++",
      "-I/Users/.../.mission/outside_wall/repos/projects/project0/libs/lib0",
      "-I/Users/.../.mission/outside_wall/opt/framework0/include",
      ...
    ]
  }
]
```

## 4. Next Steps
-   Commit changes to `provision_remote`, `projector`, and `auto_ghost`.
-   Push to `feature/remote-brain`.
-   Test on a real physical host.
