import os
import glob
import sys
import re

def count_files(directory, extension):
    # Method 1: Using glob with specific pattern (case insensitive)
    glob_files = glob.glob(os.path.join(directory, f'DOCID-*.{extension}')) + \
                 glob.glob(os.path.join(directory, f'DOCID-*.{extension.upper()}'))
    
    # Method 2: Using os.listdir with validation (case insensitive)
    all_files = os.listdir(directory)
    listdir_files = [f for f in all_files if f.startswith('DOCID-') and 
                    (f.lower().endswith(f'.{extension.lower()}'))]
    
    # Method 3: Using os.scandir with validation (case insensitive)
    scandir_files = []
    with os.scandir(directory) as it:
        for entry in it:
            if entry.name.startswith('DOCID-') and \
               entry.name.lower().endswith(f'.{extension.lower()}'):
                scandir_files.append(entry.name)
    
    # Print debugging information
    print(f"\nDebug information for DOCID-*.{extension} files (case insensitive):")
    print(f"glob count: {len(glob_files)}")
    print(f"listdir count: {len(listdir_files)}")
    print(f"scandir count: {len(scandir_files)}")
    
    # Extract and analyze DOCIDs
    docids = []
    for f in listdir_files:
        match = re.match(r'DOCID-(\d+)\.' + extension, f, re.IGNORECASE)
        if match:
            docids.append(int(match.group(1)))
    
    if docids:
        print(f"\nDOCID range: {min(docids)} to {max(docids)}")
        print(f"Number of unique DOCIDs: {len(set(docids))}")
    
    # If there are discrepancies, show the differences
    if len(glob_files) != len(listdir_files):
        glob_names = {os.path.basename(f) for f in glob_files}
        listdir_names = set(listdir_files)
        diff = listdir_names - glob_names
        if diff:
            print(f"\nFiles found by listdir but not glob:")
            for f in sorted(diff):
                print(f"  {f}")
    
    # Validate file names
    invalid_files = [f for f in listdir_files if not f.startswith('DOCID-')]
    if invalid_files:
        print(f"\nWARNING: Found files that don't match DOCID- pattern:")
        for f in sorted(invalid_files):
            print(f"  {f}")
    
    # Print first and last few files
    print(f"\nFirst 5 files:")
    for f in sorted(listdir_files)[:5]:
        print(f"  {f}")
    print(f"\nLast 5 files:")
    for f in sorted(listdir_files)[-5:]:
        print(f"  {f}")
    
    return listdir_files  # Use listdir as it's most likely to match the GUI

# Get all PDF files in original_files
pdf_files = count_files('./original_files', 'pdf')
pdf_basenames = [os.path.splitext(f)[0] for f in pdf_files]

# Get all TXT files in extracted_text
txt_files = count_files('./extracted_text', 'md')
txt_basenames = [os.path.splitext(f)[0] for f in txt_files]

# Find PDFs without corresponding TXT files
missing_txt = set(pdf_basenames) - set(txt_basenames)

# Print results
print(f"\nResults:")
print(f"Total PDFs: {len(pdf_basenames)}")
print(f"Total TXTs: {len(txt_basenames)}")
print(f"Missing TXT files: {len(missing_txt)}")

if missing_txt:
    print("\nMissing files:")
    for filename in sorted(missing_txt):
        print(f"{filename}.pdf")
