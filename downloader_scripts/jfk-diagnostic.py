#!/usr/bin/env python3
"""
JFK File Diagnostic Tool
-----------------------
This script analyzes the Excel file and the downloaded files to identify any issues.
It will:
1. Check for duplicate filenames in the Excel file
2. Verify each file has been properly downloaded
3. Report exactly which files are missing

Usage:
    python jfk_diagnostic.py [excel_file.xlsx] [release_year]
"""

import os
import sys
import pandas as pd
from collections import Counter
import argparse

# Configuration
DOWNLOAD_DIR = os.path.expanduser("~/Downloads/JFK_Files")

def check_excel_for_duplicates(excel_path, release_year):
    """Check the Excel file for duplicate filenames."""
    print(f"\n{'-'*20} Checking Excel for Duplicates {'-'*20}")
    
    # Determine the URL column based on the filename
    if '2021' in excel_path.lower():
        url_column = 'File Title'
    else:
        url_column = 'File Name'
    
    # Read the Excel file
    try:
        df = pd.read_excel(excel_path)
        
        # Verify the URL column exists
        if url_column not in df.columns:
            print(f"Error: Column '{url_column}' not found in {excel_path}")
            print(f"Available columns: {', '.join(df.columns)}")
            return None
        
        # Filter out rows without valid PDF URLs
        df = df[df[url_column].notna() & df[url_column].astype(str).str.contains('.pdf', case=False)]
        
        # Extract just the filename part
        df['filename'] = df[url_column].apply(lambda x: os.path.basename(str(x)))
        
        # Check for duplicates
        filename_counts = Counter(df['filename'])
        duplicates = {f: c for f, c in filename_counts.items() if c > 1}
        
        if duplicates:
            print(f"Found {len(duplicates)} duplicate filenames in the Excel file:")
            for filename, count in duplicates.items():
                print(f"  - {filename}: appears {count} times")
                # Show the full paths for the duplicates
                dupes = df[df['filename'] == filename]
                for idx, row in dupes.iterrows():
                    print(f"      Full path: {row[url_column]}")
        else:
            print("No duplicate filenames found in the Excel file.")
        
        total_files = len(df)
        unique_files = len(set(df['filename']))
        duplicate_count = total_files - unique_files
        
        print(f"Total files in Excel: {total_files}")
        print(f"Unique filenames: {unique_files}")
        print(f"Duplicate filenames: {duplicate_count}")
        
        return df
        
    except Exception as e:
        print(f"Error reading Excel file {excel_path}: {e}")
        return None

def verify_downloads(df, release_year):
    """Verify that all files were properly downloaded."""
    print(f"\n{'-'*20} Verifying Downloaded Files {'-'*20}")
    
    if df is None:
        print("Cannot verify downloads: Excel file analysis failed.")
        return
    
    release_dir = os.path.join(DOWNLOAD_DIR, f"release-{release_year}")
    
    if not os.path.exists(release_dir):
        print(f"Error: Download directory {release_dir} does not exist.")
        return
    
    # Get list of downloaded files
    downloaded_files = set(f for f in os.listdir(release_dir) if f.endswith('.pdf'))
    
    # Get list of expected files
    expected_files = set(df['filename'])
    
    # Find missing files
    missing_files = expected_files - downloaded_files
    
    # Find extra files
    extra_files = downloaded_files - expected_files
    
    # Report
    print(f"Total files expected: {len(expected_files)}")
    print(f"Total files downloaded: {len(downloaded_files)}")
    
    if missing_files:
        print(f"\nFound {len(missing_files)} missing files:")
        for i, filename in enumerate(sorted(missing_files), 1):
            # Find the original path for this file
            original_paths = df[df['filename'] == filename][df.columns[0]].tolist()
            print(f"  {i}. {filename} (Original path: {original_paths[0]})")
        
        # Save missing files to a text file
        missing_log = os.path.join(release_dir, f"missing_files_{release_year}.txt")
        with open(missing_log, 'w') as f:
            for filename in sorted(missing_files):
                original_paths = df[df['filename'] == filename][df.columns[0]].tolist()
                f.write(f"{filename} (Original path: {original_paths[0]})\n")
        print(f"\nList of missing files saved to: {missing_log}")
    else:
        print("\nNo missing files found!")
    
    if extra_files:
        print(f"\nFound {len(extra_files)} unexpected files:")
        for i, filename in enumerate(sorted(extra_files), 1):
            print(f"  {i}. {filename}")
    else:
        print("\nNo unexpected files found.")
    
    # Check for zero-byte files
    zero_byte_files = []
    for filename in downloaded_files:
        filepath = os.path.join(release_dir, filename)
        if os.path.getsize(filepath) == 0:
            zero_byte_files.append(filename)
    
    if zero_byte_files:
        print(f"\nFound {len(zero_byte_files)} zero-byte files:")
        for i, filename in enumerate(sorted(zero_byte_files), 1):
            print(f"  {i}. {filename}")
        
        # Save zero-byte files to a text file
        zero_log = os.path.join(release_dir, f"zero_byte_files_{release_year}.txt")
        with open(zero_log, 'w') as f:
            for filename in sorted(zero_byte_files):
                f.write(f"{filename}\n")
        print(f"\nList of zero-byte files saved to: {zero_log}")
    else:
        print("\nNo zero-byte files found.")

def main():
    parser = argparse.ArgumentParser(description='Diagnose issues with JFK file downloads')
    parser.add_argument('excel_file', nargs='?', help='Path to the Excel file containing PDF links')
    parser.add_argument('release_year', nargs='?', help='Release year (e.g., 2023, 2022, 2021, 2017-2018)')
    
    args = parser.parse_args()
    
    # If excel_file or release_year is not provided, prompt for them
    excel_file = args.excel_file
    if not excel_file:
        excel_file = input("Enter the path to the Excel file: ")
    
    release_year = args.release_year
    if not release_year:
        release_year = input("Enter the release year (e.g., 2023, 2022, 2021, 2017-2018): ")
    
    # Validate inputs
    if not os.path.exists(excel_file):
        print(f"Error: Excel file '{excel_file}' not found")
        return
    
    # Run diagnostics
    df = check_excel_for_duplicates(excel_file, release_year)
    verify_downloads(df, release_year)
    
    print("\nDiagnostic completed!")

if __name__ == "__main__":
    main()
