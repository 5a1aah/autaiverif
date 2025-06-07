import os
from pathlib import Path
import uuid
# Import the common_utils module itself to access its globals and functions
from . import common_utils
from .pdf_processor import extract_text_from_pdf, extract_comprehensive_pdf_content, convert_comprehensive_content_to_markdown

# Define base path for knowledge base source files
KB_SRC_PATH = Path(__file__).resolve().parent.parent / "knowledge_base_src"

# Simple chunking strategy (can be improved)
MAX_CHUNK_SIZE_CHARS = 1000 # Approximate characters
MAX_CHUNK_SIZE_LINES = 50   # For code files

def chunk_text_content(content: str) -> list[str]:
    """Simple paragraph-based chunking for text."""
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    chunks = []
    current_chunk = ""
    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 < MAX_CHUNK_SIZE_CHARS:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para + "\n\n"
    if current_chunk: # Add the last chunk
        chunks.append(current_chunk.strip())
    return chunks if chunks else [content] # Return original content if no paragraph splits

def chunk_code_content(content: str, filename: str) -> list[str]:
    """Simple line-based chunking for code, attempting to keep functions together (very basic)."""
    lines = content.splitlines()
    chunks = []
    current_chunk_lines = []
    for i, line in enumerate(lines):
        current_chunk_lines.append(line)
        if len(current_chunk_lines) >= MAX_CHUNK_SIZE_LINES or \
           (line.strip() == "}" and i + 1 < len(lines) and lines[i+1].strip() == ""): # End of a block
            chunks.append("\n".join(current_chunk_lines))
            current_chunk_lines = []
    if current_chunk_lines: # Add remaining lines
        chunks.append("\n".join(current_chunk_lines))
    return chunks if chunks else [content]

def extract_content_from_file(file_path: Path) -> str:
    """
    Extract content from different file types including PDFs.
    Returns the text content of the file.
    """
    file_extension = file_path.suffix.lower()
    
    if file_extension == '.pdf':
        print(f"Processing PDF file: {file_path.name}")
        try:
            # Check if we should use vision analysis (configurable via environment)
            use_vision = os.getenv('USE_PDF_VISION', 'false').lower() == 'true'
            
            if use_vision:
                print(f"  Using vision analysis for {file_path.name}")
                # Use comprehensive content extraction with image analysis
                content_dict = extract_comprehensive_pdf_content(file_path)
                # Convert to markdown format for better chunking
                content = convert_comprehensive_content_to_markdown(content_dict)
            else:
                print(f"  Using text-only extraction for {file_path.name}")
                # Use simple text extraction
                content = extract_text_from_pdf(file_path)
            
            return content
            
        except Exception as e:
            print(f"Error extracting content from PDF {file_path}: {e}")
            return ""
    else:
        # Handle regular text files
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return ""

def process_and_add_file(file_path: Path, doc_type: str):
    """Reads a file (including PDFs), chunks it, and adds chunks to ChromaDB."""
    print(f"Processing file: {file_path} (Type: {doc_type})")
    
    # Extract content using the enhanced function
    content = extract_content_from_file(file_path)
    
    if not content.strip():
        print(f"Skipping empty or unreadable file: {file_path}")
        return

    # Determine chunking strategy based on file type and doc_type
    if doc_type in ["spec", "regmap", "hal_doc"] or file_path.suffix.lower() == '.pdf':
        chunks = chunk_text_content(content)
    elif doc_type in ["c_example", "hal_code"]:
        chunks = chunk_code_content(content, file_path.name)
    else:
        print(f"Unknown document type '{doc_type}' for file {file_path}. Using default text chunking.")
        chunks = chunk_text_content(content)

    documents_to_add = []
    metadatas_to_add = []
    ids_to_add = []

    for i, chunk_content in enumerate(chunks):
        if not chunk_content.strip():
            continue
        documents_to_add.append(chunk_content)
        metadatas_to_add.append({
            "source_file": file_path.name,
            "doc_type": doc_type,
            "chunk_index": i,
            "file_type": file_path.suffix.lower()  # Add file type metadata
        })
        ids_to_add.append(f"{file_path.name}_{doc_type}_{i}_{uuid.uuid4()}")

    if documents_to_add:
        try:
            # Critical: Access kb_collection through the common_utils module
            if common_utils.kb_collection is None:
                print(f"Error: common_utils.kb_collection is None. Cannot add documents from {file_path.name}.")
                return

            common_utils.kb_collection.add(
                documents=documents_to_add,
                metadatas=metadatas_to_add,
                ids=ids_to_add
            )
            print(f"Added {len(documents_to_add)} chunks from {file_path.name} to ChromaDB.")
        except Exception as e:
            print(f"Error adding document chunks from {file_path.name} to ChromaDB: {e}")

def populate_knowledge_base():
    """
    Initializes the ChromaDB client and collection via common_utils,
    then processes and adds documents from the knowledge base source path.
    """
    # Ensure client and collection are ready and assigned in common_utils
    # This function in common_utils now handles the global assignment of kb_collection
    common_utils.initialize_chromadb_client_and_collection() 

    # Now, check if kb_collection in common_utils was successfully initialized
    if common_utils.kb_collection is None:
        print("Error: ChromaDB collection could not be initialized (common_utils.kb_collection is None). Aborting KB population.")
        return

    doc_type_map = {
        "specs": "spec",
        "hal": "hal_doc",
        "regmaps": "regmap",
        "c_test_examples": "c_example"
    }
    hal_code_extensions = {".h", ".c"}

    for dir_name, doc_type_default in doc_type_map.items():
        dir_path = KB_SRC_PATH / dir_name
        if not dir_path.exists():
            print(f"Warning: Directory not found {dir_path}, skipping.")
            continue

        print(f"\nProcessing directory: {dir_path}")
        for file_path in dir_path.rglob('*'):
            if file_path.is_file():
                doc_type = doc_type_default
                if dir_name == "hal" and file_path.suffix in hal_code_extensions:
                    doc_type = "hal_code"
                process_and_add_file(file_path, doc_type)
    
    print("\nKnowledge base population process finished.")
    # Check the collection count via common_utils
    if common_utils.kb_collection:
        print(f"Total items in '{common_utils.kb_collection.name}' collection: {common_utils.kb_collection.count()}")
    else:
        print("Could not get collection count as common_utils.kb_collection is None.")


if __name__ == "__main__":
    print("Starting Knowledge Base Population Script...")
    # Example files to have in knowledge_base_src for testing:
    # knowledge_base_src/specs/my_asic_spec.txt
    # knowledge_base_src/hal/my_hal_functions.h
    # knowledge_base_src/c_test_examples/example_test1.c
    populate_knowledge_base()
    print("Knowledge Base Population Script Ended.")
