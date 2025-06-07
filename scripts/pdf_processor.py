import fitz  # PyMuPDF
from pathlib import Path
import re
from typing import List, Dict, Tuple
import os
import base64
import io
from PIL import Image
import requests
import json

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

def extract_images_from_pdf(pdf_path: Path) -> List[Dict]:
    """
    Extract images from PDF file with their page numbers and positions.
    Returns list of dicts with image data, page info, and metadata.
    """
    try:
        doc = fitz.open(pdf_path)
        images = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            image_list = page.get_images(full=True)
            
            for img_index, img in enumerate(image_list):
                # Get image data
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                
                # Convert to PIL Image for better handling
                if pix.n - pix.alpha < 4:  # GRAY or RGB
                    img_data = pix.tobytes("png")
                    pil_image = Image.open(io.BytesIO(img_data))
                    
                    # Skip very small images (likely logos or decorative elements)
                    if pil_image.width < 100 or pil_image.height < 100:
                        pix = None
                        continue
                    
                    # Convert to base64 for API transmission
                    buffer = io.BytesIO()
                    pil_image.save(buffer, format='PNG')
                    img_base64 = base64.b64encode(buffer.getvalue()).decode()
                    
                    # Get image position and size
                    img_rects = page.get_image_rects(img)
                    rect = img_rects[0] if img_rects else fitz.Rect(0, 0, 100, 100)
                    
                    images.append({
                        'page': page_num + 1,
                        'index': img_index,
                        'base64': img_base64,
                        'format': 'png',
                        'width': pix.width,
                        'height': pix.height,
                        'position': {
                            'x0': rect.x0,
                            'y0': rect.y0, 
                            'x1': rect.x1,
                            'y1': rect.y1
                        },
                        'size_bytes': len(img_data)
                    })
                
                pix = None  # Free memory
        
        doc.close()
        return images
        
    except Exception as e:
        print(f"Error extracting images from PDF {pdf_path}: {e}")
        return []

