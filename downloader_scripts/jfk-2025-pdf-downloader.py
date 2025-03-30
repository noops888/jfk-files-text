#!/usr/bin/env python3
"""
JFK Files Downloader and Merger
-------------------------------
This script downloads JFK files from the National Archives website and merges them by release year.
Designed for macOS 15.3.2 (24D81).

Usage:
    python jfk_downloader.py

Requirements:
    - Python 3.x
    - requests
    - BeautifulSoup4
    - PyPDF2

Install dependencies with:
    pip install requests beautifulsoup4 PyPDF2
"""

import os
import requests
from bs4 import BeautifulSoup
import re
import time
from PyPDF2 import PdfMerger
from urllib.parse import urljoin

# Configuration
BASE_URL = "https://www.archives.gov"
RELEASE_URLS = {
    "2025": "https://www.archives.gov/research/jfk/release-2025",
}
DOWNLOAD_DIR = os.path.expanduser("~/Downloads/JFK_Files")
MERGED_DIR = os.path.expanduser("~/Downloads/JFK_Files/Merged")

# Create necessary directories
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(MERGED_DIR, exist_ok=True)

def extract_pdf_urls(url):
    """Extract all PDF URLs from the given page."""
    print(f"Scanning {url} for PDF links...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all links on the page
        links = soup.find_all('a', href=True)
        
        # Filter for PDF links
        pdf_links = []
        for link in links:
            href = link['href']
            if href.endswith('.pdf'):
                full_url = urljoin(BASE_URL, href) if not href.startswith('http') else href
                pdf_links.append(full_url)
        
        print(f"Found {len(pdf_links)} PDF links")
        return pdf_links
    
    except Exception as e:
        print(f"Error extracting PDF URLs from {url}: {e}")
        return []

def download_pdf(url, save_path):
    """Download a PDF file from the given URL."""
    try:
        print(f"Downloading {url}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"Download complete: {save_path}")
        return True
    
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def merge_pdfs(pdf_paths, output_path):
    """Merge multiple PDFs into a single file."""
    try:
        merger = PdfMerger()
        
        for pdf in pdf_paths:
            try:
                merger.append(pdf)
            except Exception as e:
                print(f"Error appending {pdf}: {e}")
        
        merger.write(output_path)
        merger.close()
        
        print(f"Successfully merged PDFs into {output_path}")
        return True
    
    except Exception as e:
        print(f"Error merging PDFs: {e}")
        return False

def main():
    for release, url in RELEASE_URLS.items():
        print(f"\n{'='*50}")
        print(f"Processing {release} release")
        print(f"{'='*50}")
        
        # Create release directory
        release_dir = os.path.join(DOWNLOAD_DIR, f"release-{release}")
        os.makedirs(release_dir, exist_ok=True)
        
        # Get PDF URLs
        pdf_urls = extract_pdf_urls(url)
        
        # Download PDFs
        pdf_paths = []
        for i, pdf_url in enumerate(pdf_urls):
            filename = os.path.basename(pdf_url)
            if not filename:
                filename = f"document_{i+1}.pdf"
            
            save_path = os.path.join(release_dir, filename)
            
            # Download if file doesn't exist
            if not os.path.exists(save_path):
                success = download_pdf(pdf_url, save_path)
                if success:
                    pdf_paths.append(save_path)
                
                # Be nice to the server
                time.sleep(1)
            else:
                print(f"File already exists: {save_path}")
                pdf_paths.append(save_path)
        
        # Merge PDFs
        if pdf_paths:
            output_path = os.path.join(MERGED_DIR, f"release-{release}.pdf")
            merge_pdfs(pdf_paths, output_path)
    
    print("\nAll tasks completed!")

if __name__ == "__main__":
    main()
