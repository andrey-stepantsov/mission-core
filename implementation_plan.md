# Implementation Plan - Consolidate Remote Brain Provisioning

We need to update `tools/bin/provision_remote` to include the "Remote Brain" capabilities verified in `setup_realistic_host.sh`.

## User Review Required
> [!IMPORTANT]
> This update assumes the remote host is a Debian/Ubuntu-like system (apt-get). If we need to support other distros, we'll need conditional logic.
> We will add `bear` and `clang` to the installed packages.

## Proposed Changes

### Mission Tools

#### [MODIFY] [provision_remote](file:///Users/stepants/dev/chaos/.mission/tools/bin/provision_remote)
-   **Context**: Working on `feature/remote-brain`.
-   **Deployment Strategy**: Replace `rsync` with `git` operations.
    -   Host should `git clone` (or `pull`) the repo from origin.
    -   Switch to the current branch (`feature/remote-brain`).
-   **Add System Dependencies**:
    -   Update the `apt-get` block (or add one) to install `bear`, `clang`, `build-essential`, `python3-pip`, `python3-venv`.
-   **Install Python Dependencies**:
    -   After syncing files, run `pip3 install -r ~/.mission/tools/ddd/requirements.txt` on the remote host.
-   **Auto-Ghost Configuration**:
    -   Ensure `auto_ghost` and `c_context` are executable (already handled by `rsync -a` usually, but we can explicit `chmod`).
    -   (Optional) The prompt mentioned "generating the bear-wrapped Makefile shim". This was done in `setup_realistic_host.sh` for a specific project. Since `provision_remote` is generic, we cannot modify a specific Makefile. However, we can ensure the *environment* is ready for it.
-   **Enhance Compiler Flag Handling**:
    -   Update `c_context.py` to extract all compiler flags (defines, includes, standard versions) and return them in the JSON output.
    -   Update `auto_ghost` to pass these flags through.
    -   Update `projector pull` to:
        -   Capture these flags.
        -   Merge them with user-specified local overrides (defined in `.hologram_config` or CLI).
        -   Handle `-I` and `-L` flags:
            -   Remote absolute paths are meaningless locally.
            -   Map them to `outside_wall` if they are dependencies we synced.
            -   Or expose them as-is if they are system paths (user might need to override them).
        -   **Unified Local Compile DB**:
            -   Instead of just `compile_flags.txt`, we will maintain a single `compile_commands.json` at the root of `hologram/`.
            -   When pulling a file, we look up its compile flags (via `c_context/auto_ghost`).
            -   We construct a JSON entry `{ "directory": "...", "command": "...", "file": "..." }`.
            -   **Rewriting**: We must rewrite the `directory` to the local hologram root (or subfolder) and adjust `-I` paths to point to `outside_wall` or relative hologram paths.
            -   We upsert this entry into the local `compile_commands.json`.
-   **Multi-File / Multi-DB Strategy**:
    -   `projector` already handles this by invoking `auto_ghost` in the target file's directory.
    -   Since we are building a *unified* local DB, it doesn't matter if the remote files came from different remote DBs. We normalize them into one local source of truth for the LSP.
    -   *Decision*: `projector pull` updates the specific entry for the pulled file in the shared `compile_commands.json`.
-   **DD-Daemon Setup**:
    -   `dd-daemon` is launched by `launch_tower`. We just need to ensure its dependencies (Python libs) are installed.

## Verification Plan

### Automated Tests
-   We will use the simulation environment (`tools/bin/enter_matrix`) to verification.
-   We can modify `test_projector_live.sh` or create a small script to:
    1.  Reset the simulator (`docker restart mission-host`).
    2.  Run `provision_remote` against it.
    3.  Check if `bear` is installed.
    4.  Check if `auto_ghost` runs on the remote.

### Manual Verification
-   Run `tools/bin/provision_remote -h mission-sim -u oracle`.
-   SSH into `mission-sim`.
-   Run `which bear`.
-   Run `auto_ghost --help`.
