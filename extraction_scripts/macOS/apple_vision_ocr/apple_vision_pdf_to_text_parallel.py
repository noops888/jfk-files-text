# apple_vision_pdf_to_text_parallel.py
import os
import subprocess
import argparse
from Cocoa import NSURL, NSData, NSBitmapImageRep
import Vision
import concurrent.futures
import time # Optional: for timing execution

def pdf_to_images(pdf_path):
    """Converts a PDF page to PNG images using pdftoppm."""
    temp_dir = f"/tmp/pdf_ocr_{os.path.basename(pdf_path)}/"
    # Use process-specific temp dir to avoid clashes if needed, though basename should be unique
    # temp_dir = f"/tmp/pdf_ocr_{os.path.basename(pdf_path)}_{os.getpid()}/"
    os.makedirs(temp_dir, exist_ok=True)
    try:
        # Increased resolution for potentially better OCR, adjust if needed
        subprocess.run([
            "pdftoppm", "-png", "-r", "300", pdf_path, os.path.join(temp_dir, "page")
        ], check=True, capture_output=True) # Capture stderr for logging if needed later
    except subprocess.CalledProcessError as e:
        print(f"Error running pdftoppm for {pdf_path}: {e.stderr.decode()}")
        # Decide how to handle pdftoppm failure: raise, return empty, etc.
        # Returning empty list will cause process_pdf to skip OCR for this file.
        return []
    except FileNotFoundError:
        print("Error: 'pdftoppm' command not found. Please install poppler.")
        raise # Cannot continue without pdftoppm
        
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
        # Options for recognition level: Fast, Accurate
        request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
        request.setUsesLanguageCorrection_(True) # Enable language correction

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
                 # Get the top candidate
                 top_candidate = observation.topCandidates_(1)
                 if top_candidate:
                     text_blocks.append(top_candidate[0].string())

        return text_blocks

    except Exception as e:
        print(f"Unexpected error during OCR for {image_path}: {e}")
        return [] # Return empty list on unexpected error

def process_pdf(pdf_path, output_dir):
    """Processes a single PDF: converts to images, OCRs pages, writes Markdown."""
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    # Use print with flush=True if output seems buffered/delayed in parallel execution
    print(f"-> Starting: {base_name}...", flush=True) 
    
    temp_dir_to_remove = f"/tmp/pdf_ocr_{os.path.basename(pdf_path)}/"
    
    try:
        output_path = os.path.join(output_dir, f"{base_name}.md")
        images = pdf_to_images(pdf_path)

        if not images:
            print(f"Warning: No images generated for {base_name}. Skipping OCR.")
            # Ensure temp dir is removed even if images fail
            if os.path.exists(temp_dir_to_remove):
                subprocess.run(["rm", "-rf", temp_dir_to_remove], check=False)
            return pdf_path # Indicate potential issue, summary logic handles counts

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# {base_name}\n\n")
            for idx, img_path in enumerate(images, 1):
                # Optional: Add progress per page
                # print(f"   Processing page {idx}/{len(images)} of {base_name}...")
                text_blocks = ocr_image(img_path)
                if text_blocks: # Only write if OCR returned something
                    f.write(f"## Page {idx}\n\n")
                    f.write("\n\n".join(text_blocks))
                    f.write("\n\n---\n\n")
                else:
                    print(f"Warning: No text found for page {idx} of {base_name}.")
                    # Ensure the f-string is on a single line
                    f.write(f"## Page {idx}\n\n*No text recognized on this page.*\n\n---\n\n")


        print(f"<- Finished: {base_name}", flush=True)
        return pdf_path # Return path on success

    except Exception as e:
        print(f"!!! Error processing {base_name} ({pdf_path}): {e}")
        # Log the full traceback here if needed: import traceback; traceback.print_exc()
        return None # Indicate failure

    finally:
        # Cleanup: Ensure temporary directory is removed
        if os.path.exists(temp_dir_to_remove):
             try:
                 subprocess.run(["rm", "-rf", temp_dir_to_remove], check=False)
             except Exception as cleanup_error:
                 print(f"Warning: Failed to remove temp directory {temp_dir_to_remove}: {cleanup_error}")

def main():
    parser = argparse.ArgumentParser(
        description="Parallel PDF to Markdown OCR Converter using Apple Vision.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter # Show defaults in help
    )
    parser.add_argument("input_dir", help="Directory containing PDF files")
    parser.add_argument("output_dir", help="Directory for Markdown output")
    parser.add_argument(
        "-w", "--workers", type=int, default=os.cpu_count(),
        help="Number of parallel processes (PDFs processed concurrently)"
    )
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    pdf_files = [
        os.path.join(args.input_dir, f)
        for f in os.listdir(args.input_dir)
        if f.lower().endswith('.pdf') and not f.startswith('.') # Ignore hidden files
    ]

    if not pdf_files:
        print(f"No PDF files found in '{args.input_dir}'.")
        return

    print(f"Found {len(pdf_files)} PDF files. Starting parallel processing with {args.workers} workers...")
    start_time = time.time() # Optional timing

    processed_count = 0
    error_count = 0

    # Use ProcessPoolExecutor to run tasks in parallel processes
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
        # Create a dictionary mapping futures to PDF paths for error reporting
        futures = {
            executor.submit(process_pdf, pdf_path, args.output_dir): pdf_path 
            for pdf_path in pdf_files
        }

        for future in concurrent.futures.as_completed(futures):
            pdf_path_submitted = futures[future]
            base_name_submitted = os.path.basename(pdf_path_submitted)
            try:
                result = future.result() # result is pdf_path on success, None on handled error
                if result is not None:
                    processed_count += 1
                else:
                    # Error was caught and handled within process_pdf
                    error_count += 1
                    # Error message printed within process_pdf
            except Exception as exc:
                # Catch unexpected errors not caught gracefully in process_pdf
                error_count += 1
                print(f'!!! UNHANDLED EXCEPTION processing {base_name_submitted}: {exc}')
                # Consider logging traceback here for debugging
                # import traceback
                # traceback.print_exc()


    end_time = time.time() # Optional timing
    total_time = end_time - start_time

    print("\n--- Processing Summary ---")
    print(f"Total PDF files found: {len(pdf_files)}")
    print(f"Successfully processed: {processed_count}")
    print(f"Encountered errors in: {error_count}")
    print(f"Total execution time: {total_time:.2f} seconds")
    print(f"Output saved to: {args.output_dir}")
    print("--------------------------")


if __name__ == "__main__":
    main() 