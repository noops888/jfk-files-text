#!/usr/bin/env python3
import os
import glob
from pathlib import Path
import pytesseract
from pdf2image import convert_from_path
import logging
import gc
import psutil
import sys
import time
import shutil
import json
import hashlib
from datetime import datetime
from tqdm import tqdm
import signal
import atexit
from typing import Dict, List, Optional
import argparse

# Set up logging with both file and console output
log_file = "pdf_processing.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

# Global state for crash recovery
PROGRESS_FILE = "processing_progress.json"
TEMP_DIR = "temp_processing"
MAX_RETRIES = 3
BATCH_SIZE = 10  # Process files in batches for better memory management

class ProcessingState:
    def __init__(self):
        self.processed_files: Dict[str, str] = {}  # filename -> md5 hash
        self.current_batch: List[str] = []
        self.last_processed_file: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.total_files: int = 0
        self.processed_count: int = 0
        self.failed_files: Dict[str, int] = {}  # filename -> retry count

    def save(self):
        """Save current state to file"""
        state_dict = {
            'processed_files': self.processed_files,
            'current_batch': self.current_batch,
            'last_processed_file': self.last_processed_file,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'total_files': self.total_files,
            'processed_count': self.processed_count,
            'failed_files': self.failed_files
        }
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(state_dict, f)

    @classmethod
    def load(cls) -> 'ProcessingState':
        """Load state from file"""
        state = cls()
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, 'r') as f:
                state_dict = json.load(f)
                state.processed_files = state_dict.get('processed_files', {})
                state.current_batch = state_dict.get('current_batch', [])
                state.last_processed_file = state_dict.get('last_processed_file')
                state.start_time = datetime.fromisoformat(state_dict['start_time']) if state_dict.get('start_time') else None
                state.total_files = state_dict.get('total_files', 0)
                state.processed_count = state_dict.get('processed_count', 0)
                state.failed_files = state_dict.get('failed_files', {})
        return state

