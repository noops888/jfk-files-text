# JFK Files Text Extraction Project

This project contains tools and extracted text from the JFK assassination records released by the National Archives. It includes scripts for downloading the original PDF files and converting them to searchable text format.

## Project Structure

```
.
├── downloader_scripts/                         # Scripts for downloading PDF files
├── extraction_scripts/                         # Scripts for converting PDFs to text
│   ├── linux/                                  # Linux-specific extraction tools
│   │   ├── linux_pdf_to_text.py                # Original version
│   │   ├── linux_pdf_to_text_robust.py         # New robust version
│   │   └── linux_pdf_to_text_multithreaded.py  # New multithreaded version
│   ├── macOS/                                  # macOS-specific extraction tools
│   └── find_missing.py                         # Utility to find missing conversions
└── extracted_text/                             # Extracted text content    
```

## Current Status

| Release Year | Status | Extraction Method | Files Downloaded | Size | Total Files Listed |
|--------------|---------|-------------------|------------------|------|-------------------|
| 2025 | ✅ Complete | Apple Vision OCR | 2,343 | 7.57GB | 2,359 |
| 2023 | ✅ Complete | Apple Vision OCR | 2,680 | 6.12GB | 2,693 |
| 2022 | ✅ Complete | Linux PDF to Text | 13,199 | 14.15GB | 13,199 |
| 2021 | ✅ Complete | Apple Vision OCR | 1,484 | 1.36GB | 1,491 |
| 2017-2018 | 🚧 In Progress | Linux PDF to Text | 53,497 | 37.76GB | 53,604 |

## Getting Started

### Prerequisites
- Python 3.6 or later
- System-specific dependencies (see below)

### System Dependencies

#### Linux
```bash
sudo apt-get install poppler-utils tesseract-ocr-all
```

Note: It is important to install tesseract-ocr-all becuase the source documents contain multiple foreign languages. 

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/jfk-files-text.git
cd jfk-files-text
```

2. Create and activate a Python virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Directory Structure

The extraction scripts automatically create and manage these directories:
- `original_files/`: Place your PDF files here (create this manually)
- `extracted_text/`: Output directory for markdown files (created automatically)
- `temp_processing/`: Temporary directory for processing (created automatically)

## Usage

### Downloading Files
Use the appropriate downloader script from `downloader_scripts/` based on the release year:
```bash
python downloader_scripts/jfk-2025-pdf-downloader.py
```

### Extracting Text
Choose the appropriate extraction method based on your operating system:

#### macOS
```bash
python extraction_scripts/macOS/apple_vision_ocr/apple_vision_pdf_to_text.py
```

#### Linux
You have two options:

1. Original Version (for smaller archives):
```bash
python extraction_scripts/linux/linux_pdf_to_text.py
```

2. Robust Version (recommended for large archives):
```bash
python extraction_scripts/linux/linux_pdf_to_text_robust.py
```

3. Multithreaded Version (recommended when multiople CPU cores are available):
```bash
python extraction_scripts/linux/linux_pdf_to_text_multithreaded.py --threads [number of cores to utilize]
```

The robust version includes:
- Crash recovery and automatic resume
- Memory-efficient processing
- Progress tracking and logging
- Batch processing
- Error handling and retries
- Resource monitoring
- Handles English, Spanish, Russian, Bulgarian, German, French and Italian languages 

### Custom Directories
You can specify custom input and output directories using environment variables:
```bash
INPUT_DIR=/path/to/pdfs OUTPUT_DIR=/path/to/output python extraction_scripts/linux/linux_pdf_to_text_robust.py
```

### Finding Missing Files
To check for any missing conversions:
```bash
python extraction_scripts/find_missing.py
```

## Features of the Robust Version

### Crash Recovery
- Automatically resumes from where it left off after crashes or interruptions
- Maintains state information in `processing_progress.json`
- Skips already processed files
- Retries failed files up to 3 times
- Cleans up incomplete output files

### Memory Management
- Processes one page at a time
- Uses grayscale images and lower DPI
- Implements aggressive cleanup
- Processes files in small batches
- Memory usage kept below 500MB-1GB

### Progress Tracking
- Saves state after each page
- Tracks failed files and retries
- Maintains detailed logs in `pdf_processing.log`
- Shows memory and disk usage

### Error Handling
- Retries failed files up to 3 times
- Deletes incomplete output files
- Cleans up temporary files
- Handles interruptions gracefully

## Documentation

- [Downloader Scripts Documentation](downloader_scripts/README.md)
- [Extraction Scripts Documentation](extraction_scripts/README.md)
- [Extracted Text Documentation](extracted_text/README.md)

## Troubleshooting

1. If you see "poppler not installed" errors:
   ```bash
   sudo apt-get install poppler-utils
   ```

2. If you see "tesseract not installed" errors:
   ```bash
   sudo apt-get install tesseract-ocr
   ```

3. If memory usage is too high:
   - Reduce the batch size in the script
   - Increase delays between operations
   - Process smaller batches of files

4. If the script crashes:
   - Check the log file for error messages
   - Verify system resources
   - Restart the script (it will resume from where it left off)

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- National Archives for providing the JFK assassination records
- Contributors to the various open-source tools used in this project 