# apple_vision_pdf_to_text_recursive.py
import os
import subprocess
import argparse
from Cocoa import NSURL, NSData, NSBitmapImageRep
import Vision
import concurrent.futures
import time
import shutil
from pathlib import Path

def pdf_to_images(pdf_path):
    """Converts a PDF page to PNG images using pdftoppm."""
    temp_dir = f"/tmp/pdf_ocr_{os.path.basename(pdf_path)}_{os.getpid()}/"
    os.makedirs(temp_dir, exist_ok=True)
    try:
        # Increased resolution for potentially better OCR, adjust if needed
        subprocess.run([
            "pdftoppm", "-png", "-r", "300", pdf_path, os.path.join(temp_dir, "page")
        ], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running pdftoppm for {pdf_path}: {e.stderr.decode()}")
        return []
    except FileNotFoundError:
        print("Error: 'pdftoppm' command not found. Please install poppler.")
        raise
        
    image_files = sorted([
        os.path.join(temp_dir, f)
        for f in os.listdir(temp_dir) if f.lower().endswith(".png")
    ])
    return image_files

def ocr_image(image_path):
    """Performs OCR on a single image using Apple Vision."""
    try:
        image_url = NSURL.fileURLWithPath_(image_path)
        image_data = NSData.dataWithContentsOfURL_(image_url)
        if not image_data:
            print(f"Error: Could not load image data from {image_path}")
            return []

        image_rep = NSBitmapImageRep.imageRepWithData_(image_data)
        if not image_rep:
            print(f"Error: Could not create image representation for {image_path}")
            return []

        cg_image = image_rep.CGImage()
        if not cg_image:
             print(f"Error: Could not get CGImage for {image_path}")
             return []

        request = Vision.VNRecognizeTextRequest.alloc().init()
        request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
        request.setUsesLanguageCorrection_(True)

        handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, None)
        success, error = handler.performRequests_error_([request], None)

        if not success:
            print(f"OCR failed for {image_path}. Error: {error}")
            return []
        
        # Extract text from observations
        text_blocks = []
        results = request.results()
        if results:
             for observation in results:
                 top_candidate = observation.topCandidates_(1)
                 if top_candidate:
                     text_blocks.append(top_candidate[0].string())

        return text_blocks

    except Exception as e:
        print(f"Unexpected error during OCR for {image_path}: {e}")
        return []

def process_pdf(pdf_path, output_path):
    """Processes a single PDF: converts to images, OCRs pages, writes Markdown."""
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    print(f"-> Processing PDF: {pdf_path}", flush=True) 
    
    temp_dir_to_remove = f"/tmp/pdf_ocr_{os.path.basename(pdf_path)}_{os.getpid()}/"
    
    try:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        images = pdf_to_images(pdf_path)

        if not images:
            print(f"Warning: No images generated for {pdf_path}. Skipping OCR.")
            if os.path.exists(temp_dir_to_remove):
                subprocess.run(["rm", "-rf", temp_dir_to_remove], check=False)
            return pdf_path, False

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# {base_name}\n\n")
            for idx, img_path in enumerate(images, 1):
                text_blocks = ocr_image(img_path)
                if text_blocks:
                    f.write(f"## Page {idx}\n\n")
                    f.write("\n\n".join(text_blocks))
                    f.write("\n\n---\n\n")
                else:
                    print(f"Warning: No text found for page {idx} of {pdf_path}.")
                    f.write(f"## Page {idx}\n\n*No text recognized on this page.*\n\n---\n\n")

        print(f"<- Finished PDF: {output_path}", flush=True)
        return pdf_path, True

    except Exception as e:
        print(f"!!! Error processing {pdf_path}: {e}")
        return pdf_path, False

    finally:
        if os.path.exists(temp_dir_to_remove):
             try:
                 subprocess.run(["rm", "-rf", temp_dir_to_remove], check=False)
             except Exception as cleanup_error:
                 print(f"Warning: Failed to remove temp directory {temp_dir_to_remove}: {cleanup_error}")

def copy_markdown(md_path, output_path):
    """Copies a markdown file to the output directory."""
    try:
        print(f"-> Copying MD: {md_path}", flush=True)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        shutil.copy2(md_path, output_path)
        print(f"<- Finished MD: {output_path}", flush=True)
        return md_path, True
    except Exception as e:
        print(f"!!! Error copying {md_path}: {e}")
        return md_path, False

def find_files_to_process(input_dir):
    """Recursively finds all PDF and MD files in the directory tree."""
    pdf_files = []
    md_files = []
    
    for root, dirs, files in os.walk(input_dir):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            if file.startswith('.'):
                continue
                
            file_path = os.path.join(root, file)
            if file.lower().endswith('.pdf'):
                pdf_files.append(file_path)
            elif file.lower().endswith('.md'):
                md_files.append(file_path)
    
    return pdf_files, md_files

def calculate_output_path(file_path, input_dir, output_dir, new_extension=None):
    """Calculates the output path preserving directory structure."""
    rel_path = os.path.relpath(file_path, input_dir)
    if new_extension:
        base, _ = os.path.splitext(rel_path)
        rel_path = base + new_extension
    return os.path.join(output_dir, rel_path)

def main():
    parser = argparse.ArgumentParser(
        description="Recursive PDF to Markdown converter with directory structure preservation.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("input_dir", help="Root directory containing PDF and MD files")
    parser.add_argument("output_dir", help="Root directory for output")
    parser.add_argument(
        "-w", "--workers", type=int, default=os.cpu_count(),
        help="Number of parallel processes"
    )
    args = parser.parse_args()

    # Find all files to process
    print(f"Scanning directory tree: {args.input_dir}")
    pdf_files, md_files = find_files_to_process(args.input_dir)
    
    total_files = len(pdf_files) + len(md_files)
    if total_files == 0:
        print("No PDF or MD files found.")
        return
    
    print(f"\nFound {len(pdf_files)} PDF files and {len(md_files)} MD files.")
    print(f"Starting processing with {args.workers} workers...\n")
    
    start_time = time.time()
    processed_count = 0
    error_count = 0
    
    # Prepare all tasks
    tasks = []
    
    # PDF tasks
    for pdf_path in pdf_files:
        output_path = calculate_output_path(pdf_path, args.input_dir, args.output_dir, '.md')
        tasks.append(('pdf', pdf_path, output_path))
    
    # MD tasks
    for md_path in md_files:
        output_path = calculate_output_path(md_path, args.input_dir, args.output_dir)
        tasks.append(('md', md_path, output_path))
    
    # Process all tasks in parallel
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {}
        
        for task_type, input_path, output_path in tasks:
            if task_type == 'pdf':
                future = executor.submit(process_pdf, input_path, output_path)
            else:  # md
                future = executor.submit(copy_markdown, input_path, output_path)
            futures[future] = (task_type, input_path)
        
        # Collect results
        for future in concurrent.futures.as_completed(futures):
            task_type, input_path = futures[future]
            try:
                _, success = future.result()
                if success:
                    processed_count += 1
                else:
                    error_count += 1
            except Exception as exc:
                error_count += 1
                print(f'!!! UNHANDLED EXCEPTION processing {input_path}: {exc}')
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print("\n--- Processing Summary ---")
    print(f"Total files found: {total_files}")
    print(f"  - PDF files: {len(pdf_files)}")
    print(f"  - MD files: {len(md_files)}")
    print(f"Successfully processed: {processed_count}")
    print(f"Encountered errors: {error_count}")
    print(f"Total execution time: {total_time:.2f} seconds")
    print(f"Output directory: {args.output_dir}")
    print("--------------------------")

if __name__ == "__main__":
    main()