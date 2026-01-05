# Architecture and Build System

This document explains the "Split-Brain" build system used in this monorepo.

## Overview

This is a monorepo, but the build environment and process change depending on which part of the repository you are working in. There are two main zones: the "App Zone" and the "SDK Zone".

## App Zone

- **Location**: `/srl-repo/app1`
- **Code Type**: Standard Linux applications.
- **Build Environment**: Builds inside a Docker container.
- **Build Command (Internal)**: `./rmk`

This zone contains standard Linux code. The build process is containerized for consistency.

## SDK Zone

- **Location**: `/srl-repo/asic/sdk1`
- **Code Type**: Specialized hardware code for the ASIC.
- **Build Environment**: Builds directly on the host machine.
- **Dependency**: Requires access to a license server.
- **Build Command (Internal)**: `./lmk`

This zone contains low-level code that interacts with specific hardware. Due to licensing requirements for the toolchain, it must be built on the host machine, not in a container.

## The Golden Rule: How to Build

**Developers should NEVER run `./rmk` or `./lmk` directly.**

These are low-level build scripts. To handle the complexity of switching between build environments (Docker vs. host), a wrapper tool is provided.

**The correct way to build any code in this repository is to use `ddd-wait`.**

`ddd-wait` will automatically detect which zone you are in and execute the correct build command in the correct environment.

## The Immutable Build Rule

- **The Gap is Intentional**: You will NOT find `Makefiles` or `CMakeLists.txt` in this repo. This is by design.
- **Prohibited**: Do NOT create `Makefiles`, CMake scripts, or bash wrappers.
- **Prohibited**: Do NOT run `gcc`, `g++`, or `make` manually.
- **Mandatory**: You must trust `ddd-wait` to handle the build, even if you don't see how it works.
- **Mandatory**: If you are asked to build `app1` or `sdk1`, your ONLY allowed action is to run `ddd-wait`.

### Examples

To build in the App Zone:
```bash
cd /srl-repo/app1
ddd-wait
```

To build in the SDK Zone:
```bash
cd /srl-repo/asic/sdk1
ddd-wait
```

An AI agent or a developer should always use `ddd-wait` to build code, regardless of the location within the repository.
