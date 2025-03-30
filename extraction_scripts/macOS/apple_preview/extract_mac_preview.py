#!/usr/bin/env python3
import os
import subprocess
import time
from glob import glob
from tqdm import tqdm

# Configuration
ORIGINAL_FILES_DIR = "original_files"
EXTRACTED_TEXT_DIR = "extracted_text"

# Create output directory
os.makedirs(EXTRACTED_TEXT_DIR, exist_ok=True)

# Get list of PDF files
pdf_files = glob(f"{ORIGINAL_FILES_DIR}/*.pdf")
print(f"Found {len(pdf_files)} PDF files")

# Counters
successful = 0
failed = 0
skipped = 0

# Process each PDF file
for pdf_file in tqdm(pdf_files, desc="Processing PDFs"):
    # Get the base name without extension
    basename = os.path.basename(pdf_file).replace(".pdf", "")
    output_file = f"{EXTRACTED_TEXT_DIR}/{basename}.txt"
    
    # Skip if already processed
    if os.path.exists(output_file) and os.path.getsize(output_file) > 10:
        skipped += 1
        continue
    
    print(f"\nProcessing {pdf_file}")
    
    try:
        # Open PDF in Preview and wait for it to load
        print("  Opening in Preview...")
        subprocess.run(["open", "-a", "Preview", pdf_file])
        time.sleep(3)  # Wait for Preview to open
        
        # Use AppleScript to select all and copy
        print("  Selecting all text and copying...")
        select_all_script = '''
        tell application "Preview" 
            activate
            delay 1
            tell application "System Events"
                keystroke "a" using command down
                delay 0.5
                keystroke "c" using command down
                delay 0.5
            end tell
        end tell
        '''
        subprocess.run(["osascript", "-e", select_all_script])
        
        # Get clipboard contents with pbpaste
        print("  Getting text from clipboard...")
        result = subprocess.run(["pbpaste"], capture_output=True)
        
        # Write to file
        text_content = result.stdout.decode('utf-8', errors='replace')
        print(f"  Got {len(text_content)} characters")
        
        if len(text_content) > 10:
            print(f"  Writing to {output_file}")
            with open(output_file, 'w', encoding='utf-8', errors='replace') as f:
                f.write(text_content)
                
            # Verify file was written
            if os.path.exists(output_file) and os.path.getsize(output_file) > 10:
                print(f"  Success! File written with {os.path.getsize(output_file)} bytes")
                print(f"  Sample: {text_content[:100]}")
                successful += 1
            else:
                print("  Error: File not written properly")
                failed += 1
        else:
            print("  Error: Not enough text extracted")
            failed += 1
        
        # Close Preview
        print("  Closing Preview...")
        subprocess.run(["osascript", "-e", 'tell application "Preview" to quit'])
        time.sleep(1)
        
    except Exception as e:
        print(f"  Error: {str(e)}")
        failed += 1
        
        # Try to close Preview
        try:
            subprocess.run(["osascript", "-e", 'tell application "Preview" to quit'])
        except:
            pass

# Print results
print(f"\nProcessing complete!")
print(f"Successfully processed: {successful} files")
print(f"Failed: {failed} files")
print(f"Skipped: {skipped} files")
if successful + failed > 0:
    print(f"Success rate: {successful/(successful+failed)*100:.2f}%")
