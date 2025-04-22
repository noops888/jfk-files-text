# apple_vision_pdf_to_text_parallel_v2.py
import os
import subprocess
import argparse
from Cocoa import NSURL, NSData, NSBitmapImageRep
import Vision
import concurrent.futures
import time
import logging
import sys
import traceback
from tqdm import tqdm # For progress bar
import shutil
import glob # For cleaning up tmp files
import signal # For signal handling

# --- Logging Setup ---
# Note: Logging configuration should ideally happen once, in the main part of the script.
# However, for multiprocessing, child processes might need some logger access or configuration.
# Here we set up a basic logger. More complex setups might pass logger configurations.
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(processName)s - %(message)s')
log_file = 'ocr_run.log'

# File Handler for detailed logs
file_handler = logging.FileHandler(log_file, mode='a') # Append mode
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO) # Log info and above to file

# Stream Handler for console output (less verbose)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s')) # Simpler format for console
stream_handler.setLevel(logging.WARNING) # Show warnings and errors on console by default

logger = logging.getLogger()
logger.setLevel(logging.INFO) # Root logger level
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# --- Functions ---

def pdf_to_images(pdf_path):
    """Converts a PDF page to PNG images using pdftoppm."""
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    # Use a unique temp dir per PDF, potentially including PID if contention is suspected
    temp_dir = f"/tmp/pdf_ocr_{base_name}_{os.getpid()}/"
    os.makedirs(temp_dir, exist_ok=True)
    logger.info(f"[{base_name}] Creating temp directory: {temp_dir}")

    try:
        # Increased resolution for potentially better OCR
        command = ["pdftoppm", "-png", "-r", "300", pdf_path, os.path.join(temp_dir, "page")]
        logger.info(f"[{base_name}] Running pdftoppm: {' '.join(command)}")
        # Add timeout (e.g., 60 seconds) to prevent hangs on corrupted PDFs
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=60)
        logger.debug(f"[{base_name}] pdftoppm stdout: {result.stdout}")
        if result.stderr:
            logger.warning(f"[{base_name}] pdftoppm stderr: {result.stderr}")

    except subprocess.TimeoutExpired:
        logger.error(f"[{base_name}] pdftoppm command timed out after 60 seconds.")
        # Cleanup timed-out conversion attempt
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        return [], None # Indicate failure
    except subprocess.CalledProcessError as e:
        logger.error(f"[{base_name}] Error running pdftoppm: {e.stderr}")
        # Cleanup failed conversion attempt
        if os.path.exists(temp_dir):
            subprocess.run(["rm", "-rf", temp_dir], check=False)
        return [], None # Indicate failure
    except FileNotFoundError:
        logger.error("Fatal: 'pdftoppm' command not found. Please install poppler (brew install poppler).")
        # No point continuing if pdftoppm isn't there. We can't raise easily across processes.
        # Returning empty list will stop processing for this PDF. Main process should check for errors.
        return [], None

    try:
        image_files = sorted([
            os.path.join(temp_dir, f)
            for f in os.listdir(temp_dir) if f.lower().endswith(".png")
        ])
        logger.info(f"[{base_name}] Found {len(image_files)} images in {temp_dir}")
        return image_files, temp_dir # Return temp_dir path back
    except Exception as e:
        logger.error(f"[{base_name}] Error listing/accessing images in {temp_dir}: {e}")
        logger.debug(traceback.format_exc())
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as cleanup_error:
                logger.warning(f"[{base_name}] Failed initial cleanup of {temp_dir}: {cleanup_error}")
        return [], None # Indicate failure and no temp dir


