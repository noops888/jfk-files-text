#!/usr/bin/env python3
"""
Check for files above a certain size threshold in a directory tree.
"""

import os
import sys
from pathlib import Path

def format_size(bytes):
    """Convert bytes to human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} TB"

def check_file_sizes(directory, threshold_mb=3.9):
    """Find all files >= threshold size in directory tree."""
    dir_path = Path(directory).resolve()
    
    if not dir_path.exists():
        print(f"Error: Directory does not exist: {dir_path}")
        sys.exit(1)
    
    threshold_bytes = threshold_mb * 1024 * 1024
    large_files = []
    all_files = []
    
    # Walk through directory
    for root, dirs, files in os.walk(dir_path):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            # Skip hidden files
            if file.startswith('.'):
                continue
            
            file_path = Path(root) / file
            try:
                size = file_path.stat().st_size
                all_files.append((file_path, size))
                
                if size >= threshold_bytes:
                    large_files.append((file_path, size))
            except Exception as e:
                print(f"Error checking {file_path}: {e}")
    
    # Sort by size (largest first)
    large_files.sort(key=lambda x: x[1], reverse=True)
    all_files.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\n=== File Size Report ===")
    print(f"Directory: {dir_path}")
    print(f"Threshold: {threshold_mb} MB ({format_size(threshold_bytes)})")
    print(f"Total files checked: {len(all_files)}")
    
    if large_files:
        print(f"\nFiles >= {threshold_mb} MB: {len(large_files)}")
        print("-" * 80)
        for file_path, size in large_files:
            rel_path = file_path.relative_to(dir_path)
            print(f"{format_size(size):>10}  {rel_path}")
    else:
        print(f"\n✅ No files found >= {threshold_mb} MB")
    
    # Show largest files even if under threshold
    print(f"\nTop 10 largest files:")
    print("-" * 80)
    for file_path, size in all_files[:10]:
        rel_path = file_path.relative_to(dir_path)
        percentage = (size / threshold_bytes) * 100
        print(f"{format_size(size):>10} ({percentage:>5.1f}% of threshold)  {rel_path}")

if __name__ == "__main__":
    # Default values
    directory = "./experts_md"
    threshold = 3.9
    
    # Parse arguments
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    if len(sys.argv) > 2:
        threshold = float(sys.argv[2])
    
    print(f"Checking for files >= {threshold} MB in: {directory}")
    check_file_sizes(directory, threshold)