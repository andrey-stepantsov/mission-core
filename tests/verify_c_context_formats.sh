#!/bin/bash
set -e

# Setup a dummy compile_commands.json with both formats
cat > compile_commands.json <<EOF
[
  {
    "directory": "/tmp",
    "command": "gcc -DCOMMAND_STYLE -I/tmp/include -c file1.c -o file1.o",
    "file": "/tmp/file1.c"
  },
  {
    "arguments": [
      "gcc",
      "-DARGUMENT_STYLE",
      "-I/tmp/include",
      "-c",
      "-o",
      "file2.o",
      "file2.c"
    ],
    "directory": "/tmp",
    "file": "/tmp/file2.c"
  }
]
EOF

# Create dummy files
touch /tmp/file1.c /tmp/file2.c
mkdir -p /tmp/include

echo "Testing Command Style..."
OUTPUT1=$(python3 .mission/tools/lib/c_context.py /tmp/file1.c --db compile_commands.json)
if echo "$OUTPUT1" | grep -q "COMMAND_STYLE"; then
    echo "✅ Command Style Supported"
else
    echo "❌ Command Style Failed"
    echo "$OUTPUT1"
    exit 1
fi

echo "Testing Argument Style..."
OUTPUT2=$(python3 .mission/tools/lib/c_context.py /tmp/file2.c --db compile_commands.json)
if echo "$OUTPUT2" | grep -q "ARGUMENT_STYLE"; then
    echo "✅ Argument Style Supported"
else
    echo "❌ Argument Style Failed"
    echo "$OUTPUT2"
    exit 1
fi

echo "✅ Both formats verified."
