#!/usr/bin/env python3
"""
Fixed JFK 2021 Files Downloader
------------------------------
This script downloads JFK files from the 2021 release with improved verification and error handling.
It properly handles duplicate entries and case sensitivity issues.

Usage:
    python jfk_2021_fixed_downloader.py [excel_file]
    
Examples:
    python jfk_2021_fixed_downloader.py national-archives-jfk-assassination-records-2021-release.xlsx
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
from collections import Counter

# Configuration
BASE_URL = "https://www.archives.gov/files/research/jfk/releases/2021/"
DOWNLOAD_DIR = os.path.expanduser("~/Downloads/JFK_Files")

def read_excel_file(excel_path):
    """Read the 2021 Excel file and return its DataFrame."""
    try:
        print(f"Reading Excel file: {excel_path}")
        
        # For 2021 release, the URL column is 'File Title'
        url_column = 'File Title'
        
        # Read the Excel file
        df = pd.read_excel(excel_path)
        
        # Verify the URL column exists
        if url_column not in df.columns:
            print(f"Error: Column '{url_column}' not found in {excel_path}")
            print(f"Available columns: {', '.join(df.columns)}")
            return None
        
        # Filter out rows without valid PDF URLs
        df = df[df[url_column].notna() & df[url_column].astype(str).str.contains('.pdf', case=False)]
        
        # Check for duplicates
        filenames = [os.path.basename(str(row[url_column])) for _, row in df.iterrows()]
        filename_counts = Counter(filenames)
        duplicates = {f: c for f, c in filename_counts.items() if c > 1}
        
        if duplicates:
            print(f"Found {len(duplicates)} duplicate filenames in the Excel file:")
            for filename, count in duplicates.items():
                print(f"  - {filename}: appears {count} times")
        
        print(f"Found {len(df)} PDF entries in the Excel file ({len(set(filenames))} unique filenames)")
        return df
    
    except Exception as e:
        print(f"Error reading Excel file {excel_path}: {e}")
        return None

def extract_record_id(filename):
    """Extract the record ID from the filename."""
    # Try to find the record ID in the format DOCID-XXXXXXXX or just XXXXXXXX
    match = re.search(r'(?:DOCID-)?(\d+-\d+-\d+|\d+)', filename, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

def download_file(record_id, save_path, retries=3):
    """Download a file using the known URL structure for 2021 files."""
    # Try both lowercase and uppercase variants
    urls = [
        f"{BASE_URL}docid-{record_id}.pdf",
        f"{BASE_URL}DOCID-{record_id}.pdf"
    ]
    
    for url in urls:
        for attempt in range(retries):
            try:
                response = requests.get(url, stream=True, timeout=30)
                
                # Check the actual status code
                if response.status_code != 200:
                    if attempt < retries - 1:
                        print(f"Retry {attempt+1}/{retries} for {url} after status code: {response.status_code}")
                        time.sleep(2)
                        continue
                    else:
                        # Try the next URL
                        break
                
                # If we got a response, check content type to ensure it's a PDF
                content_type = response.headers.get('Content-Type', '')
                if 'application/pdf' not in content_type.lower():
                    print(f"Warning: URL {url} returned non-PDF content type: {content_type}")
                    if attempt < retries - 1:
                        time.sleep(2)
                        continue
                    else:
                        # Try the next URL
                        break
                
                # Check content length - skip if it's too small to be a valid PDF
                content_length = int(response.headers.get('Content-Length', 0))
                if content_length < 1000:  # Less than 1KB is likely not a valid PDF
                    print(f"Warning: URL {url} returned a very small file ({content_length} bytes)")
                    if attempt < retries - 1:
                        time.sleep(2)
                        continue
                    else:
                        # Try the next URL
                        break
                
                # Download the file
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # Verify file was written and is not empty
                if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                    # Double-check that the file is a PDF by reading the first few bytes
                    with open(save_path, 'rb') as f:
                        magic = f.read(4)
                        if magic == b'%PDF':
                            return url, True
                        else:
                            print(f"Warning: Downloaded file is not a valid PDF: {save_path}")
                            os.remove(save_path)
                            # Try next URL
                            break
                else:
                    # If the file is empty, try the next URL
                    if os.path.exists(save_path):
                        os.remove(save_path)
                    break
                
            except requests.exceptions.RequestException as e:
                if attempt < retries - 1:
                    print(f"Retry {attempt+1}/{retries} for {url} after error: {e}")
                    time.sleep(2)
                else:
                    # Try the next URL
                    break
    
    return urls[0], False

def download_worker(args):
    """Worker function for parallel downloads."""
    filename, record_id, save_path = args
    url, success = download_file(record_id, save_path)
    return filename, record_id, url, success

def process_downloads(df, num_threads=4):
    """Process downloads for the 2021 release."""
    # Create release directory
    release_dir = os.path.join(DOWNLOAD_DIR, "release-2021")
    os.makedirs(release_dir, exist_ok=True)
    
    # Prepare download tasks
    download_tasks = []
    skipped_files = []
    no_record_files = []
    
    # Normalize filenames to all lowercase for case-insensitive comparison
    existing_files = {f.lower(): f for f in os.listdir(release_dir) if f.lower().endswith('.pdf')}
    
    # Get a list of unique filenames from the Excel file
    processed_filenames = set()
    
    for idx, row in df.iterrows():
        pdf_path = str(row['File Title'])
        filename = os.path.basename(pdf_path)
        
        # Check if we've already processed this filename (handle duplicates)
        if filename.lower() in processed_filenames:
            skipped_files.append(f"{filename} (duplicate in Excel)")
            continue
        
        processed_filenames.add(filename.lower())
        
        # Normalize save path
        # Always use the case as it appears in the Excel file
        save_path = os.path.join(release_dir, filename)
        
        # Skip if file already exists and has content
        if filename.lower() in existing_files:
            actual_file = existing_files[filename.lower()]
            actual_path = os.path.join(release_dir, actual_file)
            if os.path.getsize(actual_path) > 0:
                skipped_files.append(filename)
                continue
        
        # Extract record ID
        record_id = extract_record_id(filename)
        
        if record_id:
            download_tasks.append((filename, record_id, save_path))
        else:
            print(f"Warning: Could not extract record ID from filename: {filename}")
            no_record_files.append(filename)
    
    # Report on files to download
    print(f"Files to download: {len(download_tasks)} of {len(df)} total")
    print(f"Files skipped (already downloaded): {len(skipped_files)}")
    print(f"Files with no extractable record ID: {len(no_record_files)}")
    
    if not download_tasks:
        print("No files need to be downloaded")
        return
    
    # Adjust thread count for very small jobs
    if len(download_tasks) < num_threads:
        num_threads = max(1, len(download_tasks))
    
    # Download files in parallel
    successful = 0
    failed = 0
    failed_files = []
    successful_files = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {executor.submit(download_worker, task): task for task in download_tasks}
        
        with tqdm(total=len(download_tasks), desc="Downloading 2021 PDFs") as pbar:
            for future in concurrent.futures.as_completed(futures):
                try:
                    filename, record_id, url, success = future.result()
                    if success:
                        successful += 1
                        successful_files.append((filename, url))
                    else:
                        failed += 1
                        failed_files.append((filename, record_id))
                except Exception as e:
                    print(f"Error in worker: {e}")
                    failed += 1
                    task = futures[future]
                    failed_files.append((task[0], task[1]))
                pbar.update(1)
    
    # Report on download results
    print(f"\nDownload summary:")
    print(f"- Total files to process: {len(df)} ({len(processed_filenames)} unique filenames)")
    print(f"- Already downloaded/skipped: {len(skipped_files)}")
    print(f"- Successfully downloaded: {successful}")
    print(f"- Failed downloads: {failed}")
    
    # Write failed downloads to a log file
    if failed_files:
        failed_log = os.path.join(release_dir, "failed_downloads_2021.txt")
        with open(failed_log, 'w') as f:
            for filename, record_id in failed_files:
                f.write(f"{filename} (ID: {record_id})\n")
        print(f"Failed downloads logged to: {failed_log}")
    
    # Write successful downloads to a log file
    if successful_files:
        success_log = os.path.join(release_dir, "successful_downloads_2021.txt")
        with open(success_log, 'w') as f:
            for filename, url in successful_files:
                f.write(f"{filename} -> {url}\n")
        print(f"Successful downloads logged to: {success_log}")
    
    # Final verification
    verify_downloads(release_dir, processed_filenames)

def verify_downloads(release_dir, expected_filenames):
    """Verify downloaded files against expected filenames."""
    print("\nPerforming download verification...")
    
    # Get actual files in the directory
    actual_files = {f.lower(): f for f in os.listdir(release_dir) if f.lower().endswith('.pdf')}
    
    # Convert expected filenames to lowercase for comparison
    expected_lowercase = {f.lower() for f in expected_filenames}
    
    # Find missing files
    missing_files = expected_lowercase - set(actual_files.keys())
    
    # Find unexpected files
    unexpected_files = set(actual_files.keys()) - expected_lowercase
    
    # Check for zero-byte files
    zero_byte_files = []
    for filename in actual_files.values():
        filepath = os.path.join(release_dir, filename)
        if os.path.getsize(filepath) == 0:
            zero_byte_files.append(filename)
    
    # Report results
    print(f"Expected files: {len(expected_filenames)}")
    print(f"Actual files in directory: {len(actual_files)}")
    
    if missing_files:
        print(f"Missing files: {len(missing_files)}")
        missing_log = os.path.join(release_dir, "verification_missing_2021.txt")
        with open(missing_log, 'w') as f:
            for filename in missing_files:
                f.write(f"{filename}\n")
        print(f"Missing files logged to: {missing_log}")
    else:
        print("No missing files!")
    
    if unexpected_files:
        print(f"Unexpected files: {len(unexpected_files)}")
        unexpected_log = os.path.join(release_dir, "verification_unexpected_2021.txt")
        with open(unexpected_log, 'w') as f:
            for filename in unexpected_files:
                f.write(f"{actual_files[filename]}\n")
        print(f"Unexpected files logged to: {unexpected_log}")
    else:
        print("No unexpected files!")
    
    if zero_byte_files:
        print(f"Zero-byte files: {len(zero_byte_files)}")
        zero_log = os.path.join(release_dir, "verification_zero_byte_2021.txt")
        with open(zero_log, 'w') as f:
            for filename in zero_byte_files:
                f.write(f"{filename}\n")
        print(f"Zero-byte files logged to: {zero_log}")
    else:
        print("No zero-byte files!")

def main():
    parser = argparse.ArgumentParser(description='Download JFK 2021 Files with improved verification')
    parser.add_argument('excel_file', nargs='?', help='Path to the 2021 Excel file')
    parser.add_argument('--threads', type=int, default=4, help='Number of download threads')
    parser.add_argument('--verify-only', action='store_true', help='Skip downloads and just verify existing files')
    
    args = parser.parse_args()
    
    # If excel_file is not provided, prompt for it
    excel_file = args.excel_file
    if not excel_file:
        excel_file = input("Enter the path to the 2021 Excel file: ")
    
    # Validate inputs
    if not os.path.exists(excel_file):
        print(f"Error: Excel file '{excel_file}' not found")
        return
    
    # Read the Excel file
    df = read_excel_file(excel_file)
    if df is None:
        return
    
    # Create release directory
    release_dir = os.path.join(DOWNLOAD_DIR, "release-2021")
    os.makedirs(release_dir, exist_ok=True)
    
    # Generate expected filenames set
    expected_filenames = set()
    for _, row in df.iterrows():
        pdf_path = str(row['File Title'])
        filename = os.path.basename(pdf_path)
        expected_filenames.add(filename)
    
    if args.verify_only:
        # Just verify existing files
        verify_downloads(release_dir, expected_filenames)
    else:
        # Process the downloads and verify
        process_downloads(df, args.threads)
    
    print("\nProcess completed!")

if __name__ == "__main__":
    main()
