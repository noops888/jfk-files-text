#!/usr/bin/env python3
"""
JFK Files Downloader for macOS (Python Version)
This script downloads files from the National Archives JFK release
Handles duplicate filenames, subdirectories, and provides progress tracking and recovery
Supports multi-threading for faster downloads
"""

import os
import sys
import csv
import time
import argparse
import requests
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from urllib.parse import urlparse

# Global variables for thread-safe operations
download_queue = queue.Queue()
progress_lock = threading.Lock()
log_lock = threading.Lock()
progress_bar = None
downloaded_files = set()
success_count = 0
failed_count = 0

def get_user_input():
    """Get input file, output directory, and thread count from user"""
    print("JFK Files Downloader (Python Version)")
    print("====================================")
    
    # Get input file
    default_input = 'unique_urls.csv'
    input_file = input(f"Enter the URL list file path [default: {default_input}]: ").strip()
    if not input_file:
        input_file = default_input
    
    # Validate input file exists
    while not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found.")
        input_file = input(f"Enter a valid URL list file path [default: {default_input}]: ").strip()
        if not input_file:
            input_file = default_input
            if os.path.exists(input_file):
                break
    
    # Get output directory
    current_dir = os.getcwd()
    output_dir = input(f"Enter download directory [default: {current_dir}]: ").strip()
    if not output_dir:
        output_dir = current_dir
    
    # Get thread count
    default_threads = 4
    thread_input = input(f"Enter number of download threads [default: {default_threads}]: ").strip()
    if not thread_input:
        thread_count = default_threads
    else:
        try:
            thread_count = int(thread_input)
            if thread_count < 1:
                print(f"Invalid thread count. Using default: {default_threads}")
                thread_count = default_threads
        except ValueError:
            print(f"Invalid thread count. Using default: {default_threads}")
            thread_count = default_threads
    
    return input_file, output_dir, thread_count

def ensure_directory(directory):
    """Ensure the download directory exists"""
    if not os.path.exists(directory):
        print(f"Creating download directory: {directory}")
        try:
            os.makedirs(directory)
        except OSError as e:
            print(f"Error: Failed to create download directory: {e}")
            sys.exit(1)

def load_urls(url_file):
    """Load URLs from CSV file"""
    urls = []
    has_subdirectory_column = False
    
    try:
        with open(url_file, 'r') as f:
            # Check first line to determine CSV format
            first_line = f.readline().strip()
            headers = first_line.split(',')
            
            # Check if the CSV has a subdirectory column
            has_subdirectory_column = len(headers) >= 3 and headers[2].lower() == 'subdirectory'
            
            # Reset file pointer
            f.seek(0)
            
            reader = csv.reader(f)
            next(reader)  # Skip header
            
            for row in reader:
                if len(row) >= 2:
                    filename = row[0]
                    url = row[1]
                    
                    # Check for subdirectory
                    subdirectory = ""
                    if has_subdirectory_column and len(row) >= 3:
                        subdirectory = row[2]
                    
                    urls.append((filename, url, subdirectory))
    except Exception as e:
        print(f"Error reading URL file: {e}")
        sys.exit(1)
    
    return urls

def load_progress(progress_file):
    """Load previously downloaded files from progress file"""
    downloaded = set()
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            for line in f:
                downloaded.add(line.strip())
    return downloaded

