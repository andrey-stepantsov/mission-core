# Weave Tool Specification

## Concept

`weave` is a command-line interface (CLI) tool designed to help Aider (and humans) load pre-defined sets of files based on the 'Mental Model' of a given task.

## Specification

### Configuration

- **File**: `weave.yaml` located at the repository root.
- **Keys**: The keys in the YAML file are 'views' (e.g., `networking`, `hardware`, `ci`).
- **Values**: The values are lists of glob patterns that define the files for each view (e.g., `src/net/*.c`).

### CLI Usage

The `weave` tool is invoked via `bin/weave`.

- **`bin/weave list`**
  - **Action**: Shows all available views from `weave.yaml`.

- **`bin/weave get <view>`**
  - **Action**: Prints the resolved list of file paths for the given `<view>`.
  - **Output**: A single, space-separated line of file paths, suitable for passing to other tools.

- **`bin/weave show <view>`**
  - **Action**: Prints a tree-like summary of the files in the `<view>` for human consumption.

## The Agent Protocol

This protocol defines how an AI agent should use `weave`.

1.  When a user mentions a specific domain (e.g., "Fix the SDK"), the Agent should identify the corresponding view.
2.  The Agent must run `bin/weave get <view>` to retrieve the list of files. For example:
    ```bash
    bin/weave get sdk
    ```
3.  The Agent will then read the space-separated output and use the `/add` command to load those files into the context.
