# Mission Core: Architecture Reference

## SYNOPSIS

**Mission Core** is a portable "AI Developer Environment" that docks into any C/C++/Python repository. It provides a pre-configured suite of AI agents ("Personas") and context-management tools ("Weave") without altering the host project's source code or build system.

## QUICK START

### 1. Mount the Mission
Run this in your project root to dock the satellite:
```bash
git submodule add https://github.com/andrey-stepantsov/mission-core .mission
```

### 2. Launch
**Option A: Mission Control (Recommended for Tmux users)**
Launches a 3-pane dashboard with Architect, Coder, and Shell ready to go.
```bash
./.mission/dash
```

**Option B: Standalone Agents (For separate terminals)**
If you prefer your own terminal layout, launch agents individually:
```bash
# Terminal 1: The Planner
./.mission/architect

# Terminal 2: The Builder
./.mission/coder
```

## KEY ARCHITECTURAL DECISIONS

### 1. The "Ghost" Submodule Pattern
**Decision:** The pack is deployed as a Git Submodule, typically mapped to `.mission/`.
**Why:**
* **Zero Pollution:** The host repository root remains clean.
* **Bi-Directional:** Bug fixes to tools can be pushed upstream.
* **Versioning:** The host project locks tools to a specific commit.

### 2. Dockerized & Hermetic Deployment
**Decision:** The tooling operates in isolation using a self-bootstrapping `.venv` inside the submodule.
**Why:**
* **Zero Dependency:** The host machine only needs `git`, `python3`, and `tmux`.
* **Consistency:** Agents run in a controlled environment, identical across all developer machines.

### 3. DDD-Driven Context (.ddd needed)
**Decision:** The Mission Pack encourages a `.ddd/` (Domain Driven Design) directory in the host project root.
**Why:**
* AI Agents cannot guess architectural intent from legacy code alone.
* The `.ddd/` folder contains the "Map": rules and boundaries that guide the "Architect" persona.

## DETAILS

### Directory Structure
We use a **Nested** structure to separate the Public Interface from the Engine.

```text
/ (Mission Root)
├── dash                     # [Entry] Full Dashboard (Tmux)
├── architect                # [Entry] Architect Persona
├── coder                    # [Entry] Coder Persona
├── weave                    # [Entry] Context Manager
├── specs/                   # Technical Documentation
└── tools/                   # THE ENGINE (Hidden Logic)
    ├── bin/                 # Implementation scripts
    ├── lib/                 # Shared libraries
    ├── layouts/             # TMUX window definitions
    └── .venv/               # Hermetic Python Environment
```

### The Personas

| Persona | Script | Role |
| :--- | :--- | :--- |
| **Architect** | `./architect` | **Design & Plan.** Read-Only access to source. High reasoning capability. |
| **Coder** | `./coder` | **Implement.** Write access. Focus on code generation and testing. |
| **Mission Control** | `./dash` | **Orchestrate.** Launches both agents in a unified layout. |
