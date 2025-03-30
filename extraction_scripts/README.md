# Find Missing Text Files

This utility script helps identify PDF files that have not been successfully converted to text files. It compares the contents of the `original_files` directory (containing PDFs) with the `extracted_text` directory (containing converted text files) to find any missing conversions.

## Directory Structure
```
.
├── original_files/     # Contains original PDF files
└── extracted_text/     # Contains converted text files
```

## Usage

```bash
python find_missing.py
```

## Features

- Case-insensitive file matching
- Multiple file detection methods for reliability
- Detailed debugging information
- DOCID range analysis
- File name validation
- Comprehensive reporting of missing files

## Output

The script provides:
- Total count of PDF files
- Total count of text files
- Number of missing text files
- List of missing files
- Debug information including:
  - File counts from different detection methods
  - DOCID range analysis
  - First and last 5 files in each directory
  - Any files with invalid naming patterns

## Notes

- The script expects files to follow the pattern `DOCID-*.pdf` and `DOCID-*.md`
- It performs case-insensitive matching to avoid duplicates
- Invalid file names (not starting with DOCID-) are reported as warnings
- The script uses multiple file detection methods to ensure accuracy

## Example Output
```
Debug information for DOCID-*.pdf files (case insensitive):
glob count: 100
listdir count: 100
scandir count: 100

DOCID range: 1 to 100
Number of unique DOCIDs: 100

Results:
Total PDFs: 100
Total TXTs: 95
Missing TXT files: 5

Missing files:
DOCID-1.pdf
DOCID-2.pdf
...
``` 