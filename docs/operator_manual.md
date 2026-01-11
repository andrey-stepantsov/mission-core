# 🎮 Mission Control: Operator Manual

## 1. The Dashboard (`./dash`)

When you launch `.mission/dash`, you enter the **Mission Control Center**.

| Pane | Role | Description |
| :--- | :--- | :--- |
| **0 (Left)** | **Architect** | The Planner. Read-Only access. High reasoning. Ask it to "Plan feature X". |
| **1 (Center)** | **Coder** | The Builder. Write access. Implements the plan. Works inside the container. |
| **2 (Bottom)** | **Shell** | **The Clean Room.** A hermetic shell inside the container. Use this to run `make`, `tests`, or `git` to ensure you see what the AI sees. |
| **3 (Right)** | **Monitor** | **The Host.** Logs and System stats. Runs on your physical machine. |

## 2. The Workflow

### Step 1: Design (Architect)
* **User:** "We need a new driver for the BCM chip."
* **Architect:** Analyzes `specs/`, checks `weave map`, produces a Markdown plan.

### Step 2: Handoff
* **User:** "Plan looks good. @Coder implement it."
* **System:** The Architect writes to `handoff`, Coder reads it.

### Step 3: Implementation (Coder)
* **Coder:** Writes code, creates tests.
* **Constraint:** The Coder cannot run heavy builds. It relies on the "Parasitic Mode" or "Container Shell".

### Step 4: Verification (Shell)
* **User:** Switch to Pane 2 (Shell).
* **Command:** `./tests/run_tests.sh` (or `make`).
* **Why?** This ensures the environment matches the Coder's expectation exactly.

---

## 3. Command Cheatsheet

### 🧠 Context & Navigation
| Command | Description |
| :--- | :--- |
| `weave list` | Show available context views (e.g., `sdk`, `app`). |
| `weave get <view>` | Load files for a specific view. |
| `weave map callers <func>` | **Trace Dependencies.** See who calls a function. |
| `weave map callers <func> -H` | **Human Mode.** Get a copy-pasteable `/read` command. |

### 🛠️ Development
| Command | Description |
| :--- | :--- |
| `.mission/shell` | Launch the container shell (Interactive). |
| `.mission/shell make` | Run a build command inside the container (One-off). |

---

## 4. The Golden Rules

1.  **Trust the Wrapper:** Never run `gcc` manually. Always use the provided build scripts or `.mission/shell`.
2.  **Ghost Mode:** If you need an external SDK (e.g., `/opt/sdk`), define it in `compile_commands.json`. The system will auto-mount it.
3.  **Nuclear Ignore:** If `sync_ignore` is active, Aider ignores everything by default. You MUST use `weave` to whitelist files for the context.
