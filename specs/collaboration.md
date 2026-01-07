# Agent Collaboration Protocol

## Overview
This specification defines how the **Architect** (Planner/Supervisor) and the **Coder** (Worker) communicate and coordinate within the Mission Pack.

## 1. Separation of State
To enable supervision, agents must operate with distinct history files. They must not pollute each other's context.

* **Architect:** Uses `.aider.architect.history.md`.
* **Coder:** Uses `.aider.coder.history.md`.

## 2. The Forward Channel: Instruction (`handoff`)
The **Architect** directs the **Coder** via "The Memo".

### Data Structure
File: `.mission/memo.md`

### CLI Usage
* **`handoff write "Message" [--file <path>]`**
    * **User:** Architect.
    * **Action:** Overwrites the memo with a message and optionally attaches a file (like a plan or spec).
* **`handoff read`**
    * **User:** Coder.
    * **Action:** Prints the current memo. The Coder should run this at the start of a task.

## 3. The Backward Channel: Monitoring (`inspect`)
The **Architect** monitors the **Coder** to detect hallucinations or infinite loops.

### CLI Usage
* **`handoff inspect [--lines 50]`**
    * **User:** Architect.
    * **Action:** Reads the tail of `.aider.coder.history.md`.
    * **Goal:** Allow the Architect to "see what the Coder is doing" without intervening.

## 4. The Control Loop: Intervention
When the Architect detects a failure state in the Coder:

1.  **Snapshot:** Architect runs `snapshot "failure_analysis"` to archive the Coder's bad state.
2.  **Reset:** (Manual/Future) The Coder's context is cleared.
3.  **Redirect:** Architect runs `handoff write` with a corrected plan.

## System Prompts Update
* **Architect:** "You are the Manager. Use `handoff inspect` to check on the Coder. If they are stuck, snapshot and issue new instructions."
* **Coder:** "You are the Builder. Check `handoff read` for your orders."
