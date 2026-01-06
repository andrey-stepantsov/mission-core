# Field Test: Operation "Hello Weave"

## Context
**Role:** Developer (Consumer of the Mission Pack)
**Repo:** `/repos/mock-repo`
**Toolchain:** `/repos/srl-mission-pack/tools`

## Objective
Verify that the 'Weave' toolchain works in a consumer environment by creating a simple "Hello World" feature in the mock repository.

## Task List
1.  **Environment Check:**
    * Verify `tools/bin/weave` is executable.
    * Verify `tools/lib/bootstrap.sh` exists.

2.  **Implementation:**
    * Create a script `my_feature.py` in the mock repo.
    * Use the `weave` library to print a success message in JSON format.
    * **Constraint:** You MUST use the standard `bootstrap.sh` header found in `tools/lib/bootstrap.sh`.

3.  **Verification:**
    * Run the script and ensure it outputs valid JSON.
