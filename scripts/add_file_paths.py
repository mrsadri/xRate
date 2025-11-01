#!/usr/bin/env python3
"""
Script to add file path comments to the first line of all Python files.
"""

import os
from pathlib import Path

def add_file_path_comment(file_path: Path, root: Path):
    """Add file path comment to the first line if not present."""
    relative_path = file_path.relative_to(root)
    comment = f"# {relative_path}"
    
    # Read file content
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return
    
    # Check if comment already exists
    lines = content.splitlines()
    if lines and lines[0] == comment:
        return  # Already has the comment
    
    # Add comment at the beginning
    if lines:
        # If first line is a docstring start, add comment before it
        if lines[0].strip().startswith('"""'):
            new_content = comment + "\n" + content
        elif lines[0].startswith("#"):
            # Replace existing comment
            new_content = comment + "\n" + "\n".join(lines[1:])
        else:
            new_content = comment + "\n" + content
    else:
        new_content = comment + "\n" + content
    
    # Write back
    try:
        file_path.write_text(new_content, encoding="utf-8")
        print(f"✅ Added path comment to: {relative_path}")
    except Exception as e:
        print(f"Error writing {file_path}: {e}")

def main():
    """Process all Python files."""
    root = Path(__file__).parent.parent
    
    # Process src/xrate files
    src_dir = root / "src" / "xrate"
    for py_file in src_dir.rglob("*.py"):
        add_file_path_comment(py_file, root)
    
    # Process test files
    tests_dir = root / "tests"
    if tests_dir.exists():
        for py_file in tests_dir.rglob("*.py"):
            add_file_path_comment(py_file, root)
    
    print("\n✅ All file path comments added!")

if __name__ == "__main__":
    main()

