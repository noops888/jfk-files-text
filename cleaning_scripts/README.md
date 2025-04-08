# OCR Text Cleaner

A Python script for cleaning and normalizing OCR text in Markdown files.

## Overview

This script batch processes Markdown files containing OCR text to:
- Fix common OCR errors (misread characters, formatting issues)
- Remove garbage characters and artifacts
- Normalize whitespace and line breaks
- Fix date formatting and other common patterns
- Remove redundant headers, footers, and page numbers
- Fix incorrectly split or merged words

## Usage

```bash
python3 cleaner.py input_directory output_directory [--verbose]
```

### Arguments:
- `input_directory`: Path to directory containing .md files to process
- `output_directory`: Path to directory where cleaned files will be saved
- `--verbose` or `-v`: (Optional) Display detailed processing information

### Example:
```bash
python3 cleaner.py ./raw_ocr ./cleaned_output
```

This will process all `.md` files in the `raw_ocr` directory and save cleaned versions to the `cleaned_output` directory with the same filenames.

## Features

- **OCR Error Correction**: Fixes common character misrecognition issues
- **Text Normalization**: Standardizes whitespace, line breaks, and formatting
- **Duplicate Removal**: Identifies and removes repeated headers/footers
- **Format Standardization**: Normalizes dates, section breaks, etc.
- **Word Fixing**: Repairs split or merged words
- **Page Number Removal**: Eliminates page numbers and markers

## Customization

You can extend the script by adding more corrections to the various cleaning functions:

- Add specific OCR error patterns to the `corrections` dictionary in `correct_ocr_errors()`
- Adjust the regular expressions in `normalize_formatting()` for custom formatting needs
- Modify the character set in `remove_garbage_characters()` to preserve additional special characters

## Requirements

- Python 3.6+
- No external dependencies needed 