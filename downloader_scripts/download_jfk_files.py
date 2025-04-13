import csv
import os
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, unquote, quote
from tqdm.auto import tqdm
import argparse # Import argparse

# --- Configuration ---
# Removed INPUT_CSV_FILE and DOWNLOAD_ROOT_DIR constants
BASE_URL_PREFIX = 'https://www.archives.gov/files/research/jfk/'
MAX_WORKERS = 10  # Number of parallel download threads (Default, can be overridden by args)
CHUNK_SIZE = 8192 # Download chunk size in bytes
CONNECT_TIMEOUT = 10 # Seconds to wait for server connection
READ_TIMEOUT = 60   # Seconds to wait for server response during download
MAX_RETRIES = 3 # Number of retries for failed downloads
RETRY_DELAY = 5 # Seconds to wait before retrying
# --- End Configuration ---

# --- Helper Functions ---

def correct_and_parse_url(url_string):
    """Corrects URL encoding, parses, and extracts components."""
    try:
        # Replace spaces and # before general quoting for robustness
        temp_url = url_string.replace(' ', '%20').replace('#', '%23')

        # More robust quoting using urllib
        parsed = urlparse(temp_url)
        # Quote the path component, keeping slashes safe
        path_quoted = quote(unquote(parsed.path), safe='/') # Decode first in case it's partially encoded

        corrected_url = parsed._replace(path=path_quoted).geturl()

        if not corrected_url.startswith(BASE_URL_PREFIX):
            print(f"Warning: URL does not start with expected prefix: {url_string}")
            return None, None, None

        relative_path_encoded = corrected_url[len(BASE_URL_PREFIX):]
        if not relative_path_encoded:
             print(f"Warning: Could not determine relative path for URL: {url_string}")
             return None, None, None

        # Extract directory part and decoded filename
        relative_dir_encoded = os.path.dirname(relative_path_encoded)
        filename_encoded = os.path.basename(relative_path_encoded)

        # Decode directory and filename for local path creation
        relative_dir_decoded = unquote(relative_dir_encoded)
        filename_decoded = unquote(filename_encoded)

        # Handle potential empty filenames after decoding
        if not filename_decoded:
             print(f"Warning: Empty filename after decoding URL: {url_string}")
             return None, None, None

        return corrected_url, relative_dir_decoded, filename_decoded

    except Exception as e:
        print(f"Error parsing URL {url_string}: {e}")
        return None, None, None

