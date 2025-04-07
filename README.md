# JFK Files Text Extraction Project

This project contains tools and extracted text from the JFK assassination records released by the National Archives. It includes scripts for downloading the original PDF files and converting them to searchable text format.

## Project Structure

```
.
├── downloader_scripts/        # Scripts for downloading PDF files
├── extraction_scripts/        # Scripts for converting PDFs to text
│   ├── linux/                 # Linux-specific extraction tools
│   ├── macOS/                 # macOS-specific extraction tools
│   └── find_missing.py        # Utility to find missing conversions
└── extracted_text/            # Extracted text content
    ├── release-2025/          # 2025 release files
    ├── release-2023/          # 2023 release files
    ├── release-2022/          # 2022 release files
    ├── release-2021/          # 2021 release files
    ├── release-2022/          # 2017-2018 release files
    └── reports/               # Extraction reports
```

## Current Status

| Release Year | Status | Extraction Method | Files Downloaded | Size | Total Files Listed |
|--------------|---------|-------------------|------------------|------|-------------------|
| 2025 | ✅ Complete | Apple Vision OCR | 2,566 | 8.12GB | 2,566 |
| 2023 | ✅ Complete | Apple Vision OCR | 2,680 | 6.12GB | 2,693 |
| 2022 | ✅ Complete | Linux PDF to Text | 13,199 | 14.15GB | 13,263 |
| 2021 | ✅ Complete | Apple Vision OCR | 1,484 | 1.36GB | 1,491 |
| 2017-2018 | 🚧 In Progress | Linux PDF to Text | 53,497 | 37.76GB | 53,604 |

## Getting Started

### Prerequisites
- Python 3.6 or later
- System-specific dependencies (see individual script READMEs)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/jfk-files-text.git
cd jfk-files-text
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install system dependencies as needed (see individual script READMEs)

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
```bash
python extraction_scripts/linux/linux_pdf_to_text.py
```

### Finding Missing Files
To check for any missing conversions:
```bash
python extraction_scripts/find_missing.py
```

## Documentation

- [Downloader Scripts Documentation](downloader_scripts/README.md)
- [Extraction Scripts Documentation](extraction_scripts/README.md)
- [Extracted Text Documentation](extracted_text/README.md)

## Known Issues

### Data Inconsistencies

1. **Release Format Variations**
   - The release page formats are incosistent
   - No .xlsx file is available for the 2025 release
   - Previous releases have .xlsx files with inconsistent formats

2. **Duplicate Files**
   - 2017-2018 release contains duplicate file names in downloads
   - 2017-2018 .xlsx file contains 54,636 line items with duplicate filenames

3. **Missing Files**
   - Discrepancies exist between downloaded files and listed totals:
     - 2023: 13 files missing
     - 2022: 64 files missing
     - 2021: 7 files missing
     - 2017-2018: 107 files missing

4. **Zero Size Files**
   - A small number of 0kb files were output by the Linux tesseract script for the 2022 and 2017-2018 releases:
     - 2022: 54 0kb files
     - 2017-2018: (need to update when complete)
    
4. **OCR Errors**
   - The extracted text contains a substanital amount of OCR errors due to the low quality of many of the input files. 

### Archive Statistics
- Total archive size: 67.5 GB
- Total files: 73,426
- Extracted text available at: [jfk-files-text](https://github.com/noops888/jfk-files-text/)

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
