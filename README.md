# Mission Core v0.3.0: Hybrid Swarm

**Mission Core** is a containerized agent infrastructure designed for autonomous DevOps tasks. It bridges the gap between a **Host Orchestrator** (macOS/Linux) and **Isolated Agents** (Docker).

## 🏗 Architecture
The system uses a **Radio-based Communication Protocol** to bypass Docker network isolation without exposing ports.

* **Director (Container):** Writes commands to a shared log file (`.mission-context/mission_log.md`).
* **LocalSmith (Container):** Tails the log file, executes commands, and writes back ACKs.
* **Radio (Shared Lib):** Handles atomic file I/O and absolute path resolution.

## 📦 Deployment
See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed setup instructions.

*   **Supported Platforms**: Linux (AMD64), macOS (Intel & Apple Silicon/M1).
*   **Apple Silicon**: The launcher automatically performs a **Native Bootstrap** to build an ARM64-optimized image, ensuring high performance and stability.

## 🚀 Quick Start
# 1. Start the Agent
./tools/bin/up

# 2. Run the Health Check Suite
# Requires Devbox (Python 3.8)
devbox run ./tests/run_suite.sh
```

## 🧪 Development
We use **Devbox** to ensure a consistent **Python 3.8** environment associated with legacy production constraints.

### Running Tests
*   **Unit Tests (Fast)**: `devbox run "pytest -m unit"`
*   **Integration Tests (Slow)**: `devbox run "pytest -m integration"`
*   **Full Regression**: `./tests/run_suite.sh` (or `devbox run ./tests/run_suite.sh`)

## 🛠 Active Agents
| Agent | Type | Role |
|-------|------|------|
| **LocalSmith** | Docker | Infrastructure Engineer. Can edit configs, manage files, and run shell verifications. |
| **Director** | Docker | Mission Control. Sends commands to agents. |
