# The Triple-Head Workflow

You are the **Coder**. You do not build; you **Signal**.

## The Loop
1.  **Analyze:** Run `ddd-wait` (Target: `audit`) to get the file map and headers.
2.  **Edit:** Modify source files in `src/`.
3.  **Signal:** Run `ddd-wait` (Target: `dev`).
    * *Do not run `./rmk` or `./lmk` directly.*
    * *Do not run `gcc` or `clang` directly.*
4.  **Review:** Read the output. The Host Daemon will compile and return the logs to you.

## Troubleshooting
* If the build says "Header not found", run the `audit` target again to force `ctx` to re-scan for includes.
