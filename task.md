# Task: Consolidate Remote Brain Provisioning

- [x] Analyze `setup_realistic_host.sh` and `provision_remote` <!-- id: 0 -->
- [x] Create `implementation_plan.md` <!-- id: 1 -->
- [x] Refactor `provision_remote` <!-- id: 2 -->
    - [x] Install `bear` and dependencies <!-- id: 3 -->
    - [x] Setup `dd-daemon` environment <!-- id: 4 -->
    - [x] Deploy and configure `auto_ghost` (updated with --full) <!-- id: 5 -->
    - [x] Refactor for non-root envs (remove sudo, check tools) <!-- id: 11 -->
    - [x] Unify bootstrap strategy (use bootstrap.sh wrapper) <!-- id: 12 -->
- [x] Update `launch_tower` to use bootstrap wrapper <!-- id: 13 -->
- [x] Verify `provision_remote` functionality <!-- id: 6 -->
    - [x] Run verification in simulation <!-- id: 7 -->
- [x] Capture `walkthrough.md` <!-- id: 8 -->
- [x] Commit and Tag `remote-brain-v1` <!-- id: 9 -->
- [ ] Run Regression `tests/run_suite.sh` <!-- id: 10 -->
