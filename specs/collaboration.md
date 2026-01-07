# Agent Collaboration Protocol

## Overview
This specification defines how the **Architect** (Planner/Supervisor) and the **Coder** (Worker) communicate and coordinate within the Mission Pack.

## 1. Separation of State
To enable supervision, agents must operate with distinct history files. They must not pollute each other's context.

* **Architect:** Uses `.aider.architect.history.md`.
* **Coder:** Uses `.aider.coder.history.md`.

### Architect -> Coder (Forward)

The Architect sends instructions to the Coder using the `/run ./dispatch` command.

`/run ./dispatch "Your instructions for the Coder go here."`

### Coder -> Architect (Backward)

The Coder sends a report or results back to the Architect using the `/run ./submit` command.

`/run ./submit "My work is complete. Here is my report."`

### Architect View (Monitor)

The Architect can view a log of all dispatches and submissions using the `/run ./logs` command.

`/run ./logs`

## 4. The Control Loop: Intervention
When the Architect detects a failure state in the Coder:

1.  **Snapshot:** Architect runs `snapshot "failure_analysis"` to archive the Coder's bad state.
2.  **Reset:** (Manual/Future) The Coder's context is cleared.
3.  **Redirect:** Architect runs `handoff write` with a corrected plan.

## System Prompts Update
* **Architect:** "You are the Manager. Use `handoff inspect` to check on the Coder. If they are stuck, snapshot and issue new instructions."
* **Coder:** "You are the Builder. Check `handoff read` for your orders."
