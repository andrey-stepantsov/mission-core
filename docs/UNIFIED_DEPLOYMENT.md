# Mission Pack: Unified Deployment Guide (v2.8.0)

## Overview
The Mission Pack now features a **Unified Projector Architecture**. Both Remote and Local operational models use the `projector` engine to manage file synchronization and compilation context. This ensures a consistent interface for AI agents regardless of the deployment environment.

## Operational Models

### 1. Remote Brain (Hologram Mode)
**Best for:** Large codebases, cross-platform development.
- **Transport:** `ssh`
- **Workflow:** Local "Hologram" mirrors a remote "Oracle".
- **Key File:** `.hologram_config` (sets `transport: ssh`).

### 2. Standardized Local Mode (Unified Interface)
**Best for:** Local development, containerized environments.
- **Transport:** `local`
- **Workflow:** Standardizes repo access via the `projector` API.
- **Key File:** `.hologram_config` (sets `transport: local`).
- **Benefit**: AI agents use the same `projector context` API, enabling unified system prompts.

---

## Installation

The `install.sh` script is the universal entry point.

### Remote Setup
```bash
./.mission/tools/bin/install.sh remote <user@host> <remote_root>
```

### Local Setup
```bash
./.mission/tools/bin/install.sh local
```

---

## The Unified Interface

Regardless of where your code lives, the AI agent interacts with it the same way:

| Command | Action | Standardized Behavior |
|---------|--------|-----------------------|
| `projector context <file>` | Get Context | Extracts macros/includes from local DB. |
| `projector pull <file>` | Sync File | Mirrors source to workspace (Local or SSH). |
| `projector push <file>` | Push File | Syncs changes back to the source repository. |
| `projector grep <path>` | Search | Executes `rg` (Local or SSH) and maps paths. |

## Observability & Hygiene

### Shell History
All commands are prepended with `unset HISTFILE;` to maintain clean user history.

### Telemetry
`projector context` emits mode status to `stderr` to help diagnose context resolution:
- `🔮 Projector: Hologram Mode active.` (Local or SSH config found)
- `🧠 Projector: Direct Mode active.` (No config found, using CWD)
