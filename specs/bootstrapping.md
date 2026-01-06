# Toolchain Bootstrapping Architecture

## Goal

Tools must self-manage their dependencies. Users should not need to manually `pip install` anything.

## The Architecture

### Entry Point (`bin/<tool>`)

A lightweight Bash wrapper. It establishes the location of the library and calls the bootstrapper.

### Bootstrapper (`lib/bootstrap.sh`)

1.  Calculates a unique venv path (e.g., `~/.cache/mission-packs/<hash>`).
2.  Checks if the venv exists. If not, creates it and installs `requirements.txt`.
3.  Executes the target Python script using the venv's Python.

### The Logic (`lib/<tool>.py`)

The actual Python code. It can now freely import standard libraries (like `PyYAML`).

## Requirement

Refactor the existing `weave` tool to match this structure.
