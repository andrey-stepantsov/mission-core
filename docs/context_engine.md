# The Context Engine: Mastery over Monorepos

The **Context Engine** is a suite of tools designed to help Aider survive in massive (1M+ LOC) C/C++ repositories. It solves three specific problems:
1.  **Noise:** Too many files confuse the AI.
2.  **Ambiguity:** Multiple compile targets (e.g., ARM vs x86) cause hallucinations.
3.  **Isolation:** External dependencies (NFS/SDKs) are often invisible to containers.

---

## 1. The Nuclear Strategy (Focus)

In large repos, the default `.gitignore` is not enough. The **Nuclear Strategy** reverses the logic: **Ignore Everything by default**, then whitelist only what you are working on.

### Configuration (`weave.yaml`)
```yaml
# 1. The Blocklist: Ignore EVERYTHING
ignores:
  - "*"

# 2. The Whitelist: Define your active views
views:
  current_task:
    - "drivers/hal/*.c"
    - "drivers/hal/*.h"
    - "app/core/main.cpp"
```

### Execution
Run this tool to generate the strict `.aiderignore`:
```bash
./.mission/tools/bin/sync_ignore
```
*Result:* Aider will be "blind" to the rest of the repo, saving tokens and preventing distractions.

---

## 2. Target Disambiguation (Precision)

In embedded development, a single file (`kernel.c`) might be compiled 10 times for different ASICs. If Aider picks the wrong compilation flag, it will hallucinate invalid registers.

You can resolve this by adding **Selectors** to your config.

### Configuration (`weave.yaml`)
```yaml
compilation_dbs:
  - "compile_commands.json"

context_selector:
  # Only select compile commands that contain ONE of these flags
  required_flags:
    - "-D_TARGET_ASIC_V3"
    - "-march=riscv"
```

### How it works
When you ask Aider to read a file, the system checks the Compilation DB:
1.  **Too Loose:** If multiple entries match your file, it uses the `required_flags` to pick the winner.
2.  **Feedback:** If your flags are ambiguous (or match nothing), the tool warns you in the chat:
    > `⚠️ TOO LOOSE: Found 4 entries. 2 matched your selectors...`

---

## 3. Auto-Ghost (Connectivity)

Your compilation database often references headers outside the repo (e.g., `/auto/swtools/...` or `/usr/local/sdk`). Docker usually cannot see these.

**Auto-Ghost** scans your active `weave.yaml` and `compile_commands.json` at startup. It automatically finds these external paths and mounts them into the container as Read-Only volumes.

* **NFS Safe:** It uses optimized, read-only mounts that do not trigger SELinux relabeling.
* **Automatic:** No manual `docker run -v ...` required.

---

## 4. Reference: `weave.yaml`

Place this file in your repo root or `.mission/`.

```yaml
# List of Compilation Databases to scan
compilation_dbs:
  - "compile_commands.json"
  - "build/compile_commands.json"
  - "subproject/compile_commands.json"

# Disambiguation Rules
context_selector:
  required_flags: ["-DYOUR_TARGET_FLAG"]

# The Nuclear Option
ignores:
  - "*"

# Active Workspaces (Whitelists)
views:
  my_feature:
    - "src/feature/**"
    - "include/feature/**"
```
