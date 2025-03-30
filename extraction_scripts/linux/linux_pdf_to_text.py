#!/usr/bin/env python3
import os
import glob
from pathlib import Path
import pytesseract
from pdf2image import convert_from_path
import logging
import gc
import psutil
import sys
import time
import shutil

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log_memory_usage():
    """Log current memory usage"""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    logging.info(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")

def log_disk_usage():
    """Log disk usage"""
    disk = psutil.disk_usage('/')
    logging.info(f"Disk usage: {disk.percent}% (free: {disk.free / 1024 / 1024:.2f} MB)")

def cleanup_temp_files():
    """Clean up temporary files in /tmp"""
    try:
        temp_dir = '/tmp'
        for item in os.listdir(temp_dir):
            if item.startswith('pdf2image_'):
                path = os.path.join(temp_dir, item)
                try:
                    if os.path.isfile(path):
                        os.unlink(path)
                    elif os.path.isdir(path):
                        shutil.rmtree(path)
                except Exception as e:
                    logging.warning(f"Failed to delete {path}: {e}")
    except Exception as e:
        logging.warning(f"Failed to clean temp files: {e}")

def get_pdf_page_count(pdf_path):
    """Get the total number of pages in a PDF file"""
    try:
        from pdf2image import convert_from_path
        # Convert just the first page to get page count
        images = convert_from_path(pdf_path, first_page=1, last_page=1)
        # Get page count from the PDF metadata
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        count = doc.page_count
        doc.close()
        return count
    except Exception as e:
        logging.error(f"Error getting page count for {pdf_path}: {e}")
        return 0

def extract_text_from_pdf(pdf_path, output_dir):
    """
    Extract text from a PDF file and save it as markdown.
    """
    try:
        # Get total number of pages
        total_pages = get_pdf_page_count(pdf_path)
        if total_pages == 0:
            logging.error(f"Could not determine page count for {pdf_path}")
            return False
            
        logging.info(f"Processing PDF with {total_pages} pages: {pdf_path}")
        
        # Extract text from each page
        extracted_text = []
        for page_num in range(1, total_pages + 1):
            logging.info(f"Processing page {page_num} of {pdf_path}")
            log_memory_usage()
            log_disk_usage()
            
            # Convert only the current page
            images = convert_from_path(
                pdf_path,
                first_page=page_num,
                last_page=page_num,
                thread_count=1,
                dpi=150,  # Lower DPI for less memory usage
                grayscale=True,  # Use grayscale for less memory usage
                size=(None, 1500)  # Limit height to reduce memory usage
            )
            
            if not images:
                logging.error(f"Failed to convert page {page_num}")
                continue
                
            # Extract text from the current page
            text = pytesseract.image_to_string(images[0])
            extracted_text.append(text)
            
            # Clean up the image
            images[0].close()
            del images
            gc.collect()
            
            # Log memory after cleanup
            log_memory_usage()
            
            # Small delay between pages
            time.sleep(0.5)
        
        # Combine all text
        full_text = "\n\n".join(extracted_text)
        
        # Create output filename
        pdf_name = Path(pdf_path).stem
        output_path = os.path.join(output_dir, f"{pdf_name}.md")
        
        # Write to markdown file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
        
        logging.info(f"Successfully extracted text to {output_path}")
        
        # Clean up
        del extracted_text
        gc.collect()
        
        # Clean up temporary files
        cleanup_temp_files()
        
        return True
        
    except Exception as e:
        logging.error(f"Error processing {pdf_path}: {str(e)}")
        return False
    finally:
        # Ensure cleanup
        gc.collect()
        cleanup_temp_files()

def get_pdf_files(directory):
    """
    Get all PDF files from directory, case insensitive.
    """
    pdf_files = []
    for file in os.listdir(directory):
        if file.lower().endswith('.pdf'):
            pdf_files.append(os.path.join(directory, file))
    return pdf_files

def main():
    # Define directories
    input_dir = "original_files"
    output_dir = "extracted_text"
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all PDF files (case insensitive)
    pdf_files = get_pdf_files(input_dir)
    
    if not pdf_files:
        logging.warning(f"No PDF files found in {input_dir}")
        return
    
    logging.info(f"Found {len(pdf_files)} PDF files to process")
    
    # Process each PDF file
    success_count = 0
    for pdf_file in pdf_files:
        if extract_text_from_pdf(pdf_file, output_dir):
            success_count += 1
        # Clean up after each PDF
        gc.collect()
        cleanup_temp_files()
        log_memory_usage()
        log_disk_usage()
        
        # Small delay between PDFs
        time.sleep(1)
    
    logging.info(f"Processing complete. Successfully processed {success_count} out of {len(pdf_files)} files.")

if __name__ == "__main__":
    main() 