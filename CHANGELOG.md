# Changelog

All notable changes to this project will be documented in this file.

## [2.9.4] - 2026-01-22

### Added
- **Test Suite Stabilization**: Added `mock_agent.py` to simulate Director/LocalSmith behavior for robust testing in credential-restricted environments (like `devbox`).
- **Integration Test Handling**: Explicitly identified and skipped integration tests requiring external credentials (`test_integration_chat.py`, `test_scenario_config_flow.py`) to prevent false negatives in CI/local runs.
- **Python 3.8 Compatibility**: downgrades and verification to ensuring simulation host compatibility.
- **Unit Tests**: Added comprehensive unit tests for `monitor.py` (log parsing), `transport.py` (remote command construction), and `projector focus` (analysis command).

### Changed
- **Monitor Logic**: Refactored `monitor.py` to extract log parsing into a pure, testable function `parse_log_line`.
- **Infrastructure**: Hardened `devbox` environment configuration to support isolated testing.
- **Bootstrapping**: Improved resilience of `bootstrap.sh` and `dd-daemon.py` against race conditions and read-only mounts in simulation.

### Fixed
- Resolved import errors in `test_header_resolution.py` caused by incorrect binary shim usage.
- Fixed nested `devbox` calls in `test_devbox_integration.py`.
