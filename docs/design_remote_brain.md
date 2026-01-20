# design: Remote Brain Architecture ("The Hologram Strategy")

## 1. Problem Statement
*   **Constraint A**: The generic "Host" repo is massive/legacy and cannot be moved to the client.
*   **Constraint B**: "Weaves" (Code estimation/Context) depend on the Host's build system/environment and must run there.
*   **Constraint C**: Antigravity (The Brain) runs on a Client (Laptop) and needs *actual source files* to edit, but cannot hold the entire repo.

## 2. Proposed Architecture: The Hologram Projection

We treat the Local Client repo as a **Hologram**—a sparse, temporary projection of the Remote Host repo.

### A. Components
1.  **Remote Host (The Truth)**
    *   **Role**: Stores the "Real" code, runs Builds, runs Weaves.
    *   **Agents**: Runs `DDD` (Watcher) and `LocalSmith` (Ops).
2.  **Local Client (The Hologram)**
    *   **Role**: Runs Antigravity. Holds a *partial* copy of relevant files.
    *   **Agents**: Runs `Projector` (New Agent) to manage sync.

### B. The Workflow Cycle
1.  **Context Request (Client -> Host)**
    *   Antigravity needs to work on `Task X`. It asks Host: "Run weave on `path/to/module`".
2.  **Weave & Dependency Mapping (Host)**
    *   Host runs `weave`. It identifies `module.c` and its dependencies `header.h`, `libs/utils.c`.
    *   Host sends this *file list* (and potentially the content) back to Client.
3.  **Projecting (Host -> Client)**
    *   The `Projector` on the Client "materializes" these specific files into the local Hologram folder, mimicking the remote directory structure.
    *   *External Dependencies*: If `weave` identifies external libs, the Host sends their interfaces (headers/stubs) to the Client so the LLM can see definitions.
4.  **Editing (Client)**
    *   Antigravity edits `module.c` locally in the Hologram.
5.  **Write-Back (Client -> Host)**
    *   On save, the `Projector` syncs the changed file back to the Host.
6.  **Verification (Host)**
    *   Host detects change (via `DDD`), runs build/test, and reports status via Radio.

### C. Communication: SSH + Rsync
*   **Control Plane**: SSH Streams (Mission Log).
*   **Data Plane**: `rsync` (or `scp`) to fetch projected files and push edits.

## 3. Implementation: "Remote Auto-Ghost" (The Projector)
We leverage the existing **"Auto-Ghost"** strategy (defined in `specs/large_repo_strategy.md`) which scans compilation databases for out-of-tree dependencies.

The **Projector** is effectively a **Remote Auto-Ghost**:
1.  **Analyze**: Antigravity runs a remote `weave` (which uses `c_context.py` and `auto_ghost` logic) to find the "Working Set" + "Implicit Dependencies".
2.  **Ghost**: instead of Docker mounting, we `rsync` these files to the client.
3.  **Project**: The Client sees a "Ghost Repo" containing only the necessary partial state.

### Tooling
*   `projector pull <remote_path>`: Fetches file + auto-ghost dependencies.
*   `projector push <local_path>`: Syncs changes back.
*   `projector watch`: Daemon that auto-pushes edits on save.

## 4. Observability & Persistence (TMUX)
The Host is the "Radio Tower". It must run continuously.
*   **The Tower Session**: On the Host, we launch a named tmux session:
    ```bash
    tmux new-session -s mission_tower
    ```
*   **The Watcher**: Inside `mission_tower`, we run the `dd-daemon` (or equivalent watcher) in the foreground.
*   **Remote View**: The Client can inspect the state anytime via:
    ```bash
    ssh -t user@host "tmux attach -t mission_tower"
    ```

## 5. Safety Rails: The "Wall" Metaphor
We strictly enforce a boundary between "Inside" (Editable) and "Outside" (Read-Only).

*   **The Wall**: A logical barrier enforced by the Projector.
    *   **Inside the Wall (Editable)**: The specific source files you requested to work on.
    *   **Outside the Wall (Read-Only)**: Everything else, including:
        *   Dependencies fetched via "Auto-Ghost".
        *   System headers.
        *   Unrelated source modules.

### Enforcement
1.  **Projector Pull**: When fetching "Ghost" dependencies, the Projector saves them to a `outside_wall/` directory and sets permissions to **Read-Only (444)**.
2.  **Edit Boundaries**: Antigravity is instructed: "You are editing `src/module.c`. `outside_wall/lib.h` is visible for reference but is BEHIND THE WALL."
3.  **Push Guard**: `projector push` refuses to sync any file path that resides in `outside_wall/` or is formatted as a dependency.

## 6. Migration Plan
1.  **Stop Coder**: `docker stop aider-vertex` on Host.
2.  **Launch Tower**: `ssh user@host "cd /path/to/repo && ./.mission/tools/bin/launch_tower"`
3.  **Start Client**: Run Antigravity on Laptop.
    *   `projector init user@host --remote-root /path/to/repo`
    *   `antigravity start`
