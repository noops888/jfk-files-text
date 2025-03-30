import os
import time
import requests
import base64
import json
from pathlib import Path
import random

# Configuration
ORIGINAL_FILES_DIR = "original_files"
EXTRACTED_TEXT_DIR = "extracted_text"
API_KEY = "YOUR_API_KEY"  # Replace with your actual API key

# Create output directory
os.makedirs(EXTRACTED_TEXT_DIR, exist_ok=True)

def process_file(pdf_path, max_retries=5):
    """Process a single PDF file with direct API calls and better retry logic"""
    filename = pdf_path.stem
    output_path = Path(EXTRACTED_TEXT_DIR) / f"{filename}.txt"
    
    # Skip if already processed
    if output_path.exists():
        print(f"Skipping {filename} - already processed")
        return True
        
    print(f"Processing {filename}...")
    
    # Read PDF file and encode as base64
    with open(pdf_path, 'rb') as f:
        pdf_data = base64.b64encode(f.read()).decode('utf-8')
    
    # Prepare API request
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    data = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "application/pdf",
                            "data": pdf_data
                        }
                    },
                    {
                        "text": "Extract all text from this PDF document. Return only the raw text without any formatting or commentary."
                    }
                ]
            }
        ],
        "generation_config": {
            "temperature": 0
        }
    }
    
    # Try with retries for specific error codes
    for attempt in range(max_retries) :
        try:
            # Make API request
            response = requests.post(url, headers=headers, json=data)
            
            # Check if request was successful
            if response.status_code == 200:
                result = response.json()
                
                # Extract text from response
                if 'candidates' in result and len(result['candidates']) > 0:
                    text = result['candidates'][0]['content']['parts'][0]['text']
                    
                    # Save the extracted text
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(text)
                    
                    print(f"Successfully processed {filename}")
                    return True
                else:
                    print(f"Error: No text in response for {filename}")
            else:
                # Check for specific error codes that warrant retries
                retry_codes = [429, 500, 503, 504]  # Rate limit, server errors
                
                if response.status_code in retry_codes:
                    error_msg = response.text
                    print(f"API Error ({response.status_code}): {error_msg}")
                    
                    if attempt < max_retries - 1:
                        # Exponential backoff with jitter
                        delay = (2 ** attempt) + random.uniform(0, 1)
                        print(f"Retrying {filename} in {delay:.1f} seconds (attempt {attempt+1}/{max_retries})...")
                        time.sleep(delay)
                        continue
                    else:
                        print(f"Failed to process {filename} after {max_retries} attempts")
                        return False
                else:
                    # Non-retryable error
                    print(f"API Error ({response.status_code}): {response.text}")
                    return False
                    
        except Exception as e:
            print(f"Error processing {pdf_path.name}: {str(e)}")
            
            if attempt < max_retries - 1:
                # Exponential backoff with jitter
                delay = (2 ** attempt) + random.uniform(0, 1)
                print(f"Retrying {filename} in {delay:.1f} seconds (attempt {attempt+1}/{max_retries})...")
                time.sleep(delay)
                continue
            else:
                print(f"Failed to process {filename} after {max_retries} attempts")
                return False
    
    return False

def main():
    # Get list of PDF files
    pdf_dir = Path(ORIGINAL_FILES_DIR)
    pdf_files = list(pdf_dir.glob("**/*.pdf"))
    
    print(f"Found {len(pdf_files)} PDF files")
    
    # Create a list to track failed files for later retry
    failed_files = []
    
    # Process files one by one with rate limiting
    successful = 0
    failed = 0
    
    for i, pdf_file in enumerate(pdf_files):
        # Process the file
        if process_file(pdf_file):
            successful += 1
        else:
            failed += 1
            failed_files.append(pdf_file)
            
        # Add delay between files to avoid rate limits
        if i < len(pdf_files) - 1:  # Skip delay after last file
            delay = random.uniform(2, 5)  # Random delay between 2-5 seconds
            print(f"Waiting {delay:.1f} seconds before next file...")
            time.sleep(delay)
            
        # Add a longer pause every 10 files
        if (i + 1) % 10 == 0 and i < len(pdf_files) - 1:
            pause = 30
            print(f"Processed 10 files. Taking a {pause} second break to avoid rate limits...")
            time.sleep(pause)
    
    # Report on initial processing
    print(f"\nInitial processing complete!")
    print(f"Successfully processed: {successful} files")
    print(f"Failed: {failed} files")
    
    # Retry failed files once more with longer delays
    if failed_files:
        print(f"\nRetrying {len(failed_files)} failed files with longer delays...")
        retry_successful = 0
        
        for i, pdf_file in enumerate(failed_files):
            print(f"Retry attempt for {pdf_file.name}...")
            
            # Process with more retries
            if process_file(pdf_file, max_retries=7):
                retry_successful += 1
                failed -= 1
            
            # Add longer delay between retries
            if i < len(failed_files) - 1:
                delay = random.uniform(5, 10)
                print(f"Waiting {delay:.1f} seconds before next retry...")
                time.sleep(delay)
    
        print(f"\nRetry processing complete!")
        print(f"Successfully processed on retry: {retry_successful} files")
    
    # Final report
    print(f"\nFinal processing results:")
    print(f"Successfully processed: {successful + retry_successful} files")
    print(f"Failed: {failed} files")
    print(f"Success rate: {(successful + retry_successful)/(successful + failed)*100:.2f}%")

if __name__ == "__main__":
    main()

