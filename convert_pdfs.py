#!/usr/bin/env python3
"""
Standalone script to convert PDF specifications to markdown format.
Usage: python convert_pdfs.py [pdf_file_or_directory]
"""

import sys
from pathlib import Path
from scripts.pdf_processor import process_pdf_to_markdown, batch_process_pdfs

def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_pdfs.py <pdf_file_or_directory>")
        print("Example: python convert_pdfs.py knowledge_base_src/specs/my_spec.pdf")
        print("Example: python convert_pdfs.py knowledge_base_src/specs/")
        return
    
    input_path = Path(sys.argv[1])
    
    if not input_path.exists():
        print(f"Error: Path does not exist: {input_path}")
        return
    
    try:
        if input_path.is_file() and input_path.suffix.lower() == '.pdf':
            # Process single PDF file
            md_file = process_pdf_to_markdown(input_path)
            print(f"Successfully converted: {input_path.name} -> {md_file.name}")
        elif input_path.is_dir():
            # Process all PDFs in directory
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