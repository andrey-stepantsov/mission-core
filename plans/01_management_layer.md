# 02. Mission Control Architecture

## 1. The Vision
We are moving from a "Toolbox" model to a "Mission Control" model. The Mission Pack is a live, self-contained environment.

## 2. The Deployment Pattern: "Hidden Satellite"
The Mission Pack is deployed as a **Git Submodule** in `.mission/`.

## 3. Repository Structure (Nested)
We maintain a clean separation between repository metadata and the toolchain.

* `tools/`: The Engine (Scripts, Libs, Venv).
* `specs/`: The Blueprints.
* `plans/`: The Roadmap.
* `prompts/`: The Persona Definitions.

## 4. The Workflow
1.  **Install:** `git submodule add <url> .mission`
2.  **Launch:** `./.mission/tools/bin/dash`
3.  **Operate:**
    * **Window 1 (Architect):** High-level design.
    * **Window 2 (Coder):** Implementation.
    * **Window 3 (Shell):** Execution.

## 5. Implementation Roadmap

### Phase 1: Foundation (Current)
- [x] **Consolidate:** Ensure all tools live in `tools/`.
- [x] **Plumbing:** Update `bootstrap.sh` to handle nested structure.
- [x] **CLI:** Ensure `tools/bin/weave` runs correctly.

### Phase 2: The Dashboard
- [x] **`tools/bin/dash`:** Create the TMUX wrapper script.
- [x] **Layouts:** Define standard window splits (Editor + Terminal).
- [x] **Personas:** Create `tools/bin/architect` and `tools/bin/coder` wrappers.

### Phase 3: The Context Pipe - Verified.
- [x] **Infrastructure:** Create `tools/bin/apply_patch`.
- [x] **Mounting:** Fix Split-Brain bootstrapping for hybrid execution.
- [x] **Integration:** Verify `weave` works inside container.
- [x] **Handoff:** Create `tools/bin/handoff` for Agent-to-Agent communication.
- [x] **Container:** Implement `tools/bin/shell` (Hermetic).

> **Note:** The "Dispatch/Review Protocol" is now active.
