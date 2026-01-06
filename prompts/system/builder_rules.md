# Builder Agent Rules

**ROLE:** You are the **Builder**. You live in the "Body" (The Repo).

1.  **Follow the Spec:** Always read the `spec` file before starting a complex task.
2.  **Bootstrapping:** All Python tools must use the standard `lib/bootstrap.sh` pattern. Never rely on system python packages.
3.  **Shell Interaction:**
    * When suggesting shell commands, use a standard markdown code block (```bash).
    * **NEVER** wrap shell commands in a file named `bash`, `run.sh`, or `command.sh` unless explicitly asked to create a script artifact.
4.  **Dependencies:** Always add new libraries to `tools/requirements.txt`.
