#!/usr/bin/env python3
"""
JFK Final Release Downloader
--------------------------
This script downloads JFK files from one release at a time, preserving the exact path structure
from the Excel file.

Usage:
    python jfk_final_downloader.py [excel_file.xlsx] [release_year]
    
    If excel_file and release_year are not provided as arguments, the script will prompt for them.

Examples:
    python jfk_final_downloader.py nationalarchivesjfkassassinationrecords2023release.xlsx 2023
    python jfk_final_downloader.py
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
BASE_URLS = [
    "https://www.archives.gov/files/research/jfk/releases/",
    "https://www.archives.gov/research/jfk/releases/"
]
DOWNLOAD_DIR = os.path.expanduser("~/Downloads/JFK_Files")

# Create necessary directory
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def read_excel_file(excel_path):
    """Read an Excel file and return its DataFrame."""
    try:
        print(f"Reading Excel file: {excel_path}")
        # Determine the URL column based on the filename
        if '2021' in excel_path.lower():
            url_column = 'File Title'
        else:
            url_column = 'File Name'
        
        # Read the Excel file
        df = pd.read_excel(excel_path)
        
        # Verify the URL column exists
        if url_column not in df.columns:
            print(f"Error: Column '{url_column}' not found in {excel_path}")
            print(f"Available columns: {', '.join(df.columns)}")
            return None, None
        
        # Filter out rows without valid PDF URLs
        df = df[df[url_column].notna() & df[url_column].astype(str).str.contains('.pdf', case=False)]
        
        print(f"Found {len(df)} PDF entries in the Excel file")
        return df, url_column
    
    except Exception as e:
        print(f"Error reading Excel file {excel_path}: {e}")
        return None, None

def generate_pdf_urls(pdf_path, release_year):
    """Generate possible URLs for a PDF file."""
    urls = []
    
    # Process the path to handle different formats
    if pdf_path.startswith(('http://', 'https://')):
        # If it's already a full URL, use it directly
        urls.append(pdf_path)
    elif '/' in pdf_path:
        # Format: "2023/08/filename.pdf" or similar with subdirectories
        # First, preserve the exact path as in the Excel
        for base_url in BASE_URLS:
            # Try with the year prefix and the full path from Excel
            if release_year in pdf_path:
                # Path already contains year - use path as is
                parts = pdf_path.split('/')
                if len(parts) >= 2:
                    # Check if the first part is the year
                    if parts[0] == release_year:
                        # Remove the year from the path for proper URL construction
                        remaining_path = '/'.join(parts[1:])
                        urls.append(f"{base_url}{release_year}/{remaining_path}")
                    else:
                        # Keep path as is
                        urls.append(f"{base_url}{pdf_path}")
            else:
                # Path doesn't contain year - add release year
                urls.append(f"{base_url}{release_year}/{pdf_path}")
    else:
        # Just a filename without directories
        for base_url in BASE_URLS:
            urls.append(f"{base_url}{release_year}/{pdf_path}")
    
    # For 2017-2018 files, try both 2017 and 2018 directories if not already included
    if release_year == "2017-2018" and not ("2017/" in pdf_path or "2018/" in pdf_path):
        # Extract just the filename
        filename = os.path.basename(pdf_path)
        for base_url in BASE_URLS:
            urls.append(f"{base_url}2018/{filename}")
            urls.append(f"{base_url}2017/{filename}")
    
    # Remove any duplicate URLs
    return list(dict.fromkeys(urls))

def download_pdf_with_url_alternatives(urls, save_path, retries=2):
    """Try downloading a PDF using multiple possible URLs."""
    for url in urls:
        for attempt in range(retries):
            try:
                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()
                
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # If we got here, download was successful
                # Return success along with the URL that worked
                return url, True
            
            except requests.exceptions.RequestException as e:
                if attempt < retries - 1:
                    print(f"Retry {attempt+1}/{retries} for {url} after error: {e}")
                    time.sleep(2)
                elif "404" in str(e):
                    # 404 means file not found, try next URL
                    break
                else:
                    # For non-404 errors like timeouts, continue trying
                    continue
    
    # If we got here, all URLs failed
    print(f"Error downloading file after trying multiple URLs: {urls}")
    return urls[0], False

def download_worker(args):
    """Worker function for parallel downloads."""
    pdf_path, save_path, release_year = args
    urls = generate_pdf_urls(pdf_path, release_year)
    return pdf_path, download_pdf_with_url_alternatives(urls, save_path)

def verify_downloads(release_dir, expected_count):
    """Verify the actual number of files downloaded."""
    actual_count = sum(1 for f in os.listdir(release_dir) if f.endswith('.pdf'))
    print(f"\nVerification: {actual_count} files exist in the download directory")
    if actual_count != expected_count:
        print(f"Warning: Expected {expected_count} files but found {actual_count}")
    return actual_count

def process_release(excel_path, release_year, max_files=None, num_threads=4):
    """Process a JFK release based on an Excel file."""
    print(f"\n{'='*50}")
    print(f"Processing {release_year} release")
    print(f"{'='*50}")
    
    # Read the Excel file
    result = read_excel_file(excel_path)
    if result is None:
        return
    
    df, url_column = result
    
    # Create release directory
    release_dir = os.path.join(DOWNLOAD_DIR, f"release-{release_year}")
    os.makedirs(release_dir, exist_ok=True)
    
    # Limit the number of files if specified
    if max_files is not None:
        print(f"Limiting to {max_files} files for testing")
        df = df.head(max_files)
    
    # Prepare download tasks
    download_tasks = []
    for idx, row in df.iterrows():
        pdf_path = str(row[url_column])
        
        # Create a safe filename based on the end of the path
        filename = os.path.basename(pdf_path)
        save_path = os.path.join(release_dir, filename)
        
        # Skip if file already exists and has content
        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
            continue
        
        # Add to download tasks
        download_tasks.append((pdf_path, save_path, release_year))
    
    # Report on files to download
    print(f"Files to download: {len(download_tasks)} of {len(df)} total")
    
    if not download_tasks:
        print("No files need to be downloaded")
        actual_count = verify_downloads(release_dir, len(df))
        return
    
    # Adjust thread count for very small jobs
    if len(download_tasks) < num_threads:
        num_threads = max(1, len(download_tasks))
    
    # Download files in parallel
    successful = 0
    failed = 0
    failed_paths = []
    succeeded_paths = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {executor.submit(download_worker, task): task for task in download_tasks}
        
        with tqdm(total=len(download_tasks), desc=f"Downloading {release_year} PDFs") as pbar:
            for future in concurrent.futures.as_completed(futures):
                try:
                    pdf_path, (url, success) = future.result()
                    if success:
                        successful += 1
                        succeeded_paths.append((pdf_path, url))
                    else:
                        failed += 1
                        failed_paths.append(pdf_path)
                except Exception as e:
                    print(f"Error in worker: {e}")
                    failed += 1
                    failed_paths.append(futures[future][0])
                pbar.update(1)
    
    # Report on download results
    already_downloaded = len(df) - len(download_tasks)
    print(f"\nDownload summary for {release_year}:")
    print(f"- Total files to process: {len(df)}")
    print(f"- Already downloaded: {already_downloaded}")
    print(f"- Successfully downloaded: {successful}")
    print(f"- Failed downloads: {failed}")
    
    # Write failed downloads to a log file
    if failed_paths:
        failed_log = os.path.join(release_dir, f"failed_downloads_{release_year}.txt")
        with open(failed_log, 'w') as f:
            for path in failed_paths:
                f.write(f"{path}\n")
        print(f"Failed downloads logged to: {failed_log}")
    
    # Write successful downloads to a log file for debug purposes
    success_log = os.path.join(release_dir, f"successful_downloads_{release_year}.txt")
    with open(success_log, 'w') as f:
        for path, url in succeeded_paths:
            f.write(f"{path} -> {url}\n")
    print(f"Successful downloads logged to: {success_log}")
    
    # Verify the actual number of files downloaded
    expected_count = already_downloaded + successful
    actual_count = verify_downloads(release_dir, expected_count)
    
    # Add retry option for failed downloads
    if failed_paths and input("\nRetry failed downloads? (y/n): ").lower() == 'y':
        print(f"Retrying {len(failed_paths)} failed downloads...")
        retry_tasks = []
        for path in failed_paths:
            filename = os.path.basename(path)
            save_path = os.path.join(release_dir, filename)
            retry_tasks.append((path, save_path, release_year))
        
        # Create a separate function call to retry
        process_retry_downloads(retry_tasks, release_dir, release_year)

def process_retry_downloads(retry_tasks, release_dir, release_year):
    """Process retry of failed downloads with different URL patterns."""
    if not retry_tasks:
        return
    
    print(f"\n{'='*50}")
    print(f"Retrying {len(retry_tasks)} failed downloads with special patterns")
    print(f"{'='*50}")
    
    # Try some additional URL patterns for the retries
    successful = 0
    failed = 0
    failed_paths = []
    
    for pdf_path, save_path, release_year in tqdm(retry_tasks, desc="Retrying downloads"):
        # Generate more creative URLs for the retries
        filename = os.path.basename(pdf_path)
        record_num = None
        
        # Try to extract record number from filename using regex
        match = re.search(r'(\d{3}-\d{5}-\d{5})', filename)
        if match:
            record_num = match.group(1)
        
        urls = []
        # Standard URLs from before
        urls.extend(generate_pdf_urls(pdf_path, release_year))
        
        # Add more creative URLs based on patterns in the data
        if "2023/08" in pdf_path:
            # Try without month
            clean_path = pdf_path.replace("2023/08/", "")
            urls.append(f"https://www.archives.gov/files/research/jfk/releases/2023/{clean_path}")
        
        if record_num:
            # Try record number as filename
            urls.append(f"https://www.archives.gov/files/research/jfk/releases/2023/{record_num}.pdf")
            urls.append(f"https://www.archives.gov/research/jfk/releases/2023/{record_num}.pdf")
            
            # Try alternate formats like DOCID- prefix
            if "DOCID" not in filename:
                urls.append(f"https://www.archives.gov/files/research/jfk/releases/2023/DOCID-{record_num}.pdf")
        
        # Try direct download
        success = False
        working_url = None
        
        for url in urls:
            try:
                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()
                
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # If we got here, download was successful
                success = True
                working_url = url
                break
            
            except requests.exceptions.RequestException:
                continue  # Try next URL
        
        if success:
            successful += 1
            print(f"Success: {pdf_path} -> {working_url}")
        else:
            failed += 1
            failed_paths.append(pdf_path)
    
    # Write failed downloads to a log file
    if failed_paths:
        failed_log = os.path.join(release_dir, f"final_failed_downloads_{release_year}.txt")
        with open(failed_log, 'w') as f:
            for path in failed_paths:
                f.write(f"{path}\n")
        print(f"Failed downloads logged to: {failed_log}")
    
    print(f"\nRetry summary:")
    print(f"- Files retried: {len(retry_tasks)}")
    print(f"- Successfully downloaded: {successful}")
    print(f"- Failed downloads: {failed}")
    
    # Verify the actual number of files after retries
    verify_downloads(release_dir, None)

def main():
    parser = argparse.ArgumentParser(description='Download JFK Files from a single Excel file with exact path preservation')
    parser.add_argument('excel_file', nargs='?', help='Path to the Excel file containing PDF links')
    parser.add_argument('release_year', nargs='?', help='Release year (e.g., 2023, 2022, 2021, 2017-2018)')
    parser.add_argument('--max-files', type=int, help='Maximum number of files to download')
    parser.add_argument('--threads', type=int, default=4, help='Number of download threads')
    
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
    
    if release_year not in ['2023', '2022', '2021', '2017-2018']:
        print(f"Warning: '{release_year}' is not one of the expected release years (2023, 2022, 2021, 2017-2018)")
        confirm = input("Continue anyway? (y/n): ")
        if confirm.lower() != 'y':
            return
    
    # Process the release
    process_release(excel_file, release_year, args.max_files, args.threads)
    
    print("\nDownload completed!")

if __name__ == "__main__":
    main()
