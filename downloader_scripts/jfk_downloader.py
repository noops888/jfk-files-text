#!/usr/bin/env python3
"""
JFK Archive Downloader

This script downloads JFK assassination records from the National Archives website,
preserving the original directory structure. It supports multithreading, crash recovery,
and handles various file types while maintaining exact filenames.

Usage:
    python jfk_downloader.py --csv CSV_FILE --output OUTPUT_DIR [--threads THREADS] [--resume]

Arguments:
    --csv CSV_FILE       Path to the CSV file containing download URLs
    --output OUTPUT_DIR  Directory where files will be downloaded
    --threads THREADS    Number of download threads (default: 4)
    --resume             Resume previous download (skip already downloaded files)
    --verify             Verify integrity of previously downloaded files
    --help               Show this help message and exit
"""

import argparse
import csv
import hashlib
import logging
import os
import queue
import re
import sys
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("jfk_downloader.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Constants
CHUNK_SIZE = 8192  # 8KB chunks for downloading
DOWNLOAD_TIMEOUT = 60  # 60 seconds timeout for downloads
MAX_RETRIES = 5  # Maximum number of retries for a download
PROGRESS_UPDATE_INTERVAL = 2  # Update progress every 2 seconds


class DownloadTracker:
    """Tracks download progress and statistics."""
    
    def __init__(self):
        self.total_files = 0
        self.downloaded_files = 0
        self.skipped_files = 0
        self.failed_files = 0
        self.verified_files = 0
        self.total_bytes = 0
        self.lock = threading.Lock()
        self.start_time = time.time()
        self.last_update_time = time.time()
        self.last_update_bytes = 0
        self.last_update_files = 0
    
    def update(self, bytes_downloaded=0, file_status=None):
        """Update download statistics."""
        with self.lock:
            self.total_bytes += bytes_downloaded
            
            if file_status == 'downloaded':
                self.downloaded_files += 1
            elif file_status == 'skipped':
                self.skipped_files += 1
            elif file_status == 'failed':
                self.failed_files += 1
            elif file_status == 'verified':
                self.verified_files += 1
            
            # Update progress periodically
            current_time = time.time()
            if current_time - self.last_update_time >= PROGRESS_UPDATE_INTERVAL:
                self.print_progress()
                self.last_update_time = current_time
                self.last_update_bytes = self.total_bytes
                self.last_update_files = self.downloaded_files + self.skipped_files + self.verified_files
    
    def print_progress(self):
        """Print download progress."""
        elapsed_time = time.time() - self.start_time
        if elapsed_time < 1:
            elapsed_time = 1
        
        bytes_per_sec = self.total_bytes / elapsed_time
        files_per_sec = (self.downloaded_files + self.skipped_files + self.verified_files) / elapsed_time
        
        # Calculate recent rates
        recent_elapsed = time.time() - self.last_update_time
        if recent_elapsed >= 1:
            recent_bytes = self.total_bytes - self.last_update_bytes
            recent_files = (self.downloaded_files + self.skipped_files + self.verified_files) - self.last_update_files
            recent_bytes_per_sec = recent_bytes / recent_elapsed
            recent_files_per_sec = recent_files / recent_elapsed
        else:
            recent_bytes_per_sec = 0
            recent_files_per_sec = 0
        
        logger.info(
            f"Progress: {self.downloaded_files + self.skipped_files + self.verified_files}/{self.total_files} files "
            f"({(self.downloaded_files + self.skipped_files + self.verified_files) / max(1, self.total_files) * 100:.1f}%) | "
            f"Downloaded: {self.downloaded_files} | Skipped: {self.skipped_files} | "
            f"Verified: {self.verified_files} | Failed: {self.failed_files} | "
            f"Speed: {format_size(recent_bytes_per_sec)}/s ({recent_files_per_sec:.2f} files/s) | "
            f"Total: {format_size(self.total_bytes)}"
        )


class DownloadManager:
    """Manages the download process for JFK archive files."""
    
    def __init__(self, csv_file, output_dir, num_threads=4, resume=False, verify=False):
        self.csv_file = csv_file
        self.output_dir = Path(output_dir)
        self.num_threads = num_threads
        self.resume = resume
        self.verify = verify
        self.tracker = DownloadTracker()
        self.download_queue = queue.Queue()
        self.session = self._create_session()
        self.lock = threading.Lock()
        self.progress_file = self.output_dir / ".download_progress.csv"
        self.completed_files = set()
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _create_session(self):
        """Create a requests session with retry logic."""
        session = requests.Session()
        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def load_csv(self):
        """Load download URLs from CSV file."""
        logger.info(f"Loading URLs from {self.csv_file}")
        
        try:
            with open(self.csv_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                urls = list(reader)
                self.tracker.total_files = len(urls)
                logger.info(f"Found {self.tracker.total_files} files to download")
                return urls
        except Exception as e:
            logger.error(f"Error loading CSV file: {e}")
            sys.exit(1)
    
    def load_progress(self):
        """Load progress from previous download session."""
        if not self.progress_file.exists():
            logger.info("No previous download progress found")
            return
        
        try:
            with open(self.progress_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        url, status = row
                        if status in ['downloaded', 'verified']:
                            self.completed_files.add(url)
            
            logger.info(f"Loaded {len(self.completed_files)} completed files from previous session")
        except Exception as e:
            logger.error(f"Error loading progress file: {e}")
    
    def save_progress(self, url, status):
        """Save download progress."""
        try:
            with self.lock:
                with open(self.progress_file, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([url, status])
        except Exception as e:
            logger.error(f"Error saving progress: {e}")
    
    def parse_url(self, url):
        """Parse URL to determine local file path."""
        parsed_url = urlparse(url)
        
        # Extract path components
        path_parts = parsed_url.path.split('/')
        
        # Find the index of 'jfk' in the path
        try:
            jfk_index = path_parts.index('jfk')
            # Get all parts after 'jfk'
            relative_path = path_parts[jfk_index + 1:]
            # Join the parts to form the local path
            local_path = os.path.join(*relative_path)
            return local_path
        except ValueError:
            # If 'jfk' is not in the path, use the full path
            return os.path.join(*path_parts[1:])
    
    def download_file(self, url, filename, local_path):
        """Download a single file."""
        full_path = self.output_dir / local_path
        temp_path = full_path.with_suffix(full_path.suffix + '.part')
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Check if file already exists and we're resuming
        if self.resume and url in self.completed_files:
            if self.verify:
                # Verify the file integrity
                if self.verify_file(full_path):
                    logger.debug(f"Verified: {filename}")
                    self.tracker.update(file_status='verified')
                    return True
                else:
                    logger.warning(f"Integrity check failed, re-downloading: {filename}")
            else:
                logger.debug(f"Skipped (already downloaded): {filename}")
                self.tracker.update(file_status='skipped')
                return True
        
        # Download the file
        try:
            response = self.session.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT)
            response.raise_for_status()
            
            file_size = int(response.headers.get('content-length', 0))
            downloaded_bytes = 0
            
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        downloaded_bytes += len(chunk)
                        self.tracker.update(bytes_downloaded=len(chunk))
            
            # Rename temp file to final filename
            os.replace(temp_path, full_path)
            
            # Update progress
            self.save_progress(url, 'downloaded')
            self.completed_files.add(url)
            self.tracker.update(file_status='downloaded')
            
            return True
        
        except Exception as e:
            logger.error(f"Error downloading {filename}: {e}")
            self.tracker.update(file_status='failed')
            
            # Clean up temp file if it exists
            if temp_path.exists():
                try:
                    os.remove(temp_path)
                except:
                    pass
            
            return False
    
    def verify_file(self, file_path):
        """Verify file integrity by checking if it's a valid file."""
        try:
            # Check if file exists and has non-zero size
            if not file_path.exists() or file_path.stat().st_size == 0:
                return False
            
            # For PDF files, check if it starts with the PDF signature
            if file_path.suffix.lower() == '.pdf':
                with open(file_path, 'rb') as f:
                    header = f.read(5)
                    return header == b'%PDF-'
            
            # For other files, just check if they exist and have content
            return True
        except Exception as e:
            logger.error(f"Error verifying {file_path}: {e}")
            return False
    
    def worker(self):
        """Worker thread for downloading files."""
        while True:
            try:
                item = self.download_queue.get(block=False)
                if item is None:
                    break
                
                url = item['url']
                filename = item['filename']
                
                # Parse URL to get local path
                local_path = self.parse_url(url)
                
                # Download the file
                self.download_file(url, filename, local_path)
                
            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"Worker error: {e}")
            finally:
                if 'item' in locals():
                    self.download_queue.task_done()
    
    def run(self):
        """Run the download process."""
        logger.info(f"Starting download with {self.num_threads} threads")
        logger.info(f"Output directory: {self.output_dir}")
        
        # Load progress if resuming
        if self.resume:
            self.load_progress()
        
        # Load URLs from CSV
        urls = self.load_csv()
        
        # Add URLs to download queue
        for item in urls:
            self.download_queue.put(item)
        
        # Start worker threads
        threads = []
        for _ in range(self.num_threads):
            thread = threading.Thread(target=self.worker)
            thread.start()
            threads.append(thread)
        
        # Wait for all downloads to complete
        for thread in threads:
            thread.join()
        
        # Print final statistics
        self.tracker.print_progress()
        logger.info(f"Download complete. Downloaded: {self.tracker.downloaded_files}, "
                   f"Skipped: {self.tracker.skipped_files}, Failed: {self.tracker.failed_files}")


def format_size(bytes_size):
    """Format bytes to human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Download JFK assassination records from the National Archives')
    parser.add_argument('--csv', required=True, help='Path to the CSV file containing download URLs')
    parser.add_argument('--output', required=True, help='Directory where files will be downloaded')
    parser.add_argument('--threads', type=int, default=4, help='Number of download threads (default: 4)')
    parser.add_argument('--resume', action='store_true', help='Resume previous download (skip already downloaded files)')
    parser.add_argument('--verify', action='store_true', help='Verify integrity of previously downloaded files')
    return parser.parse_args()


def main():
    """Main function."""
    args = parse_arguments()
    
    # Create download manager
    manager = DownloadManager(
        csv_file=args.csv,
        output_dir=args.output,
        num_threads=args.threads,
        resume=args.resume,
        verify=args.verify
    )
    
    # Run the download process
    manager.run()


if __name__ == "__main__":
    main()