def analyze_image_with_llm(image_base64: str, context: str = "", page_text: str = "") -> str:
    """
    Send image to LLM for analysis and description.
    Uses OpenRouter API with vision-capable models.
    """
    from . import common_utils
    
    # Use vision-capable models in order of preference
    vision_models = [
        "meta-llama/llama-4-maverick:free",
        "openai/gpt-4o", 
        "google/gemini-pro-vision"
    ]
    
    headers = {
        "Authorization": f"Bearer {common_utils.OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Create enhanced prompt with context
    analysis_prompt = f"""Analyze this technical diagram/image from an ASIC specification document. 

Context: {context}

Page text context: {page_text[:500] if page_text else "No surrounding text available"}

Please provide a detailed technical description including:
1. Type of diagram (block diagram, timing chart, register layout, state machine, etc.)
2. Key components, signals, interfaces, or data structures shown
3. Register layouts, bit fields, memory maps, or address spaces if visible
4. Timing relationships, clock domains, or signal dependencies
5. State transitions, control flow, or operational modes
6. Pin assignments, interconnections, or bus structures
7. Any numerical values, specifications, or technical parameters
8. Text labels, signal names, or annotations visible in the image
9. How this relates to ASIC verification and testing requirements

Format your response as structured technical documentation suitable for verification engineers."""

    for model in vision_models:
        try:
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": analysis_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 1500,
                "temperature": 0.1
            }
            
            response = requests.post(
                common_utils.OPENROUTER_API_URL,
                headers=headers,
                json=payload,
                timeout=90
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                print(f"Model {model} failed with status {response.status_code}: {response.text}")
                continue
                
        except Exception as e:
            print(f"Error with model {model}: {e}")
            continue
    
    return "Failed to analyze image with available vision models. This image contains technical content that requires manual review."

def extract_page_text_around_images(page, image_rects: List) -> str:
    """
    Extract text content around image locations to provide context.
    """
    try:
        page_text = page.get_text()
        # For now, return the full page text as context
        # In future, could implement more sophisticated text extraction around image positions
        return page_text[:1000]  # Limit context length
    except:
        return ""

def extract_comprehensive_pdf_content(pdf_path: Path) -> Dict:
    """
    Extract both text and images from PDF, analyze images with LLM.
    Returns comprehensive content including analyzed images.
    """
    print(f"Extracting comprehensive content from: {pdf_path.name}")
    
    # Extract text content
    text_content = extract_text_from_pdf(pdf_path)
    cleaned_text = clean_and_format_text(text_content)
    
    # Extract images
    images = extract_images_from_pdf(pdf_path)
    print(f"Found {len(images)} analyzable images in PDF")
    
    # Analyze images with LLM
    analyzed_images = []
    doc = fitz.open(pdf_path)
    
    for i, img_data in enumerate(images):
        print(f"Analyzing image {i+1}/{len(images)} from page {img_data['page']} ({img_data['width']}x{img_data['height']} px)")
        
        # Get page context
        page = doc.load_page(img_data['page'] - 1)
        page_context = extract_page_text_around_images(page, [])
        
        # Create context description
        context = f"Image from page {img_data['page']} of {pdf_path.stem}, located at position ({img_data['position']['x0']:.0f},{img_data['position']['y0']:.0f})"
        
        try:
            # Analyze image with vision model
            analysis = analyze_image_with_llm(img_data['base64'], context, page_context)
            
            analyzed_images.append({
                **img_data,
                'analysis': analysis,
                'page_context': page_context[:200],  # Store limited context
                'analyzed': True
            })
            
        except Exception as e:
            print(f"Failed to analyze image {i+1}: {e}")
            analyzed_images.append({
                **img_data,
                'analysis': f"Analysis failed: {str(e)}",
                'page_context': page_context[:200],
                'analyzed': False
            })
    
    doc.close()
    
    return {
        'text_content': cleaned_text,
        'images': analyzed_images,
        'total_pages': len(fitz.open(pdf_path)),
        'source_file': str(pdf_path),
        'has_vision_analysis': len([img for img in analyzed_images if img['analyzed']]) > 0
    }

def convert_comprehensive_content_to_markdown(content: Dict) -> str:
    """
    Convert comprehensive PDF content (text + analyzed images) to markdown.
    """
    title = Path(content['source_file']).stem.replace('_', ' ').title()
    markdown_content = f"# {title}\n\n"
    markdown_content += f"*Extracted from: {Path(content['source_file']).name}*\n\n"
    
    if content['has_vision_analysis']:
        markdown_content += f"*✅ Enhanced with AI vision analysis of {len(content['images'])} technical diagrams*\n\n"
    
    # Add text content
    if content['text_content']:
        markdown_content += "## Document Text Content\n\n"
        markdown_content += convert_to_markdown(content['text_content']) + "\n\n"
    
    # Add analyzed images
    if content['images']:
        markdown_content += "## Technical Diagrams and Visual Analysis\n\n"
        markdown_content += f"*This document contains {len(content['images'])} technical diagrams/images analyzed by AI vision models*\n\n"
        
        for i, img in enumerate(content['images']):
            markdown_content += f"### Visual Element {i+1} - Page {img['page']}\n\n"
            markdown_content += f"**Image Properties:**\n"
            markdown_content += f"- Dimensions: {img['width']} × {img['height']} pixels\n"
            markdown_content += f"- Location: Page {img['page']}, position ({img['position']['x0']:.0f}, {img['position']['y0']:.0f})\n"
            markdown_content += f"- Size: {img['size_bytes']:,} bytes\n"
            markdown_content += f"- Analysis Status: {'✅ Analyzed' if img['analyzed'] else '❌ Failed'}\n\n"
            
            if img.get('page_context'):
                markdown_content += f"**Surrounding Text Context:**\n"
                markdown_content += f"```\n{img['page_context']}\n```\n\n"
            
            markdown_content += f"**AI Vision Analysis:**\n\n"
            markdown_content += f"{img['analysis']}\n\n"
            markdown_content += "---\n\n"
    
    return markdown_content

def process_pdf_with_vision(pdf_path: Path, output_dir: Path = None) -> Path:
    """
    Enhanced PDF processing with vision analysis of images.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    print(f"🔍 Processing PDF with AI vision analysis: {pdf_path.name}")
    
    # Extract comprehensive content
    content = extract_comprehensive_pdf_content(pdf_path)
    
    if not content['images']:
        print(f"⚠️  No analyzable images found in {pdf_path.name}")
    
    # Convert to markdown
    markdown_content = convert_comprehensive_content_to_markdown(content)
    
    # Determine output path
    if output_dir is None:
        output_dir = pdf_path.parent
    
    output_path = output_dir / f"{pdf_path.stem}_with_vision.md"
    
    # Save markdown file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"✅ Enhanced markdown file created: {output_path}")
        return output_path
    except Exception as e:
        print(f"❌ Error saving markdown file: {e}")
        raise

if __name__ == "__main__":
    # Example usage
    pdf_dir = Path("../knowledge_base_src/specs")
    if pdf_dir.exists():
        processed = batch_process_pdfs(pdf_dir)
        print(f"Processed {len(processed)} PDF files")