#!/usr/bin/env python3
"""
JFK Missing Files Recovery Tool
-----------------------------
This script focuses on downloading only the missing files identified by the diagnostic tool.
It can be used after the main download to fill in any gaps.

Usage:
    python jfk_recover_missing.py [excel_file.xlsx] [release_year] [missing_files.txt]
    
    If the parameters are not provided, the script will prompt for them.
"""

import os
import sys
import requests
import pandas as pd
import time
import argparse
from urllib.parse import urljoin
from tqdm import tqdm
import concurrent.futures

# Configuration
BASE_URLS = [
    "https://www.archives.gov/files/research/jfk/releases/",
    "https://www.archives.gov/research/jfk/releases/"
]
DOWNLOAD_DIR = os.path.expanduser("~/Downloads/JFK_Files")

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
        
        # Extract just the filename part as a new column
        df['filename'] = df[url_column].apply(lambda x: os.path.basename(str(x)))
        
        print(f"Found {len(df)} PDF entries in the Excel file")
        return df, url_column
    
    except Exception as e:
        print(f"Error reading Excel file {excel_path}: {e}")
        return None, None

def read_missing_files(missing_file_path):
    """Read the list of missing files from the diagnostic tool output."""
    try:
        with open(missing_file_path, 'r') as f:
            lines = f.readlines()
        
        # Extract just the filename part (before the parenthesis)
        missing_files = []
        for line in lines:
            if '(' in line:
                filename = line.split('(')[0].strip()
                missing_files.append(filename)
            else:
                # If there's no parenthesis, just use the whole line
                missing_files.append(line.strip())
        
        print(f"Found {len(missing_files)} missing files to recover")
        return missing_files
    
    except Exception as e:
        print(f"Error reading missing files list {missing_file_path}: {e}")
        return []

def generate_pdf_urls(pdf_path, release_year):
    """Generate multiple possible URLs for a PDF file."""
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
    
    # Try additional URL variations - using just the filename
    filename = os.path.basename(pdf_path)
    for base_url in BASE_URLS:
        urls.append(f"{base_url}{release_year}/{filename}")
    
    # If the path format includes a month directory (common for 2023)
    if '/' in pdf_path and release_year == "2023":
        parts = pdf_path.split('/')
        if len(parts) >= 3:  # year/month/filename.pdf format
            month = parts[1]
            filename = parts[-1]
            for base_url in BASE_URLS:
                urls.append(f"{base_url}{release_year}/{month}/{filename}")
    
    # Remove any duplicate URLs
    return list(dict.fromkeys(urls))

def download_pdf_with_url_alternatives(urls, save_path, retries=3, timeout=30):
    """Try downloading a PDF using multiple possible URLs."""
    for url in urls:
        for attempt in range(retries):
            try:
                response = requests.get(url, stream=True, timeout=timeout)
                response.raise_for_status()
                
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # Verify file was written and is not empty
                if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                    return url, True
                else:
                    # If the file is empty, try the next URL
                    os.remove(save_path)
                    break
                
            except requests.exceptions.RequestException as e:
                if attempt < retries - 1:
                    print(f"Retry {attempt+1}/{retries} for {url} after error: {e}")
                    time.sleep(2)
                else:
                    # Try the next URL without printing error
                    break
    
    # If we got here, all URLs failed
    print(f"Error downloading file after trying multiple URLs.")
    return urls[0], False

def download_worker(args):
    """Worker function for parallel downloads."""
    row, url_column, release_year, release_dir = args
    pdf_path = str(row[url_column])
    filename = row['filename']
    
    save_path = os.path.join(release_dir, filename)
    
    urls = generate_pdf_urls(pdf_path, release_year)
    return pdf_path, filename, download_pdf_with_url_alternatives(urls, save_path)

def recover_missing_files(df, url_column, missing_files, release_year, num_threads=4):
    """Download the missing files identified by the diagnostic tool."""
    print(f"\n{'='*50}")
    print(f"Recovering missing files for {release_year} release")
    print(f"{'='*50}")
    
    # Create release directory
    release_dir = os.path.join(DOWNLOAD_DIR, f"release-{release_year}")
    os.makedirs(release_dir, exist_ok=True)
    
    # Filter the DataFrame to only include the missing files
    missing_df = df[df['filename'].isin(missing_files)]
    
    if len(missing_df) == 0:
        print("No matching files found in the Excel file for the missing files list.")
        return
    
    print(f"Found {len(missing_df)} records in Excel matching the missing files.")
    
    # Prepare download tasks
    download_tasks = []
    for idx, row in missing_df.iterrows():
        download_tasks.append((row, url_column, release_year, release_dir))
    
    # Adjust thread count for very small jobs
    if len(download_tasks) < num_threads:
        num_threads = max(1, len(download_tasks))
    
    # Download files in parallel
    successful = 0
    failed = 0
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {executor.submit(download_worker, task): task[0]['filename'] for task in download_tasks}
        
        with tqdm(total=len(download_tasks), desc=f"Recovering files") as pbar:
            for future in concurrent.futures.as_completed(futures):
                pdf_path, filename, (url, success) = future.result()
                if success:
                    successful += 1
                    results.append((filename, url, "SUCCESS"))
                else:
                    failed += 1
                    results.append((filename, url, "FAILED"))
                pbar.update(1)
    
    # Report on download results
    print(f"\nRecovery summary:")
    print(f"- Total files to recover: {len(missing_df)}")
    print(f"- Successfully recovered: {successful}")
    print(f"- Failed recoveries: {failed}")
    
    # Save recovery results to a log file
    results_log = os.path.join(release_dir, f"recovery_results_{release_year}.txt")
    with open(results_log, 'w') as f:
        for filename, url, status in results:
            f.write(f"{filename}: {status} ({url})\n")
    print(f"Recovery results logged to: {results_log}")
    
    # Verify actual downloads
    actually_downloaded = sum(1 for r in results if r[2] == "SUCCESS" and 
                             os.path.exists(os.path.join(release_dir, r[0])) and 
                             os.path.getsize(os.path.join(release_dir, r[0])) > 0)
    
    print(f"Verified downloads: {actually_downloaded} files were successfully saved to disk")
    
    # Update missing files
    still_missing = []
    for filename in missing_files:
        filepath = os.path.join(release_dir, filename)
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            still_missing.append(filename)
    
    if still_missing:
        print(f"\nThere are still {len(still_missing)} files missing:")
        for i, filename in enumerate(still_missing, 1):
            print(f"  {i}. {filename}")
        
        # Save to file
        still_missing_log = os.path.join(release_dir, f"still_missing_{release_year}.txt")
        with open(still_missing_log, 'w') as f:
            for filename in still_missing:
                f.write(f"{filename}\n")
        print(f"Still missing files logged to: {still_missing_log}")
    else:
        print("\nAll files have been successfully recovered!")

def main():
    parser = argparse.ArgumentParser(description='Recover missing JFK files')
    parser.add_argument('excel_file', nargs='?', help='Path to the Excel file containing PDF links')
    parser.add_argument('release_year', nargs='?', help='Release year (e.g., 2023, 2022, 2021, 2017-2018)')
    parser.add_argument('missing_file', nargs='?', help='Path to the file containing list of missing files')
    parser.add_argument('--threads', type=int, default=4, help='Number of download threads')
    
    args = parser.parse_args()
    
    # If parameters are not provided, prompt for them
    excel_file = args.excel_file
    if not excel_file:
        excel_file = input("Enter the path to the Excel file: ")
    
    release_year = args.release_year
    if not release_year:
        release_year = input("Enter the release year (e.g., 2023, 2022, 2021, 2017-2018): ")
    
    missing_file = args.missing_file
    if not missing_file:
        default_path = os.path.join(DOWNLOAD_DIR, f"release-{release_year}", f"missing_files_{release_year}.txt")
        if os.path.exists(default_path):
            print(f"Found missing files list at: {default_path}")
            use_default = input(f"Use this file? (y/n): ")
            if use_default.lower() == 'y':
                missing_file = default_path
            else:
                missing_file = input("Enter the path to the missing files list: ")
        else:
            missing_file = input("Enter the path to the missing files list: ")
    
    # Validate inputs
    if not os.path.exists(excel_file):
        print(f"Error: Excel file '{excel_file}' not found")
        return
    
    if not os.path.exists(missing_file):
        print(f"Error: Missing files list '{missing_file}' not found")
        return
    
    # Read the Excel file
    df, url_column = read_excel_file(excel_file)
    if df is None:
        return
    
    # Read the missing files list
    missing_files = read_missing_files(missing_file)
    if not missing_files:
        return
    
    # Recover the missing files
    recover_missing_files(df, url_column, missing_files, release_year, args.threads)
    
    print("\nRecovery completed!")

if __name__ == "__main__":
    main()
