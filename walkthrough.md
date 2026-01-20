# Remote Brain Provisioning Walkthrough

We have consolidated the "Remote Brain" infrastructure into the standard provisioning workflow, adapted it for real-world non-root environments, and unified the Python bootstrap strategy.

## 1. Features
### A. Provisioning (`provision_remote`)
-   **Git-Based Deployment**: Deploys `.mission` and `ddd` tools via git (feature branch support).
-   **Non-Root Ready**: 
    -   Removed `sudo apt-get`.
    -   Now **checks** for existing `bear`, `clang`, `python3` installations.
    -   Installs Python deps via `bootstrap.sh` (user-space venv).
    -   Defaults to SSH port **22**.
-   **Generic Args**: Supports `--host`, `--port`, `--user`, `--alias`.

### B. Unified Bootstrap (`bootstrap.sh`)
-   **Single Point of Truth**: `provision_remote` and `launch_tower` now delegate to `tools/lib/bootstrap.sh`.
-   **Arch-Specific Venv**: Respects architecture-specific venv naming (e.g., `.venv-Linux-x86_64-host`) handled within `bootstrap.sh`.
-   **Isolation**: Ensures `dd-daemon` runs in the same isolated venv as Mission Tools.

### C. Compile DB & Auto-Ghost
-   **Full Context**: `auto_ghost --full` returns dependency list + compilation flags/directory.
-   **Local Hologram**: `projector` maintains a single unified `compile_commands.json` locally, rewriting remote paths (`-I/remote/...` -> `-I/local/outside_wall/...`) for seamless LSP support.

## 2. Verification
Verified in `mission-sim` (with manual prerequisite installation to mimic real host):
1.  **Provisioning**: `provision_remote --host localhost --port 2222 ...` succeeded.
2.  **Bootstrap**: Confirmed `dd-daemon` launched via venv python.
3.  **Projector Pull**: 
    -   Pulled `src/main.cpp`.
    -   Received 185 system headers in `outside_wall`.
    -   Generated valid `compile_commands.json`.

## 3. How to Use on Real Host
```bash
#  Prereqs: SSH access, bear, clang, python3 installed on host.
.mission/tools/bin/provision_remote \
  --host 192.168.1.50 \
  --port 22 \
  --user stepants \
  --alias my-remote-dev
```
