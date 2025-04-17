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
from typing import Dict, List, Optional, Tuple
import argparse
import concurrent.futures
import threading

# Set up logging with both file and console output
log_file = "pdf_processing_multithreaded.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

# Global state for crash recovery
PROGRESS_FILE = "processing_progress_multithreaded.json"
TEMP_DIR_BASE = "temp_processing_multithreaded"
MAX_RETRIES = 3

# Global flag to signal exit
exit_signal_received = threading.Event()

class ProcessingState:
    def __init__(self):
        self.processed_files: Dict[str, str] = {}  # filename -> md5 hash
        self.last_processed_file: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.total_files: int = 0
        self.processed_count: int = 0
        self.failed_files: Dict[str, int] = {}  # filename -> retry count
        self.lock = threading.Lock()

    def save(self):
        """Save current state to file (thread-safe)"""
        with self.lock:
            state_dict = {
                'processed_files': self.processed_files,
                'last_processed_file': self.last_processed_file,
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'total_files': self.total_files,
                'processed_count': self.processed_count,
                'failed_files': self.failed_files
            }
            try:
                with open(PROGRESS_FILE, 'w') as f:
                    json.dump(state_dict, f)
            except Exception as e:
                logging.error(f"Failed to save progress state: {e}")

    @classmethod
    def load(cls) -> 'ProcessingState':
        """Load state from file"""
        state = cls()
        if os.path.exists(PROGRESS_FILE):
            try:
                with open(PROGRESS_FILE, 'r') as f:
                    state_dict = json.load(f)
                    state.processed_files = state_dict.get('processed_files', {})
                    state.last_processed_file = state_dict.get('last_processed_file')
                    state.start_time = datetime.fromisoformat(state_dict['start_time']) if state_dict.get('start_time') else None
                    state.total_files = state_dict.get('total_files', 0)
                    state.processed_count = state_dict.get('processed_count', state.processed_files.__len__())
                    state.failed_files = state_dict.get('failed_files', {})
            except Exception as e:
                logging.error(f"Failed to load progress state from {PROGRESS_FILE}: {e}")
                state = cls()
        return state

    def update_success(self, pdf_path: str, file_hash: str):
        """Update state after successful processing (thread-safe)"""
        with self.lock:
            self.processed_files[pdf_path] = file_hash
            self.processed_count += 1
            self.failed_files.pop(pdf_path, None)
            self.last_processed_file = pdf_path
        self.save()

    def update_failure(self, pdf_path: str):
        """Update state after failed processing (thread-safe)"""
        with self.lock:
            retry_count = self.failed_files.get(pdf_path, 0)
            self.failed_files[pdf_path] = retry_count + 1
            self.last_processed_file = pdf_path
        self.save()

def calculate_file_hash(filepath: str) -> str:
    """Calculate MD5 hash of a file"""
    hash_md5 = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logging.error(f"Could not calculate hash for {filepath}: {e}")
        return ""

def log_memory_usage():
    """Log current memory usage"""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    logging.info(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")

def log_disk_usage():
    """Log disk usage"""
    try:
        disk = psutil.disk_usage('.')
        logging.info(f"Disk usage (current dir): {disk.percent}% (free: {disk.free / 1024 / 1024:.2f} MB)")
    except Exception as e:
        logging.warning(f"Could not get disk usage for current directory: {e}")

def cleanup_temp_dir(temp_dir_path: str):
    """Clean up a specific temporary directory"""
    if os.path.exists(temp_dir_path):
        logging.debug(f"Cleaning up temporary directory: {temp_dir_path}")
        try:
            shutil.rmtree(temp_dir_path)
        except Exception as e:
            logging.error(f"Error cleaning up temp directory {temp_dir_path}: {e}")

def cleanup_all_temp_files():
    """Clean up all temporary files managed by this script run"""
    if os.path.exists(TEMP_DIR_BASE):
        logging.info(f"Cleaning up base temporary directory: {TEMP_DIR_BASE}")
        try:
            shutil.rmtree(TEMP_DIR_BASE)
        except Exception as e:
            logging.error(f"Error cleaning up base temp directory {TEMP_DIR_BASE}: {e}")
    os.makedirs(TEMP_DIR_BASE, exist_ok=True)

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
    except Exception as e:
        logging.warning(f"Could not check completeness of {output_path}: {e}")
        return False

def extract_text_from_pdf(pdf_path: str, output_dir: str, tesseract_config: str, state: ProcessingState) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Extract text from a PDF file and save it as markdown. Designed for threaded execution.
    Returns: (status: 'success'|'skipped'|'failed', pdf_path, file_hash|error_message)
    """
    if exit_signal_received.is_set():
        logging.warning(f"Exit signal received, skipping {pdf_path}")
        return ('skipped', pdf_path, "Exit signal received")

    output_path = os.path.join(output_dir, f"{Path(pdf_path).stem}.md")
    temp_dir = os.path.join(TEMP_DIR_BASE, Path(pdf_path).stem)
    os.makedirs(temp_dir, exist_ok=True)

    with state.lock:
        is_processed = pdf_path in state.processed_files
        retry_count = state.failed_files.get(pdf_path, 0)

    if is_processed and is_file_complete(output_path):
        logging.info(f"Skipping already processed file: {pdf_path}")
        cleanup_temp_dir(temp_dir)
        return ('skipped', pdf_path, state.processed_files.get(pdf_path))

    if retry_count >= MAX_RETRIES:
        logging.error(f"Max retries ({MAX_RETRIES}) reached for {pdf_path}, skipping permanently.")
        cleanup_temp_dir(temp_dir)
        return ('failed', pdf_path, f"Max retries ({MAX_RETRIES}) reached")

    try:
        total_pages = get_pdf_page_count(pdf_path)
        if total_pages == 0:
            logging.error(f"Could not determine page count for {pdf_path}. Retries: {retry_count}")
            cleanup_temp_dir(temp_dir)
            return ('failed', pdf_path, "Could not get page count")

        logging.info(f"Processing PDF ({total_pages} pages): {pdf_path} [Retry {retry_count}]")

        existing_pages = set()
        if os.path.exists(temp_dir):
            for file in os.listdir(temp_dir):
                if file.startswith('page_') and file.endswith('.txt'):
                    try:
                        page_num = int(file.split('_')[1].split('.')[0])
                        existing_pages.add(page_num)
                    except (ValueError, IndexError):
                        continue

        extracted_text = [""] * total_pages
        page_processing_failed = False

        for page_num in range(1, total_pages + 1):
            if exit_signal_received.is_set():
                raise InterruptedError("Exit signal received during page processing")

            page_output_path = os.path.join(temp_dir, f'page_{page_num}.txt')

            if page_num in existing_pages and os.path.exists(page_output_path):
                logging.debug(f"Loading existing page {page_num}/{total_pages} from {pdf_path}")
                try:
                    with open(page_output_path, 'r', encoding='utf-8') as f:
                        extracted_text[page_num-1] = f.read()
                    continue
                except Exception as e:
                    logging.warning(f"Failed to read existing page {page_num} for {pdf_path}: {e}, reprocessing.")
                    existing_pages.remove(page_num)

            logging.info(f"Processing page {page_num}/{total_pages} for {pdf_path}")

            page_image = None
            try:
                images = convert_from_path(
                    pdf_path,
                    first_page=page_num,
                    last_page=page_num,
                    thread_count=1,
                    dpi=300,
                    grayscale=True,
                )
                if not images:
                    raise ValueError(f"pdf2image returned no image for page {page_num}")

                page_image = images[0]
                text = pytesseract.image_to_string(page_image, config=tesseract_config)
                extracted_text[page_num-1] = text

                with open(page_output_path, 'w', encoding='utf-8') as f:
                    f.write(text)

            except Exception as page_e:
                logging.error(f"Error processing page {page_num} of {pdf_path}: {page_e}")
                page_processing_failed = True
                extracted_text[page_num-1] = f"[[ERROR PROCESSING PAGE {page_num}: {page_e}]]"

            finally:
                if page_image:
                    page_image.close()
                del images
                gc.collect()

        if page_processing_failed:
            logging.warning(f"Some pages failed processing for {pdf_path}. Output will contain error markers.")

        file_stem = Path(pdf_path).stem
        full_text_parts = [f"# {file_stem}\n\n"]
        for page_num_one_indexed, page_content in enumerate(extracted_text, 1):
            full_text_parts.append(f"## Page {page_num_one_indexed}\n\n{page_content.strip()}\n\n")
        full_text = "".join(full_text_parts)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_text)

        file_hash = calculate_file_hash(pdf_path)
        if not file_hash:
            raise ValueError("Failed to calculate final file hash")

        logging.info(f"Successfully extracted text to {output_path}")
        cleanup_temp_dir(temp_dir)
        return ('success', pdf_path, file_hash)

    except InterruptedError as ie:
        logging.warning(f"Processing interrupted for {pdf_path}: {ie}")
        cleanup_temp_dir(temp_dir)
        return ('failed', pdf_path, str(ie))
    except Exception as e:
        logging.error(f"Error processing {pdf_path}: {e}", exc_info=True)
        if os.path.exists(output_path):
            try:
                logging.warning(f"Output file {output_path} might exist despite failure.")
                pass
            except Exception as del_e:
                logging.warning(f"Failed attempt to check/delete incomplete file {output_path}: {del_e}")
        cleanup_temp_dir(temp_dir)
        return ('failed', pdf_path, str(e))
    finally:
        gc.collect()

def get_pdf_files(directory: str) -> List[str]:
    """Get all PDF files from directory, case insensitive."""
    pdf_files = []
    try:
        for file in os.listdir(directory):
            if file.lower().endswith('.pdf'):
                full_path = os.path.join(directory, file)
                if os.path.isfile(full_path):
                    pdf_files.append(full_path)
    except FileNotFoundError:
        logging.error(f"Input directory not found: {directory}")
        return []
    except Exception as e:
        logging.error(f"Error listing PDF files in {directory}: {e}")
        return []
    return sorted(pdf_files)

def main():
    parser = argparse.ArgumentParser(description="Robustly extract text from PDF files in a directory using multiple threads.")
    parser.add_argument('input_dir', nargs='?', default='original_files',
                        help='Directory containing PDF files (default: original_files)')
    parser.add_argument('output_dir', nargs='?', default='extracted_text',
                        help='Directory to save extracted text files (default: extracted_text)')
    parser.add_argument('--threads', type=int, default=1,
                        help='Number of worker threads to use (default: 1)')

    args = parser.parse_args()

    input_dir = args.input_dir
    output_dir = args.output_dir
    num_threads = max(1, args.threads)

    tesseract_config = '-l eng+spa+rus+deu+fra+ita+bul --oem 1 --psm 1'
    logging.info(f"Using Tesseract config: {tesseract_config}")
    logging.info(f"Using {num_threads} worker threads.")

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(TEMP_DIR_BASE, exist_ok=True)

    state = ProcessingState.load()
    if not state.start_time:
        state.start_time = datetime.now()

    all_pdf_files = get_pdf_files(input_dir)
    if not all_pdf_files:
        logging.info("No PDF files found in input directory. Exiting.")
        return

    with state.lock:
        state.total_files = len(all_pdf_files)
        files_to_process = [
            f for f in all_pdf_files
            if not (
                f in state.processed_files and is_file_complete(os.path.join(output_dir, f"{Path(f).stem}.md"))
            ) and state.failed_files.get(f, 0) < MAX_RETRIES
        ]
        initial_processed_count = state.processed_count
        initial_failed_count = len(state.failed_files)

    if not files_to_process:
        logging.info("No new or failed files need processing based on progress file.")
        logging.info(f"Total files found: {state.total_files}, Already processed: {initial_processed_count}")
        return

    logging.info(f"Found {state.total_files} total files.")
    logging.info(f"Attempting to process {len(files_to_process)} files ({initial_processed_count} already processed, {initial_failed_count} previously failed).")

    processed_count_session = 0
    failed_count_session = 0
    skipped_count_session = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads, thread_name_prefix='PDFWorker') as executor:
        future_to_pdf = {executor.submit(extract_text_from_pdf, pdf_file, output_dir, tesseract_config, state): pdf_file for pdf_file in files_to_process}
        logging.info(f"Submitted {len(future_to_pdf)} tasks to thread pool.")

        try:
            for future in tqdm(concurrent.futures.as_completed(future_to_pdf), total=len(files_to_process), desc="Processing PDFs"):
                if exit_signal_received.is_set():
                    logging.info("Exit signal detected, attempting to cancel remaining tasks...")
                    for f in future_to_pdf:
                        if not f.done():
                            f.cancel()
                    break

                pdf_file = future_to_pdf[future]
                try:
                    status, path, result_data = future.result()

                    if status == 'success':
                        processed_count_session += 1
                        file_hash = result_data
                        state.update_success(path, file_hash)
                        logging.debug(f"Successfully processed: {path}")
                    elif status == 'failed':
                        failed_count_session += 1
                        error_message = result_data
                        state.update_failure(path)
                        logging.warning(f"Failed processing: {path} - {error_message}")
                    elif status == 'skipped':
                        skipped_count_session += 1
                        reason = result_data
                        logging.debug(f"Skipped: {path} - {reason}")
                    else:
                        logging.error(f"Unknown status '{status}' received for {path}")
                        failed_count_session += 1
                        state.update_failure(path)

                except concurrent.futures.CancelledError:
                    logging.warning(f"Task cancelled for {pdf_file}")
                    state.update_failure(pdf_file)
                    failed_count_session += 1
                except Exception as exc:
                    failed_count_session += 1
                    logging.error(f"Exception processing result for {pdf_file}: {exc}", exc_info=True)
                    state.update_failure(pdf_file)

        except KeyboardInterrupt:
            logging.info("KeyboardInterrupt received, signalling threads to exit...")
            exit_signal_received.set()

        finally:
            logging.info("Saving final state...")
            state.save()

    logging.info("="*20 + " Processing Summary " + "="*20)
    if state.start_time:
        duration = datetime.now() - state.start_time
        logging.info(f"Total processing duration: {duration}")

    logging.info(f"Files processed this session: {processed_count_session}")
    logging.info(f"Files failed this session: {failed_count_session}")
    logging.info(f"Files skipped this session (already done or interrupted): {skipped_count_session}")

    with state.lock:
        final_processed_count = state.processed_count
        final_failed_files = state.failed_files.copy()
        final_total_files = state.total_files

    logging.info(f"Total files processed successfully (cumulative): {final_processed_count} / {final_total_files}")
    if final_failed_files:
        failed_permanently = {f: r for f, r in final_failed_files.items() if r >= MAX_RETRIES}
        failed_retriable = {f: r for f, r in final_failed_files.items() if r < MAX_RETRIES}
        logging.warning(f"Total failed files (cumulative, retriable): {len(failed_retriable)}")
        if failed_retriable:
            for file, retries in list(failed_retriable.items())[:5]:
                logging.warning(f"  - {file}: {retries} retries")
            if len(failed_retriable) > 5: logging.warning("  ...")
        logging.error(f"Total failed files (cumulative, max retries reached): {len(failed_permanently)}")
        if failed_permanently:
            for file, retries in list(failed_permanently.items())[:5]:
                logging.error(f"  - {file}: {retries} retries (will not retry)")
            if len(failed_permanently) > 5: logging.error("  ...")

def signal_handler(signum, frame):
    """Handle interruption signals gracefully"""
    if not exit_signal_received.is_set():
        logging.info(f"Received signal {signum}, signalling threads to stop gracefully...")
        exit_signal_received.set()
    else:
        logging.warning("Multiple exit signals received, forcing exit.")
        sys.exit(1)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    main()
    logging.info("Script finished.") 
