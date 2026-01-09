# Large Repository Strategy: The "Context Engine"

## Context
Deploying AI agents on massive C/C++ monorepos (1M+ LOC) introduces unique performance cliffs not seen in Python/JS web projects.

## 1. The "Repository Map" Hang
**Problem:** Aider scans the entire git tree to build a "mental map," causing hangs on startup (10+ minutes) and context window exhaustion.
**Mitigation:** **Weave-Sync**.
* We do *not* let the AI see the whole repo.
* We generate a `.aiderignore` that whitelists *only* the files in the active `weave.yaml` views.
* Everything else is ignored by default.

## 2. The "N+1" JSON Bottleneck
**Problem:** Parsing `compile_commands.json` (often 500MB+) for every single file query is O(N^2) and slow.
**Mitigation:** **Context X-Ray (`c_context`)**.
* Instead of grepping the JSON, we use a dedicated python tool (`c_context.py`).
* It performs "Host Prefix Re-homing" to map Host DB paths to Container Runtime paths.
* It filters "System Headers" (std libs) to prevent polluting the context with unrelated boilerplate.

## 3. The "Hermetic Blindness" (External SDKs)
**Problem:** Embedded projects often reference SDKs outside the git tree (e.g., `/opt/sdk`). Containers cannot see these by default.
**Mitigation:** **Dual-Mount Ghosting**.
* `auto_ghost` scans the compilation DB before launch.
* It detects absolute paths outside the repo.
* It mounts them into the container at **both** the Physical Path (Host reality) and Logical Path (DB expectation) to ensure the compiler finds them.

## 4. The Validation Strategy: "Chaos Generator"
**Problem:** We cannot verify these tools on proprietary code.
**Mitigation:** **The Chaos Tool**.
* We use `tools/bin/chaos` to generate "Perfectly Broken" synthetic repositories.
* It simulates Out-of-Tree includes, missing headers, and split-brain build systems (Host vs. Container).