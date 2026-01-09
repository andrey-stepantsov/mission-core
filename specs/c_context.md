# Context X-Ray Specification (`c_context`)

## Goal
Provide physical, container-accessible paths for C/C++ dependencies to the AI agent.

## Core Logic
The tool operates in the "Context Pipe" between the `weave` tool and the Source Code.

1.  **Input:** A target source file (e.g., `drivers/hal/hal.c`).
2.  **Resolution:**
    * Find the file in `compile_commands.json`.
    * Extract `-I` (include) and `-isystem` flags.
    * **Re-Home:** Detect if the DB paths start with a Host Prefix (e.g., `/Users/me/...`) that differs from the Container (`/repo/...`). Rewrite paths dynamically.
3.  **Scan:** Parse the source file for `#include "..."` directives.
4.  **Resolve:** Match includes against the re-homed search paths.
5.  **Output:** JSON object containing:
    * `includes`: List of absolute, accessible paths to headers.
    * `missing`: List of headers that could not be found (diagnostic signal).

## Integration
* **Caller:** `tools/lib/weave.py` calls `c_context` when the `--expand` flag is used.
* **Consumer:** Aider uses the output to `/add` the headers to the chat context.