# Simulation Environment: The Realistic Factory

## Overview
The "Realistic Factory" is an enhanced simulation profile for "Mission Host" (`mission-sim`) designed to mirror a complex Enterprise legacy environment. Unlike previous iterations that used stubs, this environment supports **real compilation and execution** of C/C++ code, enabling end-to-end verification of the Remote Brain architecture.

## Architecture

### 1. Build System Shim
The remote host runs a vanilla `dd-daemon` which defaults to executing `make`. To bridge this with our generated build script (`./mk`), we plant a `Makefile` in the project root:

```makefile
all:
    @./mk
```

This allows the unmodified daemon to successfully trigger our custom build logic.

### 2. Real Compilation
The `chaos.py` tool has been upgraded to generate `lmk` (Library MaKe) scripts and `mk` (Root MaKe) scripts that utilize `/usr/bin/gcc` and `/usr/bin/g++`.

- **Component Build (`lmk`)**: Compiles individual `.c/.cpp` files into `.o` object files.
- **Root Build (`mk`)**: Links the root application's `.o` files with its library dependencies (e.g., `libs/lib0/lib0.c.o`) to produce a working executable.

### 3. Log Capture
Because actual binaries are executed, `stdout` and `stderr` are captured by the daemon and written to `.ddd/run/build.log`. This log contains real compiler output and application execution results (e.g., "Chaos App Running"), which are then broadcast back to the client via "The Radio".

## Provisioning
To deploy this environment, run:

```bash
./tools/simulation/setup_realistic_host.sh
```

This script:
1.  provisions the directory structure on `mission-sim`.
2.  Deploys `chaos.py`, `launch_tower`, and `dd-daemon`.
3.  Generates the "Project0" codebase with real C++ sources.
4.  Plants the `Makefile` shim.
## Dependency Insight
To enable accurate dependency discovery for "Auto-Ghost", the environment includes:
1.  **Bear**: A tool to generate a compilation database (`compile_commands.json`) from the build process. The `Makefile` usage is wrapped to automatically invoke `bear`.
2.  **Auto-Ghost**: A custom tool that leverages the compilation database to run `gcc -M` on source files, extracting the precise list of header dependencies (both project-local and system-level) to be synced to the client's "Outside Wall".

