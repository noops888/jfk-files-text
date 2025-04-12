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

### count.sh 
A simple shell script to count files by extension in a specified directory.


### jfk-universal-downloader.py
Downloads files from any CSV listing unqiue filenames and corresponding URLs.
```bash
python jfk_universal_downloader.py
```

### jfk-2025-pdf-downloader.py
Downloads and merges PDF files from the 2025 release which does not have an .xlsv listing all file URLs
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

## Excel Files

The following Excel files are included for reference:
- national-archives-jfk-assassination-records-2017-2018-release.xlsx
- national-archives-jfk-assassination-records-2021-release.xlsx
- national-archives-jfk-assassination-records-2022-release.xlsx
- national-archives-jfk-assassination-records-2023-release.xlsx

## CSV Files
The following unique URL CSV files are included
- 2017_unique_urls.csv
- 2018_unique_urls.csv
- 2021_unique_urls.csv
- 2023_unique_urls.csv
- 2025_unique_urls.csv

## Notes

- All scripts include error handling and retry mechanisms
- Downloads are saved to the current directory by default
- Progress bars are provided for download monitoring
- Threading is implemented for improved download speeds

