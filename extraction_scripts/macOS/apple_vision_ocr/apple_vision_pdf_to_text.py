import os
import subprocess
import argparse
from Cocoa import NSURL, NSData, NSBitmapImageRep
import Vision

def pdf_to_images(pdf_path):
    temp_dir = f"/tmp/pdf_ocr_{os.path.basename(pdf_path)}/"
    os.makedirs(temp_dir, exist_ok=True)
    subprocess.run([
        "pdftoppm", "-png", "-r", "300", pdf_path, f"{temp_dir}page"
    ], check=True)
    return sorted([f"{temp_dir}{f}" for f in os.listdir(temp_dir) if f.endswith(".png")])

def ocr_image(image_path):
    image_url = NSURL.fileURLWithPath_(image_path)
    image_data = NSData.dataWithContentsOfURL_(image_url)
    image_rep = NSBitmapImageRep.imageRepWithData_(image_data)
    cg_image = image_rep.CGImage()

    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    request.setUsesLanguageCorrection_(True)

    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, None)
    success = handler.performRequests_error_([request], None)

    if not success:
        print(f"OCR failed for {image_path}")
        return []

    return [obs.topCandidates_(1)[0].string() for obs in request.results() if obs.topCandidates_(1)]

def process_pdf(pdf_path, output_dir):
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}.md")
    
    print(f"Processing {base_name}...")
    images = pdf_to_images(pdf_path)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# {base_name}\n\n")
        for idx, img_path in enumerate(images, 1):
            text_blocks = ocr_image(img_path)
            f.write(f"## Page {idx}\n\n")
            f.write("\n\n".join(text_blocks))
            f.write("\n\n---\n\n")
    
    subprocess.run(["rm", "-rf", f"/tmp/pdf_ocr_{os.path.basename(pdf_path)}"], check=False)
    print(f"Completed processing {base_name}")

def main():
    parser = argparse.ArgumentParser(description="PDF to Markdown OCR Converter")
    parser.add_argument("input_dir", help="Directory containing PDF files")
    parser.add_argument("output_dir", help="Directory for Markdown output")
    args = parser.parse_args()
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    for filename in os.listdir(args.input_dir):
        if filename.lower().endswith('.pdf'):
            pdf_path = os.path.join(args.input_dir, filename)
            process_pdf(pdf_path, args.output_dir)

if __name__ == "__main__":
    print("Starting OCR processing...")
    main()
    print("Operation completed successfully")
