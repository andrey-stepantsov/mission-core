# C-Context Tool Specification

## Synopsis
The **C-Context Tool** (`tools/bin/c_context`) bridges the gap between the build system (`compile_commands.json`) and the AI's context window. It resolves abstract C/C++ build flags into concrete file paths.

## Motivation
AI Agents often hallucinate header locations or fail to find definitions because C/C++ include paths (`-I`) abstract the physical file structure. This tool parses the compilation database to tell the AI exactly which files are being included.

## CLI Interface
```bash
tools/bin/c_context <target_file> --db <path_to_json> --root <repo_root>
```

### Arguments
* `target_file`: The C/C++ source file to analyze.
* `--db`: Path to the `compile_commands.json` (defaults to `./compile_commands.json`).
* `--root`: The repository root (used for path normalization and filtering).

## Logic Flow
1.  **Lookup:** Locate the entry for `<target_file>` in the compilation database.
2.  **Extraction:** Parse the build command (handling both `command` string and `arguments` list styles) to extract:
    * Defines (`-D`)
    * Include Paths (`-I`, `-isystem`)
3.  **Scanning:** Read the `<target_file>` and extract all `#include "..."` and `#include <...>` lines.
4.  **Resolution:** For each include:
    * Check if it exists relative to the source file (Quote includes).
    * Iterate through extracted Include Paths (`-I`) to find the file.
5.  **Filtering (Safety):**
    * **Whitelist:** Only return headers that reside within the `--root` or its sibling directories.
    * **Blacklist:** Explicitly exclude standard system paths (`/usr`, `/opt`, `/System`) unless they are the root.

## JSON Output Schema
```json
{
  "file": "/abs/path/to/main.cpp",
  "defines": ["_GNU_SOURCE", "ASIC_BCM"],
  "includes": [
    "/abs/path/to/project/local.h",
    "/abs/path/to/sibling/lib/math.h"
  ],
  "system_includes": [
    "/usr/include/stdio.h" 
  ],
  "missing": [
    "some_generated_header.h"
  ]
}
```
* **includes:** Resolved, relevant headers (Safe to add to context).
* **system_includes:** Resolved headers found in system paths (Context noise, usually ignored).
* **missing:** Headers requested by `#include` but not found on disk.
