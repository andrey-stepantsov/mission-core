# Coverage Gap Analysis

**Date:** 2026-01-22
**Total Coverage:** 44%

## 1. Monitor (Critical Risk)
*   **File:** `monitor.py`
*   **Coverage:** 7%
*   **Gap:** The entire `monitor_build` function is untested.
*   **Reason:** It contains an infinite `while True` loop and relies on `subprocess` calls to `ssh` `tail -F`. This is "interactive" logic.
*   **Impact:** If `dd-daemon` changes its log format or signals, `projector build --wait` will hang (as seen in Phase 3).
*   **Recommendation:**
    *   Refactor `monitor_build` to accept a `stream` object (iterator) instead of calling subprocess directly.
    *   Test the `stream` parsing logic with mock log lines.

## 2. Transport Layer (Medium Risk)
*   **File:** `transport.py`
*   **Coverage:** 18%
*   **Gap:** `rsync_pull` and `rsync_push` implementations.
*   **Reason:** Tests for `sync.py` mock the `RemoteHost` class methods (`host.rsync_push`), so the actual implementation in `transport.py` is never executed during tests.
*   **Impact:** Real `rsync` command construction errors (e.g. argument order, path escaping) won't be caught.
*   **Recommendation:** Add a specific test for `transport.py` that mocks `subprocess.run` (not the method itself) to verify the constructed command arguments.

## 3. Run Command (Medium Risk)
*   **File:** `run.py`
*   **Coverage:** 15%
*   **Gap:** `do_run` function.
*   **Reason:** There seem to be no integration tests invoking `projector run`.
*   **Recommendation:** Add a simple test case in `tests/test_projector_features.py` that invokes `do_run` with a mock host.

## 4. Configuration Utilities (Low Risk)
*   **File:** `config.py`
*   **Coverage:** 15%
*   **Gap:** `load_config` (recursive search), `update_gitignore`, `enforce_cursorrules`.
*   **Reason:** Tests set up the environment in CWD, so the "directory walking" logic is unused. Maintainability logic like `gitignore` is not essential for core logic tests.
*   **Recommendation:** Safe to ignore for now, or add a dedicated `test_config_utils.py`.
