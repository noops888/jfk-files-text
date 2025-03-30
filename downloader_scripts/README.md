# JFK Files Downloader Scripts

This repository contains a collection of Python scripts designed to download the JFK assassination records from the National Archives website. Due to varying web page structures and Excel file formats across different release years, separate scripts were developed to handle each release period.

## Source

All JFK assassination records are available at: https://www.archives.gov/research/jfk

## Requirements

- Python 3.x
- Dependencies listed in `requirements.txt`

Install dependencies using:
```bash
pip install -r requirements.txt
```

## Available Scripts

### jfk-2017-2018-downloader.py
Downloads files from the 2017-2018 release using Excel file data.
```bash
python jfk-2017-2018-downloader.py [excel_file] [--threads N] [--test]
```
- `excel_file`: Path to the Excel file containing file information
- `--threads N`: Number of concurrent download threads (default: 4)
- `--test`: Run in test mode without actual downloads

### jfk-2021-downloader.py
Downloads files from the 2021 release.
```bash
python jfk-2021-downloader.py [excel_file] [--threads N] [--test]
```

### jfk-2025-pdf-downloader.py
Downloads and merges PDF files from the 2025 release.
```bash
python jfk-2025-pdf-downloader.py
```

### jfk-recover-missing.py
Recovers any missing files from previous downloads.
```bash
python jfk-recover-missing.py [release_year]
```

### jfk-diagnostic.py
Runs diagnostic checks on downloaded files.
```bash
python jfk-diagnostic.py [download_directory]
```

### jfk-other-downloader.py
Downloads miscellaneous JFK-related files.
```bash
python jfk-other-downloader.py [--threads N] [--test]
```

## Excel Files

The following Excel files are included for reference:
- national-archives-jfk-assassination-records-2017-2018-release.xlsx
- national-archives-jfk-assassination-records-2021-release.xlsx
- national-archives-jfk-assassination-records-2022-release.xlsx
- national-archives-jfk-assassination-records-2023-release.xlsx

## Notes

- All scripts include error handling and retry mechanisms
- Downloads are saved to `~/Downloads/JFK_Files` by default
- Progress bars are provided for download monitoring
- Threading is implemented for improved download speeds

