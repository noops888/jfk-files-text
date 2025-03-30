# Linux PDF Text Extraction

This script extracts text from PDF files using OCR (Optical Character Recognition) technology, specifically designed for Linux systems. It processes PDFs page by page with memory optimization and monitoring.

## Prerequisites

### System Requirements
- Linux operating system
- Tesseract OCR engine
- Poppler utilities

### Installation of System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install tesseract-ocr
sudo apt-get install poppler-utils

# Fedora
sudo dnf install tesseract
sudo dnf install poppler-utils
```

### Python Dependencies
Install Python dependencies using:
```bash
pip install -r requirements.txt
```

## Directory Structure
```
.
├── original_files/     # Place PDF files here
└── extracted_text/     # Output directory for markdown files
```

## Usage

1. Place your PDF files in the `original_files` directory
2. Run the script:
```bash
python linux_pdf_to_text.py
```

## Features

- Memory-optimized processing of large PDFs
- Page-by-page extraction with memory cleanup
- Automatic temporary file cleanup
- Memory and disk usage monitoring
- Converts PDFs to searchable markdown files
- Error handling and logging
- Progress tracking for each page and file

## Output

The script generates markdown (.md) files in the `extracted_text` directory, with the same base name as the input PDF files.

## Performance Notes

- Uses grayscale conversion and optimized DPI settings for better memory usage
- Implements garbage collection between pages
- Includes automatic cleanup of temporary files
- Monitors system resources during processing 