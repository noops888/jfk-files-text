# JFK Files Extracted Text

This directory contains the extracted text content from the JFK assassination records. The text files were generated using different extraction methods based on the release year of the documents.

## Current Status

| Release Year | Status | Extraction Method |
|--------------|---------|-------------------|
| 2025 | ✅ Complete | Apple Vision OCR (`apple_vision_pdf_to_text.py`) |
| 2023 | ✅ Complete | Apple Vision OCR (`apple_vision_pdf_to_text.py`) |
| 2022 | ✅ Complete | Linux PDF to Text (`linux_pdf_to_text.py`) |
| 2021 | ✅ Complete | Apple Vision OCR (`apple_vision_pdf_to_text.py`) |
| 2017-2018 | 🚧 In Progress | Linux PDF to Text (`linux_pdf_to_text.py`) |

## File Organization

All extracted text files follow the naming convention:
```
{original file name}.md
```

## Directory Structure
```
extracted_text/
├── release-2025/          # Completed files from 2025 release
├── release-2023/          # Completed files from 2023 release
├── release-2022/          # Completed files from 2022 release
├── release-2021/          # Completed files from 2021 release
├── release-2017-2018/     # Completed files from 2017-2018 release
└── reports/               # Reports and statistics on completed extractions
```

## File Format

The extracted text files are saved in Markdown format (.md) with the following structure:
```markdown
# Document Title

## Page 1
[Extracted text from page 1]

---

## Page 2
[Extracted text from page 2]

---
```

## Quality Assurance

- All files have been processed using high-quality OCR methods
- Text extraction was performed using native system capabilities where available
- Files maintain their original document structure with page breaks
- Special characters and formatting are preserved where possible

## Related Scripts

For information about the extraction methods used, see:
- [Apple Vision OCR Script](../extraction_scripts/macOS/apple_vision_ocr/README.md)
- [Linux PDF to Text Script](../extraction_scripts/linux/README.md)

