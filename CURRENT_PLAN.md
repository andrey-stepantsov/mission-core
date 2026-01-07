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
2.  **Launch:** `./.mission/dash` (or `./dash`)
3.  **Operate:**
    * **Left (Architect):** Strategy & Design (Read-Only).
    * **Center (Coder):** Implementation (Dockerized).
    * **Right (Ops):** Shell & Monitoring.

## 5. Implementation Roadmap

### Phase 1: Foundation (Complete)
- [x] **Consolidate:** Ensure all tools live in `tools/`.
- [x] **Plumbing:** Update `bootstrap.sh` to handle nested structure.
- [x] **CLI:** Ensure `tools/bin/weave` runs correctly.

### Phase 2: The Dashboard (Complete)
- [x] **`tools/bin/dash`:** Create the TMUX wrapper script (3-Column Layout).
- [x] **Layouts:** Implemented "Cockpit" view.
- [x] **Personas:** Created `architect` and `coder` wrappers for Docker.

### Phase 3: The Context Pipe (Next)
- [ ] **Mounting:** Ensure the Docker container can see and execute `tools/bin/weave`.
- [ ] **Handoff:** Create tools to pipe chat history/summary.
- [ ] **Integration:** Verify Aider can use `weave` to load files.
