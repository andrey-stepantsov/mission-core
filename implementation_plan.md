# Implementation Plan - Dynamic Remote Build Configuration

# Goal Description
Enable precise, file-specific build and verification workflows on the remote host by leveraging the existing file synchronization capabilities of `projector`. Instead of building a complex payload protocol for `dd-daemon`, we will use `.ddd/config.json` as a mutable "Instruction Register" that the AI/User updates, pushes, and executes.

## User Review Required
> [!NOTE]
> This approach relies on the "Projector Pattern" where configuration is **data**. To change *what* the daemon does, we simply change the configuration file on the remote.

## Proposed Changes

### Phase 1: The Protocol (Manual / AI-Driven)
**Goal:** Enable dynamic build/verify commands immediately without further code changes.
**Mechanism:** "Configuration as Data"
1.  **Pull**: User/AI runs `projector pull .ddd/config.json`.
2.  **Edit**: Modify `"build"` or `"verify"` commands in `hologram/.ddd/config.json` locally.
3.  **Push**: Run `projector push .ddd/config.json`.
4.  **Trigger**: Run `projector build`.
    *   **Result**: The remote `dd-daemon` (now Python-based) reloads the config dynamically and executes the new command.
    *   **Context**: If the working directory changed, `projector build` automatically restarts the daemon (logic confirmed in `build.py`).

### Phase 2: Automation (Implemented)
**Goal:** Streamline Phase 1 with CLI flags.
**Feature:**
-   Updated `projector build` to accept `--verify="cmd"`, `--build="cmd"`, and `--path="dir"`.
-   The tool automatically:
    1.  Reads current config.
    2.  Patches it with the new command.
    3.  Pushes the updated config to `.ddd/config.json`.
    4.  Triggers the build.

## Verification Plan (Phase 1)

### Manual Verification
1.  **Setup**: Ensure `projector` is initialized and `dd-daemon` is running.
2.  **Config**: 
    -   `projector pull .ddd/config.json`
    -   Edit `hologram/.ddd/config.json`: Set `"verify": {"cmd": "echo 'Dynamic Verification Active!'"}`
    -   `projector push .ddd/config.json`
3.  **Execution**:
    -   Run `projector build`
4.  **Validation**:
    -   Check logs: `projector log`
    -   Expect to see: `Dynamic Verification Active!` output.


## Phase 3: Structured Diagnostics (Completed)
**Goal:** Close the feedback loop by making build output machine-readable and actionable.

### Changes Implemented
1.  **`projector` Client Updates**:
    -   **Local Support**: Patched `sync.py`, `build.py`, `run.py` to support `host_target: "local"` via direct execution (bypassing SSH).
    -   **Robust Monitoring**: Updated `monitor.py` to detect "Build Stats" as completion signal, enabling support for unmodified `dd-daemon`.
    -   **Full Log Context**: Increased tail buffer to capture complete JSON blobs.

2.  **Verification**:
    -   Created `tests/autofix_demo.py` to prove the loop.
    -   Verified `gcc_json` filter output is parseable by the Agent.

### Verification Plan
1.  **Radio Signal Check**:
    -   *Superseded*: Uses "Build Stats" as implicit signal. Verified `projector build --wait` exits correctly.
2.  **Dynamic Filter Switching**:
    -   Verified via `autofix_demo.py` which pushes `config.json` enabling `gcc_json`.
3.  **Autofix Scenario**:
    -   Run `python3 .mission/tests/autofix_demo.py`.
    -   Result: **Success**. Script auto-corrected a missing semicolon.
