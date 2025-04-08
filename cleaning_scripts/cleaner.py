#!/usr/bin/env python3

import os
import re
import sys
from pathlib import Path

def fix_ocr_errors(text):
    """Fix only the most common and clear OCR errors."""
    replacements = {
        'JEK': 'JFK',
        'EROM': 'FROM',
    }
    for wrong, right in replacements.items():
        text = text.replace(wrong, right)
    return text

def format_document_id(text):
    """Format document IDs consistently."""
    # Find document ID pattern
    doc_id_pattern = r'DOCID-(\d+)'
    match = re.search(doc_id_pattern, text)
    if match:
        doc_id = match.group(1)
        # Format with hyphens every 4 digits
        formatted_id = '-'.join([doc_id[i:i+4] for i in range(0, len(doc_id), 4)])
        text = text.replace(f'DOCID-{doc_id}', f'DOCID-{formatted_id}')
    return text

def standardize_dates(text):
    """Standardize dates that are clearly in MM/DD/YYYY format."""
    def replace_date(match):
        month, day, year = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    
    # Only convert dates that are clearly in MM/DD/YYYY format
    text = re.sub(r'(\d{1,2})/(\d{1,2})/(\d{4})', replace_date, text)
    return text

def process_file(input_file, output_file):
    """Process a single markdown file."""
    try:
        # Read input file
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Apply only the essential fixes
        content = fix_ocr_errors(content)
        content = format_document_id(content)
        content = standardize_dates(content)
        
        # Write output file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
    except Exception as e:
        print(f"Error processing {input_file}: {str(e)}")
        return False

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 cleaner.py input_directory output_directory")
        sys.exit(1)
    
    input_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process all markdown files
    total_files = 0
    processed_files = 0
    
    for input_file in input_dir.glob('*.md'):
        total_files += 1
        output_file = output_dir / input_file.name
        
        if process_file(input_file, output_file):
            processed_files += 1
            print(f"Processing [{total_files}/1484]: {input_file.name} ✓")
    
    print(f"\nCompleted: {processed_files}/{total_files} files processed successfully")

if __name__ == '__main__':
    main() 