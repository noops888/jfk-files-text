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

File name are referred to in the .xlsx files and on archives.gov with mixed case, but file names on the server are all lowercase with two exceptions in the 2025 release (
104-10105-10290 (C06932214).pdf, 104-10004-10143 (C06932208).pdf). All extracted text files follow the naming convention:
```
{original file name}.md
```

## Directory Structure
```
extracted_text/             
├── releases/ 	           # 2017 release (in progress)
├── additional/            # 2017 release (in progress)
├── 2018/                  # 2018 release (in progress)   
├── 2021/                  # 2021 release 
├── 2022/                  # 2022 release
├── 2023/                  # 2023 release
├── 2025/0318/       	   # 2025 release
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

