# Cycle 2: The Mission Pack Management Layer

## 1. Context & Status
**Current Phase:** Platform Engineering (Cycle 2)
**Repo:** `/repos/srl-mission-pack`
**Role:** "The Toolsmith" (Building tools for other Agents)

We have successfully extracted the "Weave" prototype (Cycle 1) into a permanent Mission Pack. The goal now is to build the **Management Layer**—a set of meta-tools that allow the Agent to manage its own state (Identity, Focus, and Memory) without breaking the "Fourth Wall."

## 2. Architecture: The "Context Switcher"
We are moving away from static configurations to a **Dynamic State Machine**.

### A. The Plan System (Focus)
* **Storage:** All plans live in `plans/*.md`.
* **Active State:** `CURRENT_PLAN.md` is a **symlink** to the active plan.
* **Benefit:** The Agent always knows *what* to work on by reading `CURRENT_PLAN.md`, but can switch priorities instantly by changing the symlink.

### B. The Phase System (Identity)
* **Storage:** Identity rules live in `prompts/system/{role}_rules.md`.
* **Active State:** `CONVENTIONS.md` is a **copy** of the active role.
* **Benefit:** An "Architect" follows different rules than a "Builder." The Agent adapts its behavior by running a command.

### C. The Telemetry System (Memory)
* **Storage:** Logs live in `data/logs/YYYY-MM-DD_HH-mm_{Label}.md`.
* **Benefit:** Preserves "Flight Recorder" data across `/reset` boundaries for future analysis.

## 3. Implementation Plan (The To-Do List)

### ✅ Step 0: Setup
- [x] Extract Prototype Code (Completed in Cycle 1).
- [x] Create `plans/` directory and save this file.
- [x] Create `prompts/system/architect_rules.md` (Drafted).
- [x] Create `prompts/system/builder_rules.md` (Drafted).

### 🛠️ Step 1: `bin/snapshot` (Telemetry)
**Spec:**
-   **Input:** Optional label string (e.g., "End of Cycle 2").
-   **Action:** Captures `.aider.chat.history.md` and `.aider.input.history`.
-   **Output:** `data/logs/{timestamp}_{label}.md`.
-   **Constraint:** Must handle the case where history files don't exist (fresh session).

### 🛠️ Step 2: `bin/phase` (Identity)
**Spec:**
-   **Input:** `role` (e.g., `architect`, `builder`).
-   **Action:** Copies `prompts/system/{role}_rules.md` -> `CONVENTIONS.md`.
-   **Output:** "Switched to {role} mode. Please notify Aider."

### 🛠️ Step 3: `bin/plan` (Focus)
**Spec:**
-   **Input:** `plan_name` (filename in `plans/` without extension).
-   **Action:** Updates `CURRENT_PLAN.md` symlink.
-   **Output:** "Focus shifted to {plan_name}."

## 4. Development Constraints
1.  **Bootstrapping:** All Python tools must use the `lib/bootstrap.sh` wrapper pattern.
2.  **Isolation:** Do not pollute the root. Runtime data goes to `data/`.
3.  **Dependencies:** Add new libs to `tools/requirements.txt`.
