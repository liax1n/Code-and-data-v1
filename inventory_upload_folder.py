#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Folder structure export tool.
Recursively scan all subfolders and files in the current directory
and export their structure to a TXT file.
"""

import os
from datetime import datetime


# ============ Configuration ============
OUTPUT_FILE = "folder_structure.txt"      # Output filename
INCLUDE_HIDDEN = False                    # Include hidden files/folders (names starting with a dot)
EXCLUDE_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build"}
# =======================================


def should_exclude(name):
    """Determine whether a file or folder should be excluded."""
    if not INCLUDE_HIDDEN and name.startswith("."):
        return True
    return False


def scan_directory(root_path, output_lines):
    """Recursively scan directories and record structure without file contents."""
    try:
        entries = sorted(os.listdir(root_path))
    except PermissionError:
        output_lines.append(f"    [Permission denied for this directory]\n")
        return

    # Filter directory entries
    dirs = []
    files = []
    for entry in entries:
        if should_exclude(entry):
            continue
        full_path = os.path.join(root_path, entry)
        if os.path.isdir(full_path):
            if entry in EXCLUDE_DIRS:
                continue
            dirs.append(entry)
        else:
            files.append(entry)

    # Process files first
    for fname in files:
        fpath = os.path.join(root_path, fname)
        rel_path = os.path.relpath(fpath, start=os.getcwd())
        try:
            size = os.path.getsize(fpath)
        except OSError:
            size = 0

        output_lines.append(f"  📄 {fname}  ({size} bytes, {rel_path})\n")

    if files:
        output_lines.append("\n")

    # Process subdirectories recursively
    for dname in dirs:
        dpath = os.path.join(root_path, dname)
        rel_path = os.path.relpath(dpath, start=os.getcwd())
        output_lines.append(f"📁 {dname}/  ({rel_path})\n")
        output_lines.append("-" * 60 + "\n")
        scan_directory(dpath, output_lines)


def build_tree_structure(root_path, prefix="", is_last=True, output_lines=None):
    """Generate a directory tree in a README-style layout."""
    if output_lines is None:
        output_lines = []

    try:
        entries = sorted(os.listdir(root_path))
    except PermissionError:
        return output_lines

    entries = [e for e in entries if not should_exclude(e)]
    entries = [e for e in entries
               if not (os.path.isdir(os.path.join(root_path, e)) and e in EXCLUDE_DIRS)]

    for i, entry in enumerate(entries):
        full_path = os.path.join(root_path, entry)
        is_last_entry = (i == len(entries) - 1)
        connector = "└── " if is_last_entry else "├── "

        if os.path.isdir(full_path):
            output_lines.append(f"{prefix}{connector}{entry}/\n")
            extension = "    " if is_last_entry else "│   "
            build_tree_structure(full_path, prefix + extension, is_last_entry, output_lines)
        else:
            try:
                size = os.path.getsize(full_path)
                size_str = f" ({size} B)"
            except OSError:
                size_str = ""
            output_lines.append(f"{prefix}{connector}{entry}{size_str}\n")

    return output_lines


def main():
    root = os.getcwd()
    print(f"Scanning directory: {root}")

    lines = []
    # ========== Report header ==========
    lines.append("=" * 70 + "\n")
    lines.append("Folder Structure Export Report\n")
    lines.append("=" * 70 + "\n")
    lines.append(f"Root directory       : {root}\n")
    lines.append(f"Generated at         : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append(f"Include hidden items : {INCLUDE_HIDDEN}\n")
    lines.append("=" * 70 + "\n\n")

    # ========== Directory tree ==========
    lines.append("[Directory Tree]\n")
    lines.append("-" * 70 + "\n")
    lines.append(f"{os.path.basename(root)}/\n")
    tree_lines = build_tree_structure(root)
    lines.extend(tree_lines)
    lines.append("\n" + "=" * 70 + "\n\n")

    # ========== Detailed structure (paths and sizes only) ==========
    lines.append("[Detailed File Structure]\n")
    lines.append("-" * 70 + "\n\n")
    scan_directory(root, lines)

    # ========== Write output file ==========
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"✅ Export complete: {os.path.join(root, OUTPUT_FILE)}")
    print(f"   Generated {len(lines)} lines")


if __name__ == "__main__":
    main()