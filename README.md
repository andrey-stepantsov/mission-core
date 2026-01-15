# Mission Core v0.3.0: Hybrid Swarm

**Mission Core** is a containerized agent infrastructure designed for autonomous DevOps tasks. It bridges the gap between a **Host Orchestrator** (macOS/Linux) and **Isolated Agents** (Docker).

## 🏗 Architecture
The system uses a **Radio-based Communication Protocol** to bypass Docker network isolation without exposing ports.

* **Director (Host):** Writes commands to a shared log file (`.mission-context/mission_log.md`).
* **LocalSmith (Container):** Tails the log file, executes commands, and writes back ACKs.
* **Radio (Shared Lib):** Handles atomic file I/O and absolute path resolution.

## 🚀 Quick Start
```
# 1. Start the Agent
./tools/bin/up

# 2. Run the Health Check Suite
./tests/run_suite.sh
```

## 🛠 Active Agents
| Agent | Type | Role |
|-------|------|------|
| **LocalSmith** | Docker | Infrastructure Engineer. Can edit configs, manage files, and run shell verifications. |
| **Director** | Host | Mission Control. Sends commands to agents. |
