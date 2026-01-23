**Next Session Prompt:**

```markdown
Review [implementation_plan.md](cci:7://file:///Users/stepants/dev/chaos/.mission/implementation_plan.md:0:0-0:0)
---
Objective: Implement Phase 3 (Structured Diagnostics)
We have automated the build/verify loop (`projector build --path=... --verify=...`).
Now we need to close the feedback loop by making the *output* actionable for the Agent.

1.  **Analyze**: The `dd-daemon` supports filters (e.g., `gcc_json`), but `projector build` currently just streams the raw text.
2.  **Task**:
    -   Update `projector build` to fail gracefully and (optional) output structured errors if available.
    -   Verify that we can switch `dd-daemon` filters dynamically via `.ddd/config.json`.
    -   Demonstrate an "Autofix" scenario where the Agent parses the JSON error from `projector log` and fixes the code.
```
