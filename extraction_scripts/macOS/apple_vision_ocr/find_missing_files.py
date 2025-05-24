#!/usr/bin/env python3
"""
Find files that exist in source directory but not in output directory.
Compares based on relative paths and expected .md extension for PDFs.
"""

import os
import sys
from pathlib import Path

def find_missing_files(source_dir, output_dir):
    """Find files in source_dir that don't have corresponding files in output_dir."""
    source_path = Path(source_dir).expanduser().resolve()
    output_path = Path(output_dir).expanduser().resolve()
    
    if not source_path.exists():
        print(f"Error: Source directory does not exist: {source_path}")
        sys.exit(1)
    
    if not output_path.exists():
        print(f"Error: Output directory does not exist: {output_path}")
        sys.exit(1)
    
    missing_files = []
    total_source_files = 0
    
    # Walk through source directory
    for root, dirs, files in os.walk(source_path):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            # Skip hidden files
            if file.startswith('.'):
                continue
            
            # Only check PDF and MD files
            if not (file.lower().endswith('.pdf') or file.lower().endswith('.md')):
                continue
            
            total_source_files += 1
            
            # Get relative path from source root
            source_file = Path(root) / file
            rel_path = source_file.relative_to(source_path)
            
            # Determine expected output path
            if file.lower().endswith('.pdf'):
                # PDFs should be converted to .md
                expected_name = rel_path.with_suffix('.md')
            else:
                # MD files should be copied as-is
                expected_name = rel_path
            
            expected_output = output_path / expected_name
            
            # Check if output file exists
            if not expected_output.exists():
                missing_files.append({
                    'source': str(source_file),
                    'expected_output': str(expected_output),
                    'relative_path': str(rel_path),
                    'type': 'PDF' if file.lower().endswith('.pdf') else 'MD'
                })
    
    # Print results
    print(f"\n=== Missing Files Report ===")
    print(f"Source directory: {source_path}")
    print(f"Output directory: {output_path}")
    print(f"Total source files (PDF/MD): {total_source_files}")
    print(f"Missing in output: {len(missing_files)}")
    
    if missing_files:
        print(f"\nMissing files:")
        print("-" * 80)
        
        # Group by type
        pdf_missing = [f for f in missing_files if f['type'] == 'PDF']
        md_missing = [f for f in missing_files if f['type'] == 'MD']
        
        if pdf_missing:
            print(f"\nMissing PDFs ({len(pdf_missing)}):")
            for file in pdf_missing:
                print(f"  {file['relative_path']}")
                print(f"    Source: {file['source']}")
                print(f"    Expected: {file['expected_output']}")
                print()
        
        if md_missing:
            print(f"\nMissing MDs ({len(md_missing)}):")
            for file in md_missing:
                print(f"  {file['relative_path']}")
                print(f"    Source: {file['source']}")
                print(f"    Expected: {file['expected_output']}")
                print()
        
        # Save to file for easy processing
        output_file = "missing_files.txt"
        with open(output_file, 'w') as f:
            f.write("# Missing files list\n")
            f.write(f"# Source: {source_path}\n")
            f.write(f"# Output: {output_path}\n\n")
            for file in missing_files:
                f.write(f"{file['source']}\n")
        
        print(f"\nMissing file paths saved to: {output_file}")
    else:
        print("\n✅ All files have been processed successfully!")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python find_missing_files.py <source_dir> <output_dir>")
        print("Example: python find_missing_files.py ~/Documents/Health\\ Basics/Knowledgebase/Experts ./experts_md")
        sys.exit(1)
    
    source_dir = sys.argv[1]
    output_dir = sys.argv[2]
    
    find_missing_files(source_dir, output_dir)