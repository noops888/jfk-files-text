# JFK Files Text Extraction Project

This project contains tools and extracted text from the JFK assassination records released by the [National Archives.](https://www.archives.gov/research/jfk) It includes scripts for downloading the original PDF files and converting them to searchable text format. The unorthodox directory structure of the extracted text mirrors the source to make it easier to reference or link files back to the original on archives.gov. 

## Project Structure

```
.
├── downloader_scripts/        # Scripts for downloading files from the National Archives
│   ├── csv/                   # csv files listing direct download URLs for all files
│   └── xlsx/                  # xlsx files from the National Archives with additional details about each file
├── extraction_scripts/        # Scripts for converting PDF to text
│   ├── linux/                 # Linux-specific extraction tools
│   ├── macOS/                 # macOS-specific extraction tools
│   └── find_missing.py        # Utility to find missing conversions
└── extracted_text/            # Extracted text content               
    ├── releases/              # 2017 release (in progress)
        ├── additional/        # 2017 release (in progress)
        ├── 2018/              # 2018 release (in progress)   
        ├── 2021/              # 2021 release
        ├── 2022/              # 2022 release
        ├── 2023/              # 2023 release
        ├── 2025/0318/         # 2025 release
        └── reports/           # Reports and statistics on completed extractions    
```

## Current Status

| Release Year | Status | Extraction Method | Files Downloaded | Size | Total Files Listed |
|--------------|---------|-------------------|------------------|------|-------------------|
| 2025 | ✅ Complete | Apple Vision OCR | 2,566 | 8.12GB | 2,566 |
| 2023 | ✅ Complete | Apple Vision OCR | 2,693 | 6.20GB | 2,693 |
| 2022 | ✅ Complete | Linux PDF to Text | 13,199 | 14.15GB | 13,199 |
| 2021 | ✅ Complete | Apple Vision OCR | 1,484 | 1.36GB | 1,484 |
| 2017-2018 | 🚧 In Progress | Linux PDF to Text | 53,543 | 57.18GB | 53,547 |

Note: 34 files in the 2022 release and 5 files in the 2021 release tie to multiple record numbers listed in the .xlsx files which have more rows than unique file names (13,263 and 1,491 resptively). The [2017-2018 release xlsx file](https://www.archives.gov/files/research/jfk/national-archives-jfk-assassination-records-2017-2018-release.xlsx)contains 6 bad links, but [the 2017-2018 release website](https://www.archives.gov/research/jfk/release-2017-2018) lists two files not included in the xlsx in the /additional path. The 2017-2018 release all contains 19 audio files (17 .wav, 2 .mp3).

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
   - 2017-2018 release contains duplicate file names on the website and in the xslx file
   - 2017-2018 .xlsx file contains 54,636 line items including some duplicate filenames
   
3. **Missing Files**
   - 2017-2018 xlsx has 54,604 line items (6 bad links)
   - 2017-2018 website lists 54,601 line items (3 bad links, two additional files not referenced in the xlsx)

4. **Zero Size Files**
   - A small number of 0kb files were output by the Linux tesseract script for the 2022 and 2017-2018 releases:
     - 2022: 54 0kb files
     - 2017-2018: (need to update when complete)
    
4. **OCR Errors**
   - The extracted text contains a substanital amount of OCR errors due to the low quality of many of the input files. 

### Archive Statistics
- Total archive size: 87 GB
- Total files: 73,439
- Extracted text available at: [jfk-files-text](https://github.com/noops888/jfk-files-text/)

## WebUI 

A simple WebUI to query to the completed Files using the DeepSeek R1 Distill Llama 70B LLM is available at [https://jfkfiles.app.](https://jefkfiles.app)  

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [The National Archives](https://www.archives.gov/research/jfk) for providing the JFK assassination records
- Contributors to the various open-source tools used in this project 
