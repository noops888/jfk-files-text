#!/usr/bin/env python3
"""
JFK Files Final Working Downloader
--------------------------------
This script downloads JFK files using the exact URL structure and carefully verifies each download.

Usage:
    python jfk_final_working_downloader.py [excel_file] [--threads N] [--test]
"""

import os
import sys
import requests
import pandas as pd
import time
import argparse
import concurrent.futures
from tqdm import tqdm
import re

# Configuration
DOWNLOAD_DIR = os.path.expanduser("~/Downloads/JFK_Files")

def read_excel_file(excel_path):
    """Read the Excel file and return its DataFrame."""
    try:
        print(f"Reading Excel file: {excel_path}")
        
        # Determine URL column based on release year
        if '2021' in excel_path.lower():
            url_column = 'File Title'
        else:
            url_column = 'File Name'
        
        # Read the Excel file
        df = pd.read_excel(excel_path)
        
        # Display available columns for debugging
        print(f"Available columns: {', '.join(df.columns)}")
        
        # Verify the URL column exists
        if url_column not in df.columns:
            print(f"Error: Column '{url_column}' not found in {excel_path}")
            # Try alternative column names
            url_column = next((col for col in df.columns if col.lower() in ['file name', 'filename', 'file title', 'url']), None)
            if not url_column:
                print("Could not find an appropriate column for file names/URLs")
                return None, None
            print(f"Using alternative column: {url_column}")
        
        # Filter out rows without valid PDF URLs
        df = df[df[url_column].notna() & df[url_column].astype(str).str.contains('.pdf', case=False)]
        
        print(f"Found {len(df)} PDF entries in the Excel file")
        
        # Show a sample of entries
        print("\nSample of file entries:")
        for _, row in df.head(5).iterrows():
            print(f"  {row[url_column]}")
            
        return df, url_column
    
    except Exception as e:
        print(f"Error reading Excel file {excel_path}: {e}")
        return None, None

def download_single_file(url, save_path, retries=3):
    """Download a single file and verify it was properly saved."""
    for attempt in range(retries):
        try:
            print(f"Trying: {url}")
            response = requests.get(url, stream=True, timeout=30)
            
            # Check status code
            if response.status_code != 200:
                print(f"Status code: {response.status_code} for {url}")
                if attempt < retries - 1:
                    time.sleep(2)
                    continue
                return False
            
            # Check content type to ensure it's a PDF
            content_type = response.headers.get('Content-Type', '').lower()
            if 'application/pdf' not in content_type and 'pdf' not in content_type:
                print(f"Warning: URL returned non-PDF content type: {content_type}")
                if attempt < retries - 1:
                    time.sleep(2)
                    continue
                return False
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
            
            # Save the file
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Verify file was written and is not empty
            if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                # Double-check it's a PDF by reading the first few bytes
                with open(save_path, 'rb') as f:
                    header = f.read(4)
                    if header == b'%PDF':
                        print(f"SUCCESS - Saved to {save_path}")
                        return True
                    else:
                        print(f"Warning: File is not a valid PDF: {save_path}")
                        os.remove(save_path)
            else:
                print(f"Warning: File was not written or is empty: {save_path}")
                if os.path.exists(save_path):
                    os.remove(save_path)
            
            if attempt < retries - 1:
                time.sleep(2)
                
        except requests.exceptions.RequestException as e:
            print(f"Error: {e} for {url}")
            if attempt < retries - 1:
                time.sleep(2)
            else:
                return False
    
    return False

def download_file(file_path, save_path, retries=3):
    """Download a file using multiple possible URL structures."""
    # First, ensure the file_path is properly formatted
    # Make sure we don't have any Windows backslashes
    file_path = file_path.replace('\\', '/')
    
    # The base URL patterns to try
    base_urls = [
        "https://www.archives.gov/files/research/jfk/releases/",
        "https://www.archives.gov/research/jfk/releases/"
    ]
    
    # For each base URL, try the full URL
    for base_url in base_urls:
        full_url = base_url + file_path
        if download_single_file(full_url, save_path, retries):
            return full_url, True
    
    # If we couldn't download with the exact path, try some common variations
    # Especially for 2017-2018 release where files might be in 2017/ or 2018/
    variations = []
    
    # Extract filename and check if there's a year in the path
    filename = os.path.basename(file_path)
    dir_path = os.path.dirname(file_path)
    
    if '2017' in dir_path:
        # Try 2018 instead of 2017
        variations.append(file_path.replace('2017', '2018'))
    elif '2018' in dir_path:
        # Try 2017 instead of 2018
        variations.append(file_path.replace('2018', '2017'))
    
    # If the path doesn't already include a year directory, try adding it
    if not ('2017' in dir_path or '2018' in dir_path or '2021' in dir_path):
        variations.append('2017/' + filename)
        variations.append('2018/' + filename)
        variations.append('2021/' + filename)
    
    # Try each variation with each base URL
    for variant in variations:
        for base_url in base_urls:
            full_url = base_url + variant
            if download_single_file(full_url, save_path, retries):
                return full_url, True
    
    # If we reach here, all attempts failed
    print(f"ERROR - All download attempts failed for {file_path}")
    return None, False

def download_worker(args):
    """Worker function for parallel downloads."""
    file_path, save_path = args
    url, success = download_file(file_path, save_path)
    return file_path, url, success

