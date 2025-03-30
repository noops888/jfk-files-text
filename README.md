# JFK Files Text Extraction Project

This project contains tools and extracted text from the JFK assassination records released by the National Archives. It includes scripts for downloading the original PDF files and converting them to searchable text format.

## Project Structure

```
.
├── downloader_scripts/          # Scripts for downloading PDF files
├── extraction_scripts/          # Scripts for converting PDFs to text
│   ├── linux/                  # Linux-specific extraction tools
│   ├── macOS/                  # macOS-specific extraction tools
│   └── find_missing.py         # Utility to find missing conversions
└── extracted_text/             # Extracted text content
    ├── release-2025/          # 2025 release files
    ├── release-2023/          # 2023 release files
    └── release-2021/          # 2021 release files
```

## Current Status

| Release Year | Status | Extraction Method |
|--------------|---------|-------------------|
| 2025 | ✅ Complete | Apple Vision OCR |
| 2023 | ✅ Complete | Apple Vision OCR |
| 2022 | 🚧 In Progress | Linux PDF to Text |
| 2021 | ✅ Complete | Apple Vision OCR |
| 2017-2018 | 🚧 In Progress | Linux PDF to Text |

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