# Mission Core: Project Overview and Operational Hygiene

## 1. Project Identity
**Mission Core** (v2.2.0-alpha) is a containerized hybrid swarm infrastructure designed for autonomous DevOps. It orchestrates a team of agents (Director, LocalSmith, Builder) to perform complex coding and operational tasks within a sandboxed environment.

## 2. The "Nested Ghost Repository" Pattern
This project implements a unique **"Nested Ghost"** architecture to separate the *Engine* (the toolchain) from the *Workplace* (the target repo).

*   **Host Repository**: The root directory (e.g., `chaos/`) is the "Workplace". It is unaware of the Mission Pack.
*   **Engine Repository**: The `.mission/` directory is the "Mission Pack". It acts as a standalone, nested repository that contains the source code for the agents and infrastructure.

### Ghost Directories
The system relies on specific directories that are strictly `gitignored` in the host repository to maintain hygiene.

| Directory | Type | Description |
| :--- | :--- | :--- |
| `.mission/` | **Persistent** | The Engine source code. This is a productive repository. |
| `.mission-context/` | **Volatile** | Live communication logs ("Radio Protocol") and context matching. |
| `.weaves/` | **Volatile** | Output from the `weave` tool (codebase analysis fragments). |
| `.ddd/` | **Mission-Specific** | Agent configs, raw execution logs, and dynamic filters. |

## 3. Architecture & Communication
*   **Hybrid Swarm**: A mix of Host-native processes (to manage Docker) and Containerized Agents (to execute unsafe code).
*   **Radio Protocol**: Communication occurs via shared files in `.mission-context/`. This design bypasses network stack requirements and ensures strict isolation.
*   **Isolation**: Agents operate in a Docker container (`mission-core`) with specific read/write mounts.

## 4. Operational Hygiene & Cleanup
To reset the system state without destroying persistent data:

1.  **Backup Volatile Data** (Optional but recommended):
    *   Move `.mission-context` to `.mission-context.bak`
    *   Move `.weaves` to `.weaves.bak`
2.  **Clear Logs**:
    *   Remove or archive `.ddd/last_run.log`
3.  **Bootstrap**:
    *   The system auto-regenerates `.mission-context` structure on the next run.

## 5. Verification
The project includes a robust regression suite at `.mission/tests/run_suite.sh` which validates:
*   Docker Environment Health
*   Host/Container Radio Protocol
*   Director Startup Latency
*   Swarm Integration
*   Log Replay Functionality