def process_downloads(df, url_column, num_threads=4, max_files=None, test_mode=False):
    """Process downloads using various URL structures."""
    release_name = determine_release_name(df, url_column)
    release_dir = os.path.join(DOWNLOAD_DIR, release_name)
    os.makedirs(release_dir, exist_ok=True)
    
    # Limit files if requested (for testing)
    if max_files:
        print(f"Limiting to {max_files} files for testing")
        df = df.head(max_files)
    
    # Prepare download tasks
    download_tasks = []
    skipped_files = []
    
    # Process each file
    for idx, row in df.iterrows():
        file_path = str(row[url_column])
        
        # Keep the directory structure from the Excel file
        rel_path = file_path
        
        # Create the output path
        if '/' in rel_path or '\\' in rel_path:
            # Already has a path structure, preserve it
            save_path = os.path.join(release_dir, rel_path.replace('\\', '/'))
        else:
            # Just a filename, put it directly in the release directory
            save_path = os.path.join(release_dir, rel_path)
        
        # Skip if file already exists and has content
        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
            skipped_files.append(rel_path)
            continue
        
        # In test mode, just download a few files to verify the approach works
        if test_mode and idx >= 10:
            continue
        
        # Add to download tasks
        download_tasks.append((rel_path, save_path))
    
    # Report on files to download
    print(f"Files to download: {len(download_tasks)} of {len(df)} total")
    print(f"Files skipped (already downloaded): {len(skipped_files)}")
    
    if not download_tasks:
        print("No files need to be downloaded")
        return
    
    # Adjust thread count
    if len(download_tasks) < num_threads:
        num_threads = max(1, len(download_tasks))
    
    # Download files in parallel
    successful = 0
    failed = 0
    failed_files = []
    successful_files = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {executor.submit(download_worker, task): task for task in download_tasks}
        
        with tqdm(total=len(download_tasks), desc=f"Downloading {release_name} PDFs") as pbar:
            for future in concurrent.futures.as_completed(futures):
                try:
                    file_path, url, success = future.result()
                    if success:
                        successful += 1
                        successful_files.append((file_path, url))
                        # Print success message but don't overwhelm console
                        if successful % 10 == 0:
                            print(f"Successfully downloaded {successful} files so far")
                    else:
                        failed += 1
                        failed_files.append(file_path)
                except Exception as e:
                    print(f"Error in worker: {e}")
                    failed += 1
                    task = futures[future]
                    failed_files.append(task[0])
                pbar.update(1)
    
    # Report on download results
    print(f"\nDownload summary:")
    print(f"- Total files to process: {len(df)}")
    print(f"- Already downloaded/skipped: {len(skipped_files)}")
    print(f"- Successfully downloaded: {successful}")
    print(f"- Failed downloads: {failed}")
    
    # Write failed downloads to a log file
    if failed_files:
        failed_log = os.path.join(release_dir, f"failed_downloads_{release_name}.txt")
        with open(failed_log, 'w') as f:
            for file_path in failed_files:
                f.write(f"{file_path}\n")
        print(f"Failed downloads logged to: {failed_log}")
    
    # Write successful downloads to a log file
    if successful_files:
        success_log = os.path.join(release_dir, f"successful_downloads_{release_name}.txt")
        with open(success_log, 'w') as f:
            for file_path, url in successful_files:
                f.write(f"{file_path} -> {url}\n")
        print(f"Successful downloads logged to: {success_log}")
    
    # Verify downloads
    verify_downloads(release_dir)

def determine_release_name(df, url_column):
    """Determine the release name based on the file paths in the Excel."""
    # Look at a sample of entries to determine the release
    sample_paths = [str(row[url_column]) for _, row in df.head(10).iterrows()]
    
    if any('2021' in path for path in sample_paths):
        return "release-2021"
    elif any('2017' in path for path in sample_paths) or any('2018' in path for path in sample_paths):
        return "release-2017-2018"
    else:
        # Default name if can't determine
        return "release-jfk"

def verify_downloads(release_dir):
    """Verify the downloaded files."""
    # Count all PDF files recursively
    total_files = 0
    zero_byte_files = []
    for root, _, files in os.walk(release_dir):
        for file in files:
            if file.lower().endswith('.pdf'):
                file_path = os.path.join(root, file)
                total_files += 1
                # Check for zero-byte files
                if os.path.getsize(file_path) == 0:
                    zero_byte_files.append(os.path.relpath(file_path, release_dir))
    
    print(f"\nVerification: {total_files} PDF files exist in the download directory")
    
    if zero_byte_files:
        print(f"Warning: Found {len(zero_byte_files)} zero-byte PDF files")
        zero_log = os.path.join(release_dir, "zero_byte_files.txt")
        with open(zero_log, 'w') as f:
            for file_path in zero_byte_files:
                f.write(f"{file_path}\n")
        print(f"Zero-byte files logged to: {zero_log}")

def main():
    parser = argparse.ArgumentParser(description='Download JFK Files with correct URL structure')
    parser.add_argument('excel_file', nargs='?', help='Path to the Excel file')
    parser.add_argument('--threads', type=int, default=4, help='Number of download threads')
    parser.add_argument('--max-files', type=int, help='Maximum number of files to download')
    parser.add_argument('--test', action='store_true', help='Test mode - download just a few files')
    
    args = parser.parse_args()
    
    # If excel_file is not provided, prompt for it
    excel_file = args.excel_file
    if not excel_file:
        excel_file = input("Enter the path to the Excel file: ")
    
    # Validate inputs
    if not os.path.exists(excel_file):
        print(f"Error: Excel file '{excel_file}' not found")
        return
    
    # Read the Excel file
    result = read_excel_file(excel_file)
    if result is None:
        return
    
    df, url_column = result
    
    # Process the downloads
    process_downloads(df, url_column, args.threads, args.max_files, args.test)
    
    print("\nDownload process completed!")

if __name__ == "__main__":
    main()
