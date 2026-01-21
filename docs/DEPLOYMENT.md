# Mission Pack Deployment Guide

## 1. Prerequisites
Before launching the Mission Pack, ensure you have:
*   **Docker Installed**: The entire system runs containerized.
*   **Google Cloud Credentials**:
    *   **Default Path**: `~/.config/gcloud/application_default_credentials.json` (generated via `gcloud auth application-default login`).
    *   **Environment Variable**: Alternatively, set `GOOGLE_APPLICATION_CREDENTIALS=/path/to/creds.json`.
*   **Vertex AI API Enabled**: Ensure the project associated with your credentials has the Vertex AI API enabled.

## 2. Setting Up a New "Ghost" Repository
To deploy the Mission Pack into a new or existing project (The "Workplace"), follow the **Nested Ghost** pattern.

### Step 1: Initialize the Workplace
Create your project directory (if it doesn't exist).
```bash
mkdir my-new-project
cd my-new-project
git init
```

### Step 2: Summons the Mission Pack
Add the Mission Pack as a "Ghost" submodule. It **must** be named `.mission` to act as the hidden engine.
```bash
# Add as a hidden submodule
git submodule add -b main https://github.com/andrey-stepantsov/mission-core.git .mission

# Initialize it
git submodule update --init --recursive
```

### Step 3: Bootstrap the Tools
Run the bootstrap script to ensure the `projector` and other tools are ready.
```bash
# This sets up local environment and linking if necessary
./.mission/tools/bin/setup_hologram ./.mission
```

### Step 4: Connect to Remote (Projector Init)
Configure the connection to your remote "Oracle" (Host).
```bash
# Usage: projector init <ssh_target> --remote-root <remote_path>
./.mission/tools/bin/projector init user@mission-host --remote-root /repos/my-project
```
*   This creates `.hologram_config` and initializes the local `hologram/` directory.

### Step 5: Verify
Pull a file to test the connection.
```bash
./.mission/tools/bin/projector pull README.md
```

## 3. Architecture & Platform Specifics
The system is built on `aider-vertex`, a Nix-based Docker image. The deployment behavior varies by platform to ensure stability.

### 🐧 AMD64 (Linux / Intel Mac / Windows)
*   **Behavior**: Fast Startup.
*   **Mechanism**: The launcher will attempt to pull the pre-built `aider-vertex:latest` image from the container registry.
*   **Extension**: It then builds a lightweight local extension (`mission-core`) containing your project-specific dependencies.

### 🍎 ARM64 (Apple Silicon: M1/M2/M3)
*   **Behavior**: Slower Initial Launch (Bootstrap Phase).
*   **Challenge**: The upstream `aider-vertex` image is `linux/amd64`. Running this directly on Apple Silicon requires QEMU emulation, which is slow and prone to segfaults when running complex tools like `pip`.
*   **Solution (Native Bootstrap)**: 
    *   The launcher (`tools/bin/up`) automatically detects your ARM64 architecture.
    *   If a native image is missing, it initiates a **Nix-in-Docker Build**.
    *   It runs a temporary container (`nixos/nix`) to build `aider-vertex` *from source* for `linux/arm64`.
    *   This results in a **Native Image** that runs at full speed with no emulation stability issues.
*   **Note**: The first run may take 5-10 minutes to compile the base image. Subsequent runs are instant.

## 4. Troubleshooting

**"Base image not found" on x86_64**
*   Run: `docker pull ghcr.io/andrey-stepantsov/aider-vertex:latest`
*   Tag it: `docker tag ghcr.io/andrey-stepantsov/aider-vertex:latest aider-vertex:latest`

**"Segfault" or "Emulation Error" on M1**
*   Ensure you are using the Native Bootstrap path.
*   Delete any existing amd64 images: `docker rmi aider-vertex:latest`
*   Run `./tools/bin/up` again to force a native rebuild.
