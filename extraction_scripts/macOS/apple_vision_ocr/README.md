# Apple Vision OCR PDF Text Extraction

This script uses Apple's Vision framework for OCR (Optical Character Recognition) to extract text from PDF files on macOS. It leverages the native Vision framework for high-quality text recognition.

## Prerequisites

### System Requirements
- macOS 10.15 or later
- Poppler utilities (for PDF to image conversion)

### Installation of System Dependencies

```bash
# Install Poppler using Homebrew
brew install poppler
```

### Python Dependencies
Install Python dependencies using:
```bash
pip install -r requirements.txt
```

## Usage

```bash
python apple_vision_pdf_to_text.py <input_directory> <output_directory>
```

```bash
python apple_vision_pdf_to_text_parallel.py <input_directory> <output_directory> -w [nummber of CPU cores to utilize]
```


### Arguments
- `input_directory`: Directory containing PDF files to process
- `output_directory`: Directory where markdown files will be saved

## Features

- Uses Apple's Vision framework for high-quality OCR
- Processes PDFs page by page
- Generates markdown output with page breaks
- Automatic cleanup of temporary files
- Progress tracking
- Error handling

## Output Format

The script generates markdown (.md) files with the following structure:
```markdown
# Document Title

## Page 1
[Extracted text from page 1]

---

## Page 2
[Extracted text from page 2]

---
```

## Notes

- The script uses a 300 DPI resolution for optimal text recognition
- Temporary files are automatically cleaned up after processing
- Each page is processed separately to manage memory usage 