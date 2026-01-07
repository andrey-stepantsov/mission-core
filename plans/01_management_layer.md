# 02. Mission Control Architecture

## 1. The Vision
We are moving from a "Toolbox" model (scripts in a drawer) to a "Mission Control" model. The Mission Pack is a live, self-contained environment that "docks" with a project to provide AI-assisted development capabilities (Dashboards, Context Management, Build Tools) without polluting the product source code.

## 2. The Deployment Pattern: "Hidden Satellite"
The Mission Pack is deployed as a **Git Submodule** to ensure bi-directional sync (fixes can be pushed back) and version locking.

* **Project Root:**
    * `src/`: Product Code (Pure, Zero Dependency on Mission Pack).
    * `.ddd/`: Domain Definitions (Project-specific rules/context).
    * `.mission/`: The Mission Pack Submodule (The Engine).

## 3. Repository Structure (The Mission Pack)
The `srl-mission-pack` repository is "flattened" so the root *is* the toolbox.

(Structure omitted for brevity - bin/ lib/ layouts/ containers/)

## 4. The Workflow
1.  **Install:** `git submodule add <url> .mission`
2.  **Launch:** `./.mission/bin/dash`
3.  **Operate:**
    * **Window 1 (Architect):** High-level design, read-only access to `src/`, full access to `.ddd/`.
    * **Window 2 (Coder):** Implementation, write access to `src/`.
    * **Window 3 (Shell):** Execution and testing.

## 5. Implementation Roadmap

### Phase 1: Foundation (Current)
- [x] **Refactor:** Flatten repository structure (`tools/` -> root).
- [x] **Plumbing:** Update `bootstrap.sh` to support self-contained `.venv`.
- [x] **CLI:** Ensure `bin/weave` works with new paths.

### Phase 2: The Dashboard
- [ ] **`bin/dash`:** Create the TMUX wrapper script.
- [ ] **Layouts:** Define standard window splits (Editor + Terminal).
- [ ] **Personas:** Create `bin/architect` and `bin/coder` wrappers for Aider.

### Phase 3: The Context Pipe
- [ ] **Handoff:** Create tools to pipe chat history/summary from Architect to Coder.
- [ ] **Container:** Implement `bin/shell` to run tools inside a hermetic container.
