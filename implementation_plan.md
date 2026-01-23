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

### Phase 2: Automation (Deferred)
**Goal:** Streamline Phase 1 with CLI flags.
**Planned Feature:**
-   Update `projector build` to accept `--verify="cmd"` or `--build="cmd"`.
-   The tool will automatically:
    1.  Read current config.
    2.  Patch it with the new command.
    3.  Push the temporary config.
    4.  Trigger the build.
    5.  (Optional) Revert the config?

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

