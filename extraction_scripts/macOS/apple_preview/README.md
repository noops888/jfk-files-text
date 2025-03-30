# Apple Preview PDF Text Extraction

This script uses macOS's native Preview application to extract text from PDF files. It provides a simple and reliable method for text extraction using built-in macOS capabilities.

## Prerequisites

### System Requirements
- macOS
- Preview application (built into macOS)
- AppleScript support

### Python Dependencies
Install Python dependencies using:
```bash
pip install -r requirements.txt
```

## Directory Structure
```
.
├── original_files/     # Place PDF files here
└── extracted_text/     # Output directory for text files
```

## Usage

1. Place your PDF files in the `original_files` directory
2. Run the script:
```bash
python extract_mac_preview.py
```

## Features

- Uses native macOS Preview application
- No external OCR dependencies required
- Progress tracking with tqdm
- Skips already processed files
- Error handling and logging
- Simple and reliable extraction

## Output

The script generates text (.txt) files in the `extracted_text` directory, with the same base name as the input PDF files.

## Notes

- This method works best with PDFs that already contain text (not scanned documents)
- The script uses AppleScript to interact with Preview
- Each file is processed independently
- The script maintains a record of processed files to avoid duplicates
- The script fails if a file has a very large number of pages (exact limit is not clear)

## Troubleshooting

If you encounter any issues:
1. Ensure Preview is the default PDF viewer
2. Check that the PDF files are not corrupted
3. Verify that you have read permissions for the input files
4. Ensure you have write permissions for the output directory