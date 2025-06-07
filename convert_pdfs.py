#!/usr/bin/env python3
"""
Standalone script to convert PDF specifications to markdown format.
Usage: python convert_pdfs.py [pdf_file_or_directory] [--vision]
"""

import sys
from pathlib import Path
from scripts.pdf_processor import process_pdf_to_markdown, batch_process_pdfs, process_pdf_with_vision

def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_pdfs.py <pdf_file_or_directory> [--vision]")
        print("Example: python convert_pdfs.py knowledge_base_src/specs/my_spec.pdf")
        print("Example: python convert_pdfs.py knowledge_base_src/specs/ --vision")
        print("\nOptions:")
        print("  --vision    Enable AI vision analysis of images in PDFs (requires API key)")
        return
    
    input_path = Path(sys.argv[1])
    use_vision = '--vision' in sys.argv
    
    if not input_path.exists():
        print(f"Error: Path does not exist: {input_path}")
        return
    
    if use_vision:
        print("🔍 Vision analysis enabled - Technical diagrams will be analyzed with AI")
    
    try:
        if input_path.is_file() and input_path.suffix.lower() == '.pdf':
            # Process single PDF file
            if use_vision:
                md_file = process_pdf_with_vision(input_path)
            else:
                md_file = process_pdf_to_markdown(input_path)
            print(f"Successfully converted: {input_path.name} -> {md_file.name}")
        elif input_path.is_dir():
            # Process all PDFs in directory
            if use_vision:
                pdf_files = list(input_path.glob("*.pdf"))
                if not pdf_files:
                    print(f"No PDF files found in {input_path}")
                    return
                
                processed_files = []
                for pdf_file in pdf_files:
                    try:
                        md_file = process_pdf_with_vision(pdf_file)
                        processed_files.append(md_file)
                    except Exception as e:
                        print(f"Failed to process {pdf_file.name}: {e}")
            else:
                processed_files = batch_process_pdfs(input_path)
            
            print(f"Successfully processed {len(processed_files)} PDF files")
            for md_file in processed_files:
                print(f"  Created: {md_file.name}")
        else:
            print(f"Error: Input must be a PDF file or directory: {input_path}")
    except Exception as e:
        print(f"Error during conversion: {e}")

if __name__ == "__main__":
    main()