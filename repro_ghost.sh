#!/bin/bash
set -e
# Create a file with a space in the name
touch "tools/bin/space file.txt"

# Run auto_ghost on it (Strategy 1: Target File with explicit scanner mode to avoid C compiler requirements for this dummy file)
# Note: auto_ghost scanner logic calls scan_file.
# We probably need a C file to trigger the full logic, but let's see if we can trigger the scanner.
echo '#include "header with space.h"' > "tools/bin/source with space.c"
touch "tools/bin/header with space.h"

# Run auto_ghost
echo "Running auto_ghost on 'tools/bin/source with space.c'..."
./tools/bin/auto_ghost "tools/bin/source with space.c" --mode scanner
