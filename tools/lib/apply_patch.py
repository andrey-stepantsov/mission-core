import sys
import os

def apply_patch(input_content):
    lines = input_content.splitlines(keepends=True)

    # 1. Validation and Header Parsing
    if not lines:
        print("Error: Empty input provided.", file=sys.stderr)
        return False

    target_file = lines[0].strip()
    if not target_file:
        print("Error: First line (filename) is empty.", file=sys.stderr)
        return False

    # 2. Locate Markers
    try:
        search_idx = -1
        divider_idx = -1
        replace_idx = -1

        for i, line in enumerate(lines):
            clean_line = line.strip()
            if clean_line == "<<<<<<< SEARCH":
                search_idx = i
            elif clean_line == "=======":
                divider_idx = i
            elif clean_line == ">>>>>>> REPLACE":
                replace_idx = i
                break

        if search_idx == -1 or divider_idx == -1 or replace_idx == -1:
            print(f"Error: Malformed patch for '{target_file}'. Missing standard markers.", file=sys.stderr)
            return False
            
        # Verify marker order
        if not (search_idx < divider_idx < replace_idx):
            print("Error: Markers are out of order.", file=sys.stderr)
            return False

        # 3. Extract Blocks
        # We assume the content *between* markers is the payload
        search_block = "".join(lines[search_idx + 1 : divider_idx])
        replace_block = "".join(lines[divider_idx + 1 : replace_idx])

    except Exception as e:
        print(f"Error parsing patch structure: {e}", file=sys.stderr)
        return False

    # 4. Apply to File
    if not os.path.exists(target_file):
        print(f"Error: Target file '{target_file}' does not exist.", file=sys.stderr)
        return False

    try:
        with open(target_file, 'r', encoding='utf-8') as f:
            content = f.read()

        if search_block not in content:
            print(f"Error: SEARCH block not found in '{target_file}'.", file=sys.stderr)
            return False

        if content.count(search_block) > 1:
            print(f"Warning: Multiple occurrences found in '{target_file}'. Patching first occurrence only.", file=sys.stderr)

        new_content = content.replace(search_block, replace_block, 1)

        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        print(f"✅ Success: Patched '{target_file}'")
        return True

    except Exception as e:
        print(f"Error writing to file: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    # Read all input from stdin (allows piping)
    input_data = sys.stdin.read()
    if not input_data:
        print("Usage: cat patch.txt | tools/bin/apply_patch")
        sys.exit(1)
    
    success = apply_patch(input_data)
    if not success:
        sys.exit(1)
