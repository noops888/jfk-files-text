# JFK Files Downloader Scripts

This repository contains a collection of Python scripts designed to download the JFK assassination records from the National Archives website. Due to varying web page structures and Excel file formats across different release years, separate scripts were developed to handle each release period.

## Source

All JFK assassination records are available at: https://www.archives.gov/research/jfk

The download script will preserve the directory structure of the original archive. We identified the following URL patterns for each JFK archive release:

Release 2017-2018

https://www.archives.gov/files/research/jfk/releases/
https://www.archives.gov/files/research/jfk/releases/2018/
https://www.archives.gov/files/research/jfk/releases/additional/

Release 2021

https://www.archives.gov/files/research/jfk/releases/2021/

Release 2022

https://www.archives.gov/files/research/jfk/releases/2022/

Release 2023

https://www.archives.gov/files/research/jfk/releases/2023/
https://www.archives.gov/files/research/jfk/releases/2023/08/

Release 2025

https://www.archives.gov/files/research/jfk/releases/2025/0318/


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

### jfk-diagnostic.py
Runs diagnostic checks on downloaded files.
```bash
python jfk-diagnostic.py [download_directory]
```

### jfk_downloader.py
Downloads files from any CSV listing unqiue filenames and corresponding URLs.
```bash
ython jfk_downloader.py --csv CSV_FILE --output OUTPUT_DIR [--threads THREADS] [--resume] [--verify]
```

Arguments

--csv CSV_FILE: Path to the CSV file containing download URLs
--output OUTPUT_DIR: Directory where files will be downloaded
--threads THREADS: Number of download threads (default: 4)
--resume: Resume previous download (skip already downloaded files)
--verify: Verify integrity of previously downloaded files

### jfk-recover-missing.py
Recovers any missing files from previous downloads.
```bash
python jfk-recover-missing.py [release_year]
```

## Excel Files

The following Excel files are included for reference:
- ./xlsx/national-archives-jfk-assassination-records-2017-2018-release.xlsx
- ./xlsx/national-archives-jfk-assassination-records-2021-release.xlsx
- ./xlsx/national-archives-jfk-assassination-records-2022-release.xlsx
- ./xlsx/national-archives-jfk-assassination-records-2023-release.xlsx

## CSV Files
The following unique URL CSV files are included
- ./csv/jfk_archive_2017_2018_urls.csv
- ./csv/jfk_archive_2021_urls.csv
- ./csv/jfk_archive_2022_urls.csv
- ./csv/jfk_archive_2023_urls.csv
- ./csv/jfk_archive_2025_urls.csv

## Notes

- All scripts include error handling and retry mechanisms
- Downloads are saved to the current directory by default
- Progress bars are provided for download monitoring
- Threading is implemented for improved download speeds