def calculate_file_hash(filepath: str) -> str:
    """Calculate MD5 hash of a file"""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def log_memory_usage():
    """Log current memory usage"""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    logging.info(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")

def log_disk_usage():
    """Log disk usage"""
    disk = psutil.disk_usage('/')
    logging.info(f"Disk usage: {disk.percent}% (free: {disk.free / 1024 / 1024:.2f} MB)")

def cleanup_temp_files():
    """Clean up temporary files"""
    if os.path.exists(TEMP_DIR):
        logging.info("Cleaning up temporary files...")
        shutil.rmtree(TEMP_DIR)
        os.makedirs(TEMP_DIR, exist_ok=True)

def get_pdf_page_count(pdf_path: str) -> int:
    """Get the total number of pages in a PDF file"""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        count = doc.page_count
        doc.close()
        return count
    except Exception as e:
        logging.error(f"Error getting page count for {pdf_path}: {e}")
        return 0

def is_file_complete(output_path: str) -> bool:
    """Check if a file has been completely processed"""
    if not os.path.exists(output_path):
        return False
    try:
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return len(content.strip()) > 0
    except Exception:
        return False

def extract_text_from_pdf(pdf_path: str, output_dir: str, state: ProcessingState) -> bool:
    """
    Extract text from a PDF file and save it as markdown.
    Returns True if successful, False otherwise.
    """
    output_path = os.path.join(output_dir, f"{Path(pdf_path).stem}.md")
    temp_dir = os.path.join(TEMP_DIR, Path(pdf_path).stem)
    os.makedirs(temp_dir, exist_ok=True)
    
    # Skip if already processed and file exists
    if pdf_path in state.processed_files and is_file_complete(output_path):
        logging.info(f"Skipping already processed file: {pdf_path}")
        return True

    try:
        # Get total number of pages
        total_pages = get_pdf_page_count(pdf_path)
        if total_pages == 0:
            logging.error(f"Could not determine page count for {pdf_path}")
            return False
            
        logging.info(f"Processing PDF with {total_pages} pages: {pdf_path}")
        
        # Check for existing page files
        existing_pages = set()
        for file in os.listdir(temp_dir):
            if file.startswith('page_') and file.endswith('.txt'):
                try:
                    page_num = int(file.split('_')[1].split('.')[0])
                    existing_pages.add(page_num)
                except ValueError:
                    continue
        
        # Extract text from each page
        extracted_text = []
        for page_num in range(1, total_pages + 1):
            # Skip if page was already processed
            if page_num in existing_pages:
                logging.info(f"Loading existing page {page_num} of {pdf_path}")
                with open(os.path.join(temp_dir, f'page_{page_num}.txt'), 'r', encoding='utf-8') as f:
                    extracted_text.append(f.read())
                continue
                
            logging.info(f"Processing page {page_num} of {total_pages} {pdf_path}")
            log_memory_usage()
            log_disk_usage()
            
            # Convert only the current page
            images = convert_from_path(
                pdf_path,
                first_page=page_num,
                last_page=page_num,
                thread_count=1,
                dpi=300,
                grayscale=True
            )
            
            if not images:
                logging.error(f"Failed to convert page {page_num}")
                continue
                
            # Extract text from the current page with specific Tesseract config
            # Language codes: eng, spa, rus, deu (German), fra (French), ita (Italian), bul
            tesseract_config = '-l eng+spa+rus+deu+fra+ita+bul --oem 1 --psm 3' 
            text = pytesseract.image_to_string(images[0], config=tesseract_config)
            extracted_text.append(text)
            
            # Save page text to temporary file
            with open(os.path.join(temp_dir, f'page_{page_num}.txt'), 'w', encoding='utf-8') as f:
                f.write(text)
            
            # Clean up the image
            images[0].close()
            del images
            gc.collect()
            
            # Save progress after each page
            state.save()
            
            # Small delay between pages
            time.sleep(0.5)
        
        # Assemble the final text with headers
        file_stem = Path(pdf_path).stem
        full_text_parts = [f"# {file_stem}\n\n"]
        for page_num_one_indexed, page_content in enumerate(extracted_text, 1):
            full_text_parts.append(f"## Page {page_num_one_indexed}\n\n{page_content.strip()}\n\n")
        
        full_text = "".join(full_text_parts)

        # Write to markdown file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
        
        # Update processing state
        state.processed_files[pdf_path] = calculate_file_hash(pdf_path)
        state.processed_count += 1
        state.save()
        
        logging.info(f"Successfully extracted text to {output_path}")
        
        # Clean up
        del extracted_text
        gc.collect()
        
        # Clean up temporary files
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        
        return True
        
    except Exception as e:
        logging.error(f"Error processing {pdf_path}: {str(e)}")
        # If file exists but processing failed, delete it
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception as e:
                logging.warning(f"Failed to delete incomplete file {output_path}: {e}")
        return False
    finally:
        gc.collect()

def get_pdf_files(directory: str) -> List[str]:
    """Get all PDF files from directory, case insensitive."""
    pdf_files = []
    for file in os.listdir(directory):
        if file.lower().endswith('.pdf'):
            pdf_files.append(os.path.join(directory, file))
    return sorted(pdf_files)  # Sort for consistent processing order

def process_batch(files: List[str], output_dir: str, state: ProcessingState) -> None:
    """Process a batch of PDF files"""
    for pdf_file in files:
        retry_count = state.failed_files.get(pdf_file, 0)
        if retry_count >= MAX_RETRIES:
            logging.error(f"Max retries reached for {pdf_file}, skipping")
            continue
            
        if extract_text_from_pdf(pdf_file, output_dir, state):
            state.failed_files.pop(pdf_file, None)
        else:
            state.failed_files[pdf_file] = retry_count + 1
            state.save()

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Robustly extract text from PDF files in a directory.")
    parser.add_argument('input_dir', nargs='?', default='original_files', 
                        help='Directory containing the PDF files to process (default: original_files)')
    parser.add_argument('output_dir', nargs='?', default='extracted_text', 
                        help='Directory to save the extracted text files (default: extracted_text)')
    
    args = parser.parse_args()

    # Use parsed arguments for directories
    input_dir = args.input_dir
    output_dir = args.output_dir
    
    # Ensure directories exist
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # Load or create processing state
    state = ProcessingState.load()
    if not state.start_time:
        state.start_time = datetime.now()
        state.save()
    
    # Get all PDF files
    all_pdf_files = get_pdf_files(input_dir)
    state.total_files = len(all_pdf_files)
    
    # Filter out already processed files
    remaining_files = [f for f in all_pdf_files if f not in state.processed_files]
    
    if not remaining_files:
        logging.info("No new files to process")
        return
    
    # Log based on whether resuming or starting fresh
    if state.processed_count > 0:
        logging.info(f"Found {state.total_files} total files. Resuming processing. {state.processed_count} files already processed, {len(remaining_files)} remaining.")
    else:
        logging.info(f"Found {state.total_files} files to process.")
    
    # Process files in batches
    for i in range(0, len(remaining_files), BATCH_SIZE):
        batch = remaining_files[i:i + BATCH_SIZE]
        state.current_batch = batch
        state.save()
        
        process_batch(batch, output_dir, state)
        
        # Clean up after each batch
        gc.collect()
        cleanup_temp_files()
        log_memory_usage()
        log_disk_usage()
        
        # Small delay between batches
        time.sleep(1)
    
    # Final cleanup
    cleanup_temp_files()
    
    # Log final statistics
    duration = datetime.now() - state.start_time
    logging.info(f"Processing complete. Duration: {duration}")
    logging.info(f"Successfully processed {state.processed_count} out of {state.total_files} files")
    if state.failed_files:
        logging.warning(f"Failed files: {len(state.failed_files)}")
        for file, retries in state.failed_files.items():
            logging.warning(f"  {file}: {retries} retries")

def signal_handler(signum, frame):
    """Handle interruption signals"""
    logging.info(f"Received signal {signum}, saving state and exiting gracefully...")
    # Deregister the cleanup function to prevent it from running on exit
    atexit.unregister(cleanup_temp_files)
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Register cleanup function
    atexit.register(cleanup_temp_files)
    
    main() 
