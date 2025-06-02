import fitz  # PyMuPDF
from pathlib import Path
import re
from typing import List, Dict
import os

def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extract text content from PDF file using PyMuPDF.
    """
    try:
        doc = fitz.open(pdf_path)
        text_content = ""
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text_content += f"\n\n--- Page {page_num + 1} ---\n\n"
            text_content += page.get_text()
        
        doc.close()
        return text_content
    except Exception as e:
        print(f"Error extracting text from PDF {pdf_path}: {e}")
        return ""

def clean_and_format_text(raw_text: str) -> str:
    """
    Clean and format extracted PDF text to improve markdown conversion.
    """
    # Remove excessive whitespace
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', raw_text)
    
    # Fix common PDF extraction issues
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # Add space between camelCase
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    text = re.sub(r'\n ', '\n', text)  # Remove leading spaces after newlines
    
    return text.strip()

def convert_to_markdown(text: str, title: str = None) -> str:
    """
    Convert cleaned text to markdown format with basic structure.
    """
    markdown_content = ""
    
    if title:
        markdown_content += f"# {title}\n\n"
    
    lines = text.split('\n')
    in_code_block = False
    
    for line in lines:
        line = line.strip()
        
        if not line:
            markdown_content += "\n"
            continue
            
        # Detect headers (lines that are all caps or start with numbers)
        if re.match(r'^[A-Z\s\d\.]+$', line) and len(line) > 3:
            markdown_content += f"\n## {line}\n\n"
        # Detect numbered sections
        elif re.match(r'^\d+\.\d*\s+', line):
            markdown_content += f"\n### {line}\n\n"
        # Detect bullet points
        elif line.startswith(('•', '-', '*')):
            markdown_content += f"* {line[1:].strip()}\n"
        # Detect code-like content (contains specific keywords)
        elif any(keyword in line.lower() for keyword in ['register', 'bit', 'field', 'address', '0x']):
            if not in_code_block:
                markdown_content += "\n```\n"
                in_code_block = True
            markdown_content += f"{line}\n"
        else:
            if in_code_block:
                markdown_content += "```\n\n"
                in_code_block = False
            markdown_content += f"{line}\n\n"
    
    if in_code_block:
        markdown_content += "```\n"
    
    return markdown_content

def process_pdf_to_markdown(pdf_path: Path, output_dir: Path = None) -> Path:
    """
    Convert PDF file to markdown and save it.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    print(f"Processing PDF: {pdf_path.name}")
    
    # Extract text from PDF
    raw_text = extract_text_from_pdf(pdf_path)
    if not raw_text:
        raise ValueError(f"No text extracted from PDF: {pdf_path}")
    
    # Clean and format text
    cleaned_text = clean_and_format_text(raw_text)
    
    # Convert to markdown
    title = pdf_path.stem.replace('_', ' ').title()
    markdown_content = convert_to_markdown(cleaned_text, title)
    
    # Determine output path
    if output_dir is None:
        output_dir = pdf_path.parent
    
    output_path = output_dir / f"{pdf_path.stem}.md"
    
    # Save markdown file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"Markdown file created: {output_path}")
        return output_path
    except Exception as e:
        print(f"Error saving markdown file: {e}")
        raise

def batch_process_pdfs(pdf_directory: Path, output_directory: Path = None) -> List[Path]:
    """
    Process all PDF files in a directory.
    """
    if not pdf_directory.exists():
        raise FileNotFoundError(f"Directory not found: {pdf_directory}")
    
    pdf_files = list(pdf_directory.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {pdf_directory}")
        return []
    
    processed_files = []
    for pdf_file in pdf_files:
        try:
            md_file = process_pdf_to_markdown(pdf_file, output_directory)
            processed_files.append(md_file)
        except Exception as e:
            print(f"Failed to process {pdf_file.name}: {e}")
    
    return processed_files

if __name__ == "__main__":
    # Example usage
    pdf_dir = Path("../knowledge_base_src/specs")
    if pdf_dir.exists():
        processed = batch_process_pdfs(pdf_dir)
        print(f"Processed {len(processed)} PDF files")