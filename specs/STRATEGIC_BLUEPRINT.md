# Mission Core: Strategic Roadmap (v2.0+)

**Vision:** Transform Mission Core from a specialized C/C++ tool into a **Universal Development Console** capable of hot-swapping toolchains ("Cartridges") for any environment (Nix, Docker, Python, Legacy).

## 1. The Core Concept: "Console & Cartridges"

We separate the **Engine** (The AI/UI) from the **Context** (The Tools/Prompts).

* **The Console (`.mission/`):** The immutable engine. Contains `dash`, `leader`, `coder`, and the container runtime. It provides the *capability* to plan and code.
* **The Cartridge (Context):** A pluggable configuration that defines *how* to build and *who* the agents are.

### Architecture Diagram
```text
[ Repo Root ]
├── .mission/ (The Console)
│   ├── tools/bin/leader   <-- The Brain (Loads Persona)
│   └── tools/bin/ddd      <-- The Hands (Loads Build Config)
│
├── .mission-context/ (The Active Cartridge)
│   ├── mission.yaml       <-- Manifest (Name, Version)
│   ├── leader_rules.md    <-- "I am a Nix Architect"
│   └── ddd_config.json    <-- "Build with `nix build`"
│
└── .ddd/ (The Runtime)
    └── run/               <-- Local Sockets/PID (Isolated)
```

## 2. Implementation Phases

### Phase 1: Identity & Pluggability (Immediate)
**Goal:** Enable the "Leader" to load prompts from the project root.
* **Refactor:** Rename `Architect` -> `Leader`.
* **Mechanism:** `launch_container.sh` detects and mounts `.mission-context/` if present.
* **Result:** Custom C/C++ personas (e.g., "Embedded Expert") can be loaded per project.

### Phase 2: Isolation (Pre-req for Multi-Project)
**Goal:** Make the build daemon (`ddd`) hermetic to the project.
* **Refactor:** Move `ddd` state from global paths to `.ddd/run/`.
* **Why:** Allows multiple Mission Packs to run simultaneously on one machine without cross-talk.

### Phase 3: The Cartridge System (Future)
**Goal:** Support fundamental toolchain swaps (e.g., Nix).
* **Feature:** `dash --context <name>`
* **Mechanism:** The launcher symlinks a sub-repo (e.g., `.mission/contexts/nix-dev`) to `.mission-context/` before starting.
* **Validation:** Deploy the "Nix/Flake" cartridge to prove the system handles non-standard build flows.

## 3. Technology Stack Priorities
1.  **C/C++ & Bash:** The primary "Brownfield" target. Must work on legacy systems.
2.  **Python:** The automation layer.
3.  **Nix:** The future of "Greenfield" environments. The ultimate stress test for the Cartridge system.
4.  **Docker:** Infrastructure-as-Code support.

## 4. Protocol Upgrades
* **Symmetry:** `handoff` evolves from a simple overwrite buffer to a **Shared Mission Log** (Append-Only Journal).
* **Review:** A new `review` tool runs automated quality gates (lint/diff) inside the container.