def get_remote_file_size(url):
    """Gets the remote file size using a HEAD request."""
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.head(url, timeout=CONNECT_TIMEOUT, allow_redirects=True)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            size = int(response.headers.get('content-length', 0))
            return size
        except requests.exceptions.Timeout:
             print(f"Timeout getting size for {url} (Attempt {attempt + 1}/{MAX_RETRIES})")
             if attempt < MAX_RETRIES - 1: time.sleep(RETRY_DELAY)
        except requests.exceptions.RequestException as e:
            print(f"Error getting size for {url}: {e} (Attempt {attempt + 1}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES - 1: time.sleep(RETRY_DELAY)
            else: return None # Return None after max retries
    return None


def download_file(url_info, download_root_dir, pbar_files):
    """Downloads a single file with error handling and retries."""
    original_url, corrected_url, relative_dir, filename = url_info

    if not corrected_url:
        return original_url, "Skipped (URL parse error)"

    target_dir = os.path.join(download_root_dir, relative_dir)
    target_path = os.path.join(target_dir, filename)

    status = "Unknown Error"
    downloaded_bytes = 0

    for attempt in range(MAX_RETRIES):
        try:
            # Ensure target directory exists
            os.makedirs(target_dir, exist_ok=True)

            remote_size = get_remote_file_size(corrected_url)

            # Check if file exists and is complete
            if os.path.exists(target_path):
                local_size = os.path.getsize(target_path)
                if remote_size is not None and local_size == remote_size and remote_size > 0:
                    status = f"Skipped (Already Exists - {local_size} bytes)"
                    pbar_files.update(1) # Update overall file progress bar
                    return original_url, status
                else:
                    # print(f"File {target_path} exists but size mismatch (local={local_size}, remote={remote_size}). Re-downloading.")
                    pass # Proceed to download/overwrite

            # Download the file
            response = requests.get(corrected_url, stream=True, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
            response.raise_for_status()

            actual_remote_size = int(response.headers.get('content-length', 0)) # Get size from GET request header too

            with open(target_path, 'wb') as f, tqdm.wrapattr(f, "write",
                                                              unit='B', unit_scale=True, unit_divisor=1024,
                                                              total=actual_remote_size,
                                                              desc=f"{filename[:30]:<30}", # Show truncated filename
                                                              leave=False, # Don't leave individual bars when done
                                                              miniters=1) as file_out:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk: # filter out keep-alive new chunks
                        file_out.write(chunk)
                        downloaded_bytes = file_out.tell()


            # Final size check after download
            local_size_after = os.path.getsize(target_path)
            if actual_remote_size > 0 and local_size_after != actual_remote_size:
                 raise IOError(f"Incomplete download: local size {local_size_after} != remote size {actual_remote_size}")

            status = f"Success ({local_size_after} bytes)"
            pbar_files.update(1)
            return original_url, status # Success

        except requests.exceptions.Timeout:
            status = f"Timeout (Attempt {attempt + 1}/{MAX_RETRIES})"
            print(f"{status} downloading {corrected_url}")
        except requests.exceptions.RequestException as e:
            status = f"Request Error: {e} (Attempt {attempt + 1}/{MAX_RETRIES})"
            print(f"{status} downloading {corrected_url}")
        except IOError as e:
             status = f"IO Error: {e} (Attempt {attempt + 1}/{MAX_RETRIES})"
             print(f"{status} saving {target_path}")
             # Attempt to delete potentially corrupted file
             try:
                 if os.path.exists(target_path): os.remove(target_path)
             except OSError: pass
        except Exception as e:
             status = f"Unexpected Error: {e} (Attempt {attempt + 1}/{MAX_RETRIES})"
             print(f"{status} processing {corrected_url}")

        # Wait before retrying if not the last attempt
        if attempt < MAX_RETRIES - 1:
            print(f"Retrying in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)

    pbar_files.update(1) # Ensure progress bar advances even on failure
    return original_url, f"Failed ({status})"

# --- Main Execution ---
if __name__ == "__main__":
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(
        description="Download files listed in a CSV from the JFK Assassination Records Archive.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter # Show defaults in help
    )
    parser.add_argument(
        "input_csv",
        help="Path to the input CSV file (must have URL in the second column)."
    )
    parser.add_argument(
        "output_dir",
        help="Path to the root directory where files will be downloaded."
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=MAX_WORKERS,
        help="Number of parallel download threads."
    )
    # Add other arguments if needed, e.g., for timeouts, retries
    args = parser.parse_args()
    # --- End Argument Parsing ---

    # Use arguments instead of constants
    input_csv_path = args.input_csv
    download_root_path = args.output_dir
    num_workers = args.workers

    print(f"Starting download process...")
    print(f"Reading input CSV: {input_csv_path}")
    print(f"Saving files to: {download_root_path}")
    print(f"Using max {num_workers} parallel downloads.")

    download_tasks = []
    processed_urls = set()
    skipped_invalid_urls = 0

    # Read CSV and prepare unique tasks
    try:
        with open(input_csv_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            try:
                header = next(reader) # Skip header
            except StopIteration:
                 print(f"Error: Input CSV file '{input_csv_path}' is empty or has no header.")
                 exit()

            print("Parsing URLs and preparing download tasks...")
            for i, row in enumerate(tqdm(reader, desc="Reading CSV")):
                if len(row) >= 2:
                    original_url = row[1].strip()
                    if not original_url:
                        # print(f"Skipping row {i+2}: Empty URL")
                        continue

                    if original_url in processed_urls:
                        # print(f"Skipping row {i+2}: Duplicate URL {original_url}")
                        continue

                    corrected_url, relative_dir, filename = correct_and_parse_url(original_url)

                    if corrected_url and relative_dir is not None and filename:
                        download_tasks.append((original_url, corrected_url, relative_dir, filename))
                        processed_urls.add(original_url)
                    else:
                        # print(f"Skipping row {i+2}: Invalid or unparsable URL {original_url}")
                        skipped_invalid_urls += 1
                # else:
                    # print(f"Skipping row {i+2}: Insufficient columns")

    except FileNotFoundError:
        print(f"Error: Input CSV file not found at {input_csv_path}")
        exit()
    except Exception as e:
        print(f"Error reading CSV file '{input_csv_path}': {e}")
        exit()

    total_files = len(download_tasks)
    print(f"Found {total_files} unique, valid URLs to download.")
    if skipped_invalid_urls > 0:
        print(f"Skipped {skipped_invalid_urls} invalid or unparsable URLs.")

    if total_files == 0:
        print("No files to download.")
        exit()

    success_count = 0
    failed_count = 0
    skipped_count = 0
    error_log = []

    print(f"Starting downloads with {min(num_workers, total_files)} workers...")

    # Initialize overall progress bar
    with tqdm(total=total_files, desc="Overall Progress", unit="file") as pbar_files:
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Submit tasks
            futures = {executor.submit(download_file, task, download_root_path, pbar_files): task for task in download_tasks}

            # Process results as they complete
            for future in as_completed(futures):
                original_url = futures[future][0] # Get original URL from task info
                try:
                    _, status = future.result()
                    if status.startswith("Success"):
                        success_count += 1
                    elif status.startswith("Skipped"):
                        skipped_count += 1
                    else:
                        failed_count += 1
                        error_log.append(f"{original_url}: {status}")
                except Exception as e:
                    failed_count += 1
                    status = f"Execution Error: {e}"
                    error_log.append(f"{original_url}: {status}")
                    print(f"Critical error processing task for {original_url}: {e}")
                # pbar_files reflects completed tasks regardless of success/failure

    print("\n--- Download Summary ---")
    print(f"Total Unique URLs: {total_files}")
    print(f"Successful Downloads: {success_count}")
    print(f"Skipped (Already Exists): {skipped_count}")
    print(f"Failed Downloads: {failed_count}")

    if error_log:
        print("\n--- Failed URLs ---")
        for entry in error_log:
            print(entry)
        # Optionally write errors to a file
        # with open('download_errors.log', 'w') as f:
        #     for entry in error_log:
        #         f.write(f"{entry}\n")
        # print("\nFailed URLs logged to download_errors.log")

    print("\nDownload process finished.") 