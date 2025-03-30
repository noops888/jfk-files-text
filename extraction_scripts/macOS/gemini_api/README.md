# Gemini API PDF Text Extraction

This script uses Google's Gemini API to extract text from PDF files. It provides high-quality text extraction with advanced language understanding capabilities.

## Prerequisites

### System Requirements
- macOS
- Python 3.7 or later
- Google Cloud API key with Gemini API access

### Python Dependencies
Install Python dependencies using:
```bash
pip install -r requirements.txt
```

## Configuration

1. Obtain a Google Cloud API key with Gemini API access
2. Replace the `API_KEY` variable in the script with your actual API key:
```python
API_KEY = "YOUR_API_KEY"  # Replace with your actual API key
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
python extract_with_gemini.py
```

## Features

- Uses Google's Gemini API for advanced text extraction
- Automatic retry mechanism for failed API calls
- Skips already processed files
- Progress tracking
- Error handling and logging
- Rate limiting and backoff implementation

## Output

The script generates text (.txt) files in the `extracted_text` directory, with the same base name as the input PDF files.

## Notes

- The script includes rate limiting to avoid API quota issues
- Failed extractions are logged for review
- Each file is processed independently
- The script maintains a record of processed files to avoid duplicates 