def download_worker(download_dir, progress_file, log_file):
    """Worker function for downloading files in a thread"""
    global success_count, failed_count
    
    while True:
        try:
            # Get a file from the queue
            filename, url, subdirectory = download_queue.get(block=False)
            
            # Skip if already downloaded
            if filename in downloaded_files:
                download_queue.task_done()
                continue
            
            # Create full path including subdirectory if needed
            if subdirectory:
                # Create subdirectory if it doesn't exist
                subdir_path = os.path.join(download_dir, subdirectory)
                if not os.path.exists(subdir_path):
                    with progress_lock:
                        if not os.path.exists(subdir_path):
                            os.makedirs(subdir_path)
                output_path = os.path.join(subdir_path, filename)
            else:
                output_path = os.path.join(download_dir, filename)
            
            # Download the file
            try:
                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()
                
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # Mark as downloaded
                with progress_lock:
                    with open(progress_file, 'a') as f:
                        f.write(f"{filename}\n")
                    downloaded_files.add(filename)
                    success_count += 1
                
                # Log success
                with log_lock:
                    with open(log_file, 'a') as log:
                        log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - SUCCESS: {filename}\n")
            
            except Exception as e:
                # Log failure
                with log_lock:
                    with open(log_file, 'a') as log:
                        log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - FAILED: {filename} - {url} - {str(e)}\n")
                with progress_lock:
                    failed_count += 1
            
            # Update progress bar
            with progress_lock:
                progress_bar.update(1)
            
            # Mark task as done
            download_queue.task_done()
        
        except queue.Empty:
            # No more files to download
            break

def main():
    """Main function"""
    global progress_bar, downloaded_files, success_count, failed_count
    
    # Get input file, output directory, and thread count from user
    url_file, download_dir, thread_count = get_user_input()
    
    # Setup paths
    download_dir = os.path.abspath(download_dir)
    progress_file = os.path.join(download_dir, '.download_progress.txt')
    log_file = os.path.join(download_dir, 'download_log.txt')
    
    # Ensure download directory exists
    ensure_directory(download_dir)
    
    # Load URLs
    urls = load_urls(url_file)
    total_files = len(urls)
    
    # Load progress
    downloaded_files = load_progress(progress_file)
    
    print(f"Download directory: {download_dir}")
    print(f"URL file: {url_file}")
    print(f"Total files to download: {total_files}")
    print(f"Using {thread_count} download threads")
    
    # Count files by subdirectory
    subdirectory_counts = {}
    for _, _, subdirectory in urls:
        if subdirectory not in subdirectory_counts:
            subdirectory_counts[subdirectory] = 0
        subdirectory_counts[subdirectory] += 1
    
    # Display subdirectory information
    for subdir, count in subdirectory_counts.items():
        if subdir:
            print(f"Files in '{subdir}' subdirectory: {count}")
        else:
            print(f"Files in main directory: {count}")
    
    # Ask for confirmation before starting
    confirm = input(f"Ready to download {total_files} files. Continue? (y/n): ").strip().lower()
    if confirm != 'y' and confirm != 'yes':
        print("Download cancelled.")
        return
    
    # Log start
    with open(log_file, 'a') as log:
        log.write(f"Download session started at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"Using {thread_count} download threads\n")
    
    if downloaded_files:
        print(f"Resuming download: {len(downloaded_files)} files already downloaded")
    
    # Initialize progress bar
    progress_bar = tqdm(total=total_files, unit='file', desc="Overall Progress")
    
    # Update progress bar for already downloaded files
    progress_bar.update(len(downloaded_files))
    
    # Add files to download queue
    for filename, url, subdirectory in urls:
        if filename not in downloaded_files:
            download_queue.put((filename, url, subdirectory))
    
    # Create and start worker threads
    threads = []
    for _ in range(thread_count):
        thread = threading.Thread(
            target=download_worker,
            args=(download_dir, progress_file, log_file)
        )
        thread.daemon = True
        thread.start()
        threads.append(thread)
    
    # Wait for all downloads to complete
    download_queue.join()
    
    # Wait for all threads to finish
    for thread in threads:
        thread.join()
    
    # Close progress bar
    progress_bar.close()
    
    # Log completion
    with open(log_file, 'a') as log:
        log.write(f"Download session completed at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"Total files: {total_files}, Successful: {len(downloaded_files)}, Failed: {failed_count}\n\n")
    
    print("\nDownload completed!")
    print("==================")
    print(f"Total files: {total_files}")
    print(f"Successfully downloaded: {len(downloaded_files)}")
    print(f"Failed downloads: {failed_count}")
    print(f"Download log saved to: {log_file}")

if __name__ == "__main__":
    main()
