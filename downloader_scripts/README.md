# JFK Assassination Records Archive - Download Utilities

This repository contains Python scripts to help process and download files from the National Archives' JFK Assassination Records Releases.

Specifically, it helps extract file links from the index spreadsheets provided by NARA and then download the corresponding files while preserving the intended directory structure.

## Scripts

1.  **`generate_link_csv.py`**: Extracts file links from NARA's Excel index files (`.xlsx`) into a simple CSV format.
2.  **`download_jfk_files.py`**: Downloads files listed in a CSV file, preserving the relative path structure and handling duplicates/errors.

## Prerequisites

*   Python 3.7+
*   Required Python libraries (see `requirements.txt`)
*   The NARA JFK Assassination Records index files (`.xlsx`) or pre-formatted CSV files containing the download URLs.

## Setup

1.  **Clone the repository (Optional):**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```
    *(Or simply ensure the Python scripts and your data files are in the same working directory)*

2.  **Create a virtual environment (Recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage Workflow

Here's the typical workflow for processing a NARA release spreadsheet:

**Step 1: Extract Links from Excel to CSV**

Use `generate_link_csv.py` to create a downloader-compatible CSV from the NARA Excel file. You need to specify the input Excel file, the desired output CSV name, and potentially the column containing the links (if it's not Column A).

*Example for 2017-2018 (Links in Column A):*
```bash
python generate_link_csv.py \
  national-archives-jfk-assassination-records-2017-2018-release.xlsx \
  jfk_archive_2017-2018_urls.csv
```

*Example for 2021 (Links in Column B):*
```bash
python generate_link_csv.py \
  national-archives-jfk-assassination-records-2021-release.xlsx \
  jfk_archive_2021_urls.csv \
  --column B
```

*(Repeat for other years as needed, adjusting the `--column` flag if necessary.)*


**Step 2: Download Files**

Use `download_jfk_files.py`, providing the CSV generated in Step 1 or 2 and the desired root directory for downloads.

*Example downloading from the 2017-2018 CSV into `./jfk_downloads`:*
```bash
python download_jfk_files.py \
  jfk_archive_2017-2018_urls.csv \
  ./jfk_downloads
```

## Notes

*   The download script (`download_jfk_files.py`) checks for existing files and compares file sizes. If a local file exists and matches the size reported by the server (via a `HEAD` request), it will be skipped. This allows the script to be stopped and restarted.
*   If a local file exists but the size is different, or if the remote size cannot be determined, the script will re-download and overwrite the local file.
*   Failed downloads are logged to the console at the end of the process.
*   The scripts expect URLs to follow the pattern `https://www.archives.gov/files/research/jfk/...`. The path structure following this prefix is recreated locally within the specified output directory.
*   Filesystem case sensitivity: The scripts save files using the casing derived from the URL path. On case-insensitive filesystems like default macOS, `File.pdf` and `file.pdf` might be treated as the same file if they are in the same directory, but the downloader saves them using the case provided by the URL.