def ocr_image(image_path):
    """Performs OCR on a single image using Apple Vision."""
    page_num = os.path.basename(image_path).split('-')[-1].split('.')[0] # Extract page number roughly
    try:
        # logger.debug(f"Starting OCR for page {page_num} ({os.path.basename(image_path)})...")
        image_url = NSURL.fileURLWithPath_(image_path)
        image_data = NSData.dataWithContentsOfURL_(image_url)
        # Check if data loaded successfully AND has non-zero length
        if not image_data or image_data.length() == 0:
            logger.error(f"Page {page_num}: Failed to load NSData or data is empty from {image_path}")
            return []

        image_rep = NSBitmapImageRep.imageRepWithData_(image_data)
        if not image_rep:
            logger.error(f"Page {page_num}: Failed to create NSBitmapImageRep for {image_path}")
            return []

        cg_image = image_rep.CGImage()
        if not cg_image:
            logger.error(f"Page {page_num}: Failed to get CGImage for {image_path}")
            return []

        request = Vision.VNRecognizeTextRequest.alloc().init()
        request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
        request.setUsesLanguageCorrection_(True)

        handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, None)
        success, error = handler.performRequests_error_([request], None)

        if not success:
            # Convert NSError to string for logging
            error_str = str(error.localizedDescription()) if error else "Unknown Vision Error"
            logger.error(f"Page {page_num}: OCR failed for {image_path}. Error: {error_str}")
            # Log more details if available (domain, code)
            if error:
                logger.error(f"    Error Domain: {error.domain()}, Code: {error.code()}")
                user_info = error.userInfo()
                if user_info:
                    logger.error(f"    User Info: {user_info}")
            return []

        text_blocks = []
        results = request.results()
        if results:
             for observation in results:
                 top_candidate = observation.topCandidates_(1)
                 if top_candidate:
                     text_blocks.append(top_candidate[0].string())
        # logger.debug(f"Finished OCR for page {page_num}. Found {len(text_blocks)} text blocks.")
        return text_blocks

    except KeyboardInterrupt:
        # Allow KeyboardInterrupt to propagate for shutdown handling
        raise
    except Exception as e:
        # Log other unexpected errors during OCR
        logger.error(f"Page {page_num}: Unexpected error during OCR for {image_path}: {e}")
        logger.debug(traceback.format_exc()) # Log traceback for unexpected errors
        return []


def process_pdf(pdf_path, output_dir, force_overwrite):
    """
    Processes a single PDF: checks existence, converts to images, OCRs pages, writes Markdown.
    Returns:
        str: PDF path on success or skipped.
        None: On critical error during processing.
    """
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}.md")
    # REVERTING: Write directly to output_path, remove temp file logic for diagnosis
    temp_dir_to_remove = None # Initialize

    # --- Check for existing FINAL output ---
    if os.path.exists(output_path) and not force_overwrite:
        logger.info(f"[{base_name}] Final output file already exists, skipping: {output_path}")
        return pdf_path # Indicate skipped, not an error

    # --- Cleanup potential leftover temp file from previous crash ---
    if os.path.exists(output_path):
        logger.warning(f"[{base_name}] Found stale output file, deleting: {output_path}")
        try:
            os.remove(output_path)
        except OSError as e:
            logger.error(f"[{base_name}] Failed to delete stale output file {output_path}: {e}")
            # Decide if this is fatal? Probably okay to continue and overwrite.

    logger.info(f"-> Processing: {base_name} (PID: {os.getpid()})") # Simplified log message
    start_time_pdf = time.time()

    try:
        # --- Convert PDF to Images ---
        images, temp_dir_to_remove = pdf_to_images(pdf_path) # Get temp_dir path back
        if not images:
            logger.warning(f"[{base_name}] No images generated or pdftoppm failed. Cannot OCR.")
            # pdf_to_images should handle its own temp dir cleanup on failure
            return None # Indicate failure for this PDF

        # --- OCR Images and Write to TEMPORARY Output ---
        # REVERTING: Write directly to final output path
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# {base_name}\n\n")
            page_count = len(images)
            for idx, img_path in enumerate(images, 1):
                page_start_time = time.time()
                text_blocks = ocr_image(img_path)
                page_end_time = time.time()

                if text_blocks:
                    f.write(f"## Page {idx}\n\n")
                    f.write("\n\n".join(text_blocks))
                    f.write("\n\n---\n\n")
                else:
                    logger.warning(f"[{base_name}] No text found for page {idx} of {page_count}.")
                    f.write(f"## Page {idx}\n\n*No text recognized on this page.*\n\n---\n\n")
                    # NOTE: No longer copying error images for simplicity

        end_time_pdf = time.time()
        logger.info(f"<- Finished: {base_name} in {end_time_pdf - start_time_pdf:.2f}s")
        return pdf_path # Indicate success

    except Exception as e:
        logger.error(f"!!! UNHANDLED error processing {base_name} ({pdf_path}): {e}")
        logger.error(traceback.format_exc()) # Log full traceback to file
        return None # Indicate failure

    finally:
        # Cleanup: Ensure temporary directory is removed if it exists
        if temp_dir_to_remove and os.path.exists(temp_dir_to_remove):
             logger.info(f"[{base_name}] Cleaning up temp directory: {temp_dir_to_remove}")
             try: # Use shutil.rmtree
                 shutil.rmtree(temp_dir_to_remove)
             except Exception as cleanup_error:
                 logger.warning(f"[{base_name}] Failed to remove temp directory {temp_dir_to_remove}: {cleanup_error}")

        # REVERTING: No temp output file to clean up


def main():
    # --- Architecture Check ---
    # --- Signal Handler for graceful exit attempts ---
    original_sigint_handler = signal.getsignal(signal.SIGINT)
    shutdown_flag = [False] # Use a list to make it mutable for the handler

    def signal_handler(sig, frame):
        nonlocal shutdown_flag
        # Revert to two-stage interrupt
        if shutdown_flag[0]:
             print("\nForce exiting after second Ctrl+C...", file=sys.stderr)
             # Restore original handler and re-raise to force exit
             signal.signal(signal.SIGINT, original_sigint_handler)
             raise KeyboardInterrupt
        else:
             print("\nCtrl+C detected! Attempting graceful shutdown... Press Ctrl+C again to force exit.", file=sys.stderr)
             logger.warning("SIGINT received, initiating shutdown.")
             shutdown_flag[0] = True

    signal.signal(signal.SIGINT, signal_handler)

    # NOTE: For best performance on Apple Silicon, ensure you are running this script
    # using a native ARM64 Python interpreter, not one running via Rosetta 2.
    # You can check with: python -c "import platform; print(platform.machine())"
    # It should output 'arm64'.

    parser = argparse.ArgumentParser(
        description="V2: Parallel PDF to Markdown OCR Converter using Apple Vision with logging and progress.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("input_dir", help="Directory containing PDF files")
    parser.add_argument("output_dir", help="Directory for Markdown output")
    parser.add_argument(
        "-w", "--workers", type=int, default=os.cpu_count(),
        help="Number of parallel processes (PDFs processed concurrently)"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Force overwrite of existing Markdown files."
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Show INFO level messages on console (in addition to file log)."
    )
    args = parser.parse_args()

    # Adjust console log level if verbose
    if args.verbose:
        stream_handler.setLevel(logging.INFO)

    logger.info("========================================================")
    logger.info(f"Script starting with args: {args}")
    logger.info(f"Using Python: {sys.executable} ({sys.version})")
    logger.info(f"Architecture: {platform.machine()}") # Added platform import needed
    logger.info(f"Output log file: {log_file}")


    # Check if pdftoppm exists before starting pool
    try:
        subprocess.run(["pdftoppm", "-v"], check=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        logger.error("Fatal: 'pdftoppm' command not found or not working. Please install poppler.")
        sys.exit(1)


    os.makedirs(args.output_dir, exist_ok=True)
    logger.info(f"Ensured output directory exists: {args.output_dir}")


    # --- Clean up any old .tmp files from previous crashes ---
    stale_tmp_files = glob.glob(os.path.join(args.output_dir, ".*.md.tmp"))
    if stale_tmp_files:
        logger.warning(f"Found {len(stale_tmp_files)} stale .tmp files from previous runs. Cleaning up...")
        for tmp_file in stale_tmp_files:
            try:
                os.remove(tmp_file)
                logger.info(f"Removed stale temp file: {tmp_file}")
            except OSError as e:
                logger.error(f"Failed to remove stale temp file {tmp_file}: {e}")


    try:
        all_files_in_input = os.listdir(args.input_dir)
    except FileNotFoundError:
        logger.error(f"Input directory not found: {args.input_dir}")
        sys.exit(1)


    pdf_files = sorted([
        os.path.join(args.input_dir, f)
        for f in all_files_in_input
        if f.lower().endswith('.pdf') and not f.startswith('.')
    ])


    if not pdf_files:
        logger.warning(f"No PDF files found in '{args.input_dir}'. Exiting.")
        return


    total_files = len(pdf_files)
    logger.info(f"Found {total_files} PDF files.")


    skipped_count = 0
    pdf_files_to_process = []
    if not args.force:
        # Pre-filter based on existing output files
        skipped_files_initial = []
        for pdf_path in pdf_files:
             base_name = os.path.splitext(os.path.basename(pdf_path))[0]
             output_path = os.path.join(args.output_dir, f"{base_name}.md")
             if os.path.exists(output_path):
                 skipped_files_initial.append(pdf_path)
             else:
                 pdf_files_to_process.append(pdf_path)
        skipped_count = len(skipped_files_initial)
        if skipped_count > 0:
            logger.info(f"Found {skipped_count} completed files (existing .md). Skipping them.")
        pdf_files = pdf_files_to_process # Reassign pdf_files to only those needing processing
    else:
        skipped_count = 0 # Forcing overwrite means no initial skips
        logger.info("Force overwrite enabled, processing all found files.")
        pdf_files_to_process = pdf_files # Process all


    total_files_to_process = len(pdf_files_to_process)


    # Console message summarizing plan BEFORE starting pool
    print(f"PDF Scan Complete: Found={total_files}, To Process={total_files_to_process}, Skipped={skipped_count}")


    if total_files_to_process == 0:
        logger.info("No files need processing.")
        # Exit cleanly if no work to do after skipping
        print("All PDFs already processed. Exiting.")
        return # Skip the pool execution entirely


    logger.info(f"Starting parallel processing with {args.workers} workers for {total_files_to_process} files...")
    start_time = time.time()


    processed_count_run = 0 # Counter for this run only
    error_count_run = 0     # Counter for this run only


    # REMOVING max_tasks_per_child for diagnosis
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
        # Revert to dictionary comprehension for futures
        futures = {
            executor.submit(process_pdf, pdf_path, args.output_dir, args.force): pdf_path
            for pdf_path in pdf_files_to_process
            # Add check here too? Might be less efficient than checking in the loop below
        }

        # Use tqdm for terminal progress bar
        # Wrap as_completed to show progress based on completed tasks
        if not futures: # Handle case where no tasks were submitted (all skipped or immediate interrupt)
            logger.warning("No tasks submitted to executor.")
            progress_bar = []
        else:
            results_iterator = concurrent.futures.as_completed(futures)
            # Use len(futures) for total as it reflects actual submitted tasks
            progress_bar = tqdm(results_iterator, total=len(futures), desc="Processing PDFs", unit="file", initial=0, file=sys.stderr)

        try:
            for future in progress_bar:
                pdf_path_submitted = futures[future]
                base_name_submitted = os.path.basename(pdf_path_submitted)
                try:
                    result = future.result() # result is pdf_path on success/skipped, None on error
                    if result is not None:
                        # Check if it was skipped or processed
                        output_path = os.path.join(args.output_dir, f"{os.path.splitext(base_name_submitted)[0]}.md")
                        if os.path.exists(output_path) and not args.force and result == pdf_path_submitted:
                             # This logic is tricky - we rely on the logger inside process_pdf now
                             # Let's count based on the return value primarily
                             # If process_pdf returned the path, it either succeeded or skipped
                             # We need a way to differentiate... let's refine process_pdf return
                             # --- REVISION: process_pdf returns status codes ---
                             # Let's adjust this later if needed. For now, assume path return means 'handled' (processed or skipped)
                             # and None means 'error'. We'll differentiate skipped in summary later.
                             processed_count_run += 1 # Treat skipped as handled for now in the counter
                        else:
                             processed_count_run += 1 # Explicitly processed
                    else:
                        # Error was caught and logged within process_pdf
                        error_count_run += 1
                        logger.warning(f"Task for {base_name_submitted} reported an error (check log).")

                except Exception as exc:
                    # Catch unexpected errors from the future/executor itself
                    error_count_run += 1
                    logger.error(f'!!! UNHANDLED EXCEPTION processing future for {base_name_submitted}: {exc}')
                    logger.error(traceback.format_exc())

                # Update progress description with current counts
                progress_bar.set_description(
                    f"Processing (Done:{processed_count_run}, Skip:{skipped_count}, Err:{error_count_run})"
                )

                # Check flag before getting result, allows quicker exit
                # (Note: With os._exit(), this loop likely won't be reached after Ctrl+C)
                if shutdown_flag[0]:
                    logger.warning("Shutdown flag detected, initiating executor shutdown (wait=False).")
                    # Initiate non-waiting shutdown immediately
                    executor.shutdown(wait=False)
                    break # Exit processing loop

        except KeyboardInterrupt:
            # Catch Ctrl+C if it happens directly in the loop iteration itself
            logger.warning("KeyboardInterrupt caught during main processing loop. Shutting down.")
            shutdown_flag[0] = True # Ensure flag is set
        finally:
            # Ensure progress bar is closed properly
            if 'progress_bar' in locals() and hasattr(progress_bar, 'close'):
                 progress_bar.close()
            # The executor shutdown is now handled earlier if shutdown_flag is set,
            # or implicitly by the __exit__ of the 'with' block if the loop completes naturally.
            # Still call shutdown(wait=False) here if flag is set, ensures it's called even if loop finishes early
            if shutdown_flag[0] and 'executor' in locals():
                 logger.warning("Graceful shutdown attempted. Executor was signalled to shutdown without waiting.")
                 logger.warning("If script hangs, unresponsive workers may require a second Ctrl+C.")
                 # Calling shutdown again here might be redundant if already called in loop, but safe
                 executor.shutdown(wait=False)


    end_time = time.time()
    total_time = end_time - start_time


    # --- Final Summary ---
    logger.info("\n--- Processing Summary ---")
    logger.info(f"Total PDF files found: {total_files}")
    logger.info(f"Files skipped (output existed): {skipped_count}")
    logger.info(f"Files attempted processing in this run: {total_files_to_process}")
    logger.info(f"Successfully processed in this run: {processed_count_run}")
    logger.info(f"Encountered errors in this run: {error_count_run}")
    logger.info(f"Total execution time: {total_time:.2f} seconds")
    logger.info(f"Output saved to: {args.output_dir}")
    logger.info(f"Log file saved to: {log_file}")
    logger.info("--------------------------\n")

    # Also print summary to console regardless of verbose level
    print("\n--- Processing Summary ---")
    print(f"Total PDF files found: {total_files}")
    print(f"Files skipped (output existed): {skipped_count}")
    print(f"Files attempted processing in this run: {total_files_to_process}")
    print(f"Successfully processed in this run: {processed_count_run}")
    print(f"Encountered errors in this run: {error_count_run}")
    print(f"Total execution time: {total_time:.2f} seconds")
    print(f"Output saved to: {args.output_dir}")
    print(f"Log file saved to: {log_file}")
    print("--------------------------\n")


if __name__ == "__main__":
    # Need platform import for architecture check
    import platform # Ensure platform is imported here for the main guard
    main() 