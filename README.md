# Mission Core v2.9.0: Projector Run & UX Fixes

**Mission Core** is a containerized agent infrastructure that provides a **Unified Projector Interface** for autonomous coding agents. It abstract local and remote environments into a consistent API for context, search, and synchronization.

## 🏗 Architecture
The system uses `projector` as the central engine:
- **Remote Brain**: Mirrors a remote host ("Oracle") to a local sparse workspace ("Hologram") via SSH.
- **Local Brain**: Manages a local repository using the same API via direct filesystem operations.

## 📦 Deployment
See [docs/UNIFIED_DEPLOYMENT.md](docs/UNIFIED_DEPLOYMENT.md) for the universal installation guide.

## 🚀 Quick Start
```bash
# 1. Initialize (Remote or Local)
./tools/bin/install.sh [remote|local]

# 2. Start the Agent
./tools/bin/up
```

## 🛠 Active Agents
| Agent | Role |
|-------|------|
| **LocalSmith** | Managing files, running builds, executing verifications. |
| **Projector** | Polymorphic transport layer (SSH/Local) for data access. |
