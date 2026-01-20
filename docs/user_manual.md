# Mission User Manual

## Remote Brain Workflow

The **Remote Brain** architecture allows you to work on local code ("Hologram") while synchronizing and building on a remote host ("Oracle").

### Environment Choice: Devbox vs. Container

You can run the client-side tools (`projector`) in two environments. Choose the one that fits your current task.

| Feature | **Devbox (Local Shell)** | **Container (The Matrix)** |
| :--- | :--- | :--- |
| **Role** | **Production Client**. This represents *You* working on your laptop. | **Simulation Lab**. This represents a generated "Client" machine inside a controlled testbed. |
| **Isolation** | **Process-level**. Tools are isolated via Nix, but you share your OS, network, and SSH keys. | **OS-level**. Completely separate filesystem, network, and users (`neo`). |
| **Networking** | "Remote" hosts are real servers (e.g., `remote-host`). Simulating a host locally requires port mapping. | Perfect DNS simulation. You can `ssh oracle@mission-host` just like a real server. |
| **Setup** | Fast. `devbox shell` and you're ready. | Slower. Requires `docker compose up`, then attaching your IDE. |
| **Persistence** | Permanent. Your changes are on your disk. | Ephemeral. If you delete the container, non-mounted data is gone. |
| **Best For...** | **Daily Driving**. Connecting to real physical hosts (`remote-host`). | **Training / Testing**. Verifying the agent knows how to use the tools. |

### Scenario Recommendation

**1. "I want to verify Antigravity can use the tools."**
> **Choose: Container (`mission-client`)**
> *   **Why:** It forces the agent to use the *exact* environment defined in the project, ensuring `setup_hologram` and `projector` work cleanly from scratch. It prevents "it works on my machine" issues.

**2. "I want to fix a bug on `remote-host`."**
> **Choose: Devbox**
> *   **Why:** You don't want the friction of Docker. You just want the tools (`projector`, `rsync`) installed in a clean shell so you can connect to the real server and work.

### How to Switch

*   **To use Devbox:**
    ```bash
    # In your local terminal (not inside docker)
    devbox shell
    # Now you have access to 'projector', 'python', etc.
    projector init <user>@<remote-host> --remote-root /path/to/repo
    ```

*   **To use Containers:**
    1.  Start the simulation: `cd .mission/tools/simulation && docker compose up -d`
    2.  Attach your IDE (VS Code) to the `mission-client` container.
    3.  Run commands as the `neo` user inside the container.
