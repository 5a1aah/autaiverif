# ASIC Verification Automation with LLMs and RAG

This project automates parts of the ASIC verification workflow by leveraging Large Language Models (LLMs) via the OpenRouter API, specifically using models like DeepSeek V3. It employs Retrieval Augmented Generation (RAG) to provide context from your project-specific documents, enabling the generation of:

1.  **Verification Plans:** Detailed test plans based on ASIC specifications and features with automatic format validation and regeneration.
2.  **C Test Code:** C test functions derived from the verification plan and guided by example C test files and Hardware Abstraction Layer (HAL) information.
3.  **PDF Processing:** Automatic conversion of PDF specifications to markdown format for seamless integration into the knowledge base.

The goal is to accelerate the verification process, assist engineers in drafting documentation and test code, and ensure consistency by grounding generation in project-specific knowledge.

## Features

### Core Automation Features
* **Automated Verification Plan Generation:** Creates comprehensive test plans with test IDs, descriptions, stimuli, expected outcomes, and coverage points.
* **Automated C Test Code Generation:** Generates C test functions using specific HAL details and referencing provided C test examples for style and structure.
* **Individual Test Regeneration:** Ability to regenerate specific test cases without regenerating the entire test suite.
* **PDF to Markdown Conversion:** Automatically converts PDF specifications to markdown format for knowledge base integration.
* **Feature Extraction from Specifications:** Automatically extracts design features from ASIC specification documents with categorization and priority assignment.
* **Comprehensive Verification Generation:** End-to-end automation that extracts features, generates verification plans, creates test files, and produces Excel reports for all features in one command.

### Quality Assurance Features
* **Automatic Format Validation:** Validates verification plans and C tests for correct format and structure.
* **Intelligent Regeneration:** Automatically regenerates incorrectly formatted verification plans with enhanced prompts.
* **Error Handling and Recovery:** Robust error handling with graceful fallback mechanisms.
* **Validation Reports:** Detailed feedback on plan validity, warnings, and suggestions for improvement.
* **Multi-Format Output:** Supports JSON, CSV, and human-readable text formats for extracted features.
* **Comprehensive Reporting:** Generates detailed summary reports with statistics and categorization of all generated artifacts.

### Technical Features
* **Retrieval Augmented Generation (RAG):** Utilizes a local vector database (ChromaDB) to retrieve relevant information from your ASIC specifications, HAL documentation, register maps, and C test examples.
* **Example-Driven Code Generation:** Uses existing C test examples from your knowledge base to guide the LLM in generating new tests with consistent style and structure.
* **Configurable Prompts:** Allows customization of prompts used to interact with the LLM for both stages.
* **Modular Architecture:** Organized into separate Python scripts for each major task with clear separation of concerns.
* **Enhanced Token Limits:** Optimized token allocation for better generation quality (4096 tokens for complex operations).
* **Intelligent Feature Extraction:** Advanced algorithms to automatically identify and categorize design features from specification documents.
* **Batch Processing:** Efficient processing of multiple features with parallel execution and progress tracking.
* **Flexible Output Modes:** Support for both unified verification plans (single comprehensive plan) and individual feature-specific plans.

## Project Structure
asic_verification_automation/
├── knowledge_base_src/       # Your raw documents for RAG
│   ├── specs/                # ASIC specification documents (.txt, .md)
│   ├── hal/                  # HAL documentation, .h files (.txt, .md, .h)
│   ├── regmaps/              # Register map details (.txt, .csv, .md)
│   └── c_test_examples/      # Example C test files (.c)
├── vector_db/                # Persistent storage for ChromaDB (created automatically)
├── generated_outputs/
│   ├── verification_plans/   # Output: Generated verification plans
│   ├── c_tests/              # Output: Generated C test files
│   ├── excel_reports/        # Output: Excel format verification reports
│   ├── extracted_features/   # Output: Extracted features in JSON/CSV/text formats
│   └── comprehensive_verification/ # Output: Complete verification artifacts
├── scripts/
│   ├── 01_populate_kb.py     # Processes docs and builds the vector DB
│   ├── 02_generate_verif_plan.py # Generates verification plans
│   ├── 03_generate_c_tests.py    # Generates C tests
│   ├── feature_extractor.py  # Extracts features from specifications
│   ├── batch_processor.py    # Batch processing utilities
│   ├── unified_generator.py  # Unified verification generation
│   ├── common_utils.py       # Helper functions (API calls, RAG retrieval, etc.)
│   └── __init__.py           # Makes 'scripts' a package
├── prompts/                  # Prompt templates for the LLM
│   ├── stage1_verif_plan_prompt.txt
│   └── stage2_c_test_gen_prompt.txt
├── main_orchestrator.py      # Main CLI script to run the project
├── requirements.txt          # Python dependencies
└── README.md                 # This file
## Requirements

### Software
* Python 3.8 or newer
* `pip` (Python package installer)
* Git (recommended for version control)

### Python Libraries
These are listed in `requirements.txt` and can be installed using `pip`:
* `requests` - HTTP requests for API calls
* `sentence-transformers` - Text embeddings for RAG
* `chromadb` - Vector database for knowledge storage
* `pandas` - Data manipulation for Excel reports
* `openpyxl` - Excel file generation
* `PyMuPDF>=1.23.0` - PDF processing and text extraction

### API Key
* An **OpenRouter API Key** is required to use the LLM (e.g., DeepSeek V3). You can get one from [OpenRouter.ai](https://openrouter.ai/).

## Setup Instructions

### 1. Clone or Download the Project
```bash
# If using Git
git clone <repository_url>
cd asic_verification_automation

### 2. Create and Activate a Python Virtual Environment (Recommended)
```
python -m venv venv
```
Activate the environment:

- Windows: .\venv\Scripts\activate
- macOS/Linux: source venv/bin/activate
### 3. Install Python Dependencies
```
pip install -r requirements.
txt
```
### 4. Configure OpenRouter API Key

The system now supports multiple ways to configure your API key and model settings:

#### Method 1: Environment Variables (Recommended)
Set environment variables for global configuration:

**Windows PowerShell:**
```powershell
$env:OPENROUTER_API_KEY = "sk-or-v1-your-actual-api-key-here"
$env:DEEPSEEK_MODEL_NAME_DEFAULT = "deepseek/deepseek-chat-v3-0324:free"
```

**Linux/macOS:**
```bash
export OPENROUTER_API_KEY="sk-or-v1-your-actual-api-key-here"
export DEEPSEEK_MODEL_NAME_DEFAULT="deepseek/deepseek-chat-v3-0324:free"
```

**Windows Command Prompt:**
```cmd
set OPENROUTER_API_KEY=sk-or-v1-your-actual-api-key-here
set DEEPSEEK_MODEL_NAME_DEFAULT=deepseek/deepseek-chat-v3-0324:free
```

#### Method 2: Command Line Arguments (Per-Command Basis)
All commands now support API key configuration via command line arguments:

```bash
# Using API key arguments for plan generation
python main_orchestrator.py gen_plan "test feature" --openrouter-key "sk-or-v1-your-key" --deepseek-model "deepseek/deepseek-chat-v3-0324:free"

# Using API key arguments for test generation
python main_orchestrator.py gen_tests --plan_file "path/to/plan.md" --openrouter-key "sk-or-v1-your-key" --deepseek-model "deepseek/deepseek-chat-v3-0324:free"
```

#### Method 3: Global Arguments (For All Subcommands)
You can also specify API configuration at the top level:

```bash
python main_orchestrator.py --openrouter-key "sk-or-v1-your-key" --deepseek-model "deepseek/deepseek-chat-v3-0324:free" gen_plan "test feature"
```

#### Method 4: Direct Configuration (Fallback)
Edit `scripts/common_utils.py` and update the API key (not recommended for production):

```python
OPENROUTER_API_KEY = "sk-or-v1-your-actual-api-key-here"
DEEPSEEK_MODEL_NAME_DEFAULT = "deepseek/deepseek-chat-v3-0324:free"
```

#### Priority Order
The system resolves API configuration in the following priority order:
1. Command line arguments (`--openrouter-key`, `--deepseek-model`)
2. Environment variables (`OPENROUTER_API_KEY`, `DEEPSEEK_MODEL_NAME_DEFAULT`)
3. Hardcoded defaults in `common_utils.py`

### 5. Populate the Knowledge Base
This is a critical step for quality output. The system supports multiple document formats:
 Supported File Formats
- Specifications: .txt , .md , .pdf
- HAL Documentation: .txt , .md , .h
- Register Maps: .txt , .csv , .md
- C Test Examples: .c Directory Structure
```
knowledge_base_src/
├── specs/              # 
Add your ASIC specification 
documents here
├── hal/                # 
Add HAL documentation and .h 
files here
├── regmaps/            # 
Add register map details here
└── c_test_examples/    # 
Add well-written C test 
examples here
``` PDF Processing
The system automatically converts PDF files to markdown format:

- Place PDF specifications in the appropriate directories
- Run the knowledge base population script
- PDFs will be automatically converted and processed
### 6. Initialize the Knowledge Base
```
python scripts/populate_kb.py
```
This will:

- Process all documents in knowledge_base_src/
- Convert PDF files to markdown automatically
- Create embeddings and store them in the vector database
- Display progress and statistics
## Usage Guide
### Main Orchestrator Commands
All operations use main_orchestrator.py from the project root:

```
python main_orchestrator.py 
<command> [options]
```
### Available Commands 1. Generate Verification Plan
```
python main_orchestrator.py 
generate_plan --feature 
"CLINT machine level timer 
interrupts"
```
Features:

- Automatic format validation
- Intelligent regeneration on format errors (up to 3 attempts)
- Enhanced prompts for retry attempts
- Detailed validation feedback 2. Generate C Tests from Plan
```
python main_orchestrator.py 
generate_tests --plan_file 
"generated_outputs/
verification_plans/
verif_plan_CLINT_machine_leve
l_timer_interrupts.md"
```
Features:

- Automatic validation of generated tests
- Individual test regeneration capability
- Enhanced error handling and recovery
- Temporary file management for safe regeneration 3. Regenerate Individual Test
```
python main_orchestrator.py 
regenerate_test --test_file 
"generated_outputs/c_tests/
test_mtip_001.c" --plan_file 
"generated_outputs/
verification_plans/
verif_plan_CLINT_machine_leve
l_timer_interrupts.md"
```
Features:

- Focused regeneration of specific test cases
- Maintains consistency with original verification plan
- Validates regenerated test before replacement 4. Convert Verification Plan to Excel
```
python main_orchestrator.py 
plan_to_excel --plan_file 
"generated_outputs/
verification_plans/
verif_plan_CLINT_machine_leve
l_timer_interrupts.md"
``` 5. Update Knowledge Base
```
python main_orchestrator.py 
update_kb
```
Re-processes all documents in knowledge_base_src/ including new PDF files.

### PDF Conversion Utilities Standalone PDF Conversion
```
# Convert single PDF file
python convert_pdfs.py 
knowledge_base_src/specs/
my_specification.pdf

# Convert all PDFs in a 
directory
python convert_pdfs.py 
knowledge_base_src/specs/
``` Automatic PDF Processing
PDF files are automatically processed during knowledge base population:

```
python scripts/populate_kb.py
```
### Advanced Usage Custom Prompt Templates
Modify prompt templates in the prompts/ directory:

- stage1_verif_plan_prompt.txt - Verification plan generation
- stage2_c_test_gen_prompt.txt - C test code generation API Configuration
Update API settings in scripts/common_utils.py :

```
OPENROUTER_API_KEY = 
"your_api_key"
OPENROUTER_API_URL = 
"https://openrouter.ai/api/
v1/chat/completions"
DEEPSEEK_MODEL_NAME_DEFAULT 
= "deepseek/
deepseek-chat:free"
``` Token Limits and Quality

The system uses optimized token limits:

- Verification Plans: 4096 tokens
- C Test Generation: 4096 tokens
- Temperature: 0.3 for deterministic output
## Quality Assurance Features
### Automatic Validation
- Verification Plans: Validates format, required fields, and structure
- C Tests: Checks for compilation readiness and HAL function usage
- Error Recovery: Automatic regeneration with enhanced prompts
### Regeneration Mechanisms
- Plan Regeneration: Up to 3 attempts with improved guidance
- Test Regeneration: Individual test case regeneration
- Validation Feedback: Detailed reports on issues and suggestions
### Best Practices
1. High-Quality Examples: Provide well-written C test examples in the knowledge base
2. Comprehensive Specifications: Include detailed ASIC specifications and register maps
3. HAL Documentation: Ensure complete HAL function documentation
4. Regular Updates: Update the knowledge base when specifications change
5. Validation Review: Always review generated content before use
## Troubleshooting
### Common Issues PDF Conversion Errors
```
# Install PDF processing 
dependencies
pip install PyMuPDF>=1.23.0

# Check PDF file integrity
python convert_pdfs.py path/
to/your/file.pdf
``` API Key Issues
```
# Verify API key is set
echo $OPENROUTER_API_KEY  # 
Linux/macOS
echo %OPENROUTER_API_KEY%  # 
Windows CMD
echo 
$env:OPENROUTER_API_KEY  # 
Windows PowerShell
``` Knowledge Base Issues
```
# Clear and rebuild 
knowledge base
rm -rf vector_db/  # Linux/
macOS
rmdir /s vector_db  # Windows
python scripts/populate_kb.py
``` Generation Quality Issues
1. Add More Examples: Include high-quality C test examples
2. Improve Specifications: Provide detailed, well-structured specifications
3. Check Token Limits: Ensure sufficient token allocation for complex tests
4. Review HAL Documentation: Verify HAL function documentation is complete
### Error Messages
- "No text extracted from PDF": PDF may be image-based or corrupted
- "ChromaDB collection not initialized": Run populate_kb.py first
- "API request failed": Check API key and internet connection
- "Validation failed": Review generated content format

## Recent Updates and Improvements

### API Key Configuration Enhancement (Latest Update)
- **Enhanced Command Line Support**: All commands now support `--openrouter-key` and `--deepseek-model` arguments
- **Multiple Configuration Methods**: Support for environment variables, command line arguments, and global arguments
- **Priority-Based Resolution**: Clear priority order for API configuration resolution
- **Improved Error Handling**: Better feedback when API keys are missing or invalid

### Updated Command Structure
The following commands have been updated with new API key support:

#### 1. Generate Verification Plan (Updated)
```bash
# Using environment variables
python main_orchestrator.py gen_plan "CLINT machine level timer interrupts"

# Using command line arguments
python main_orchestrator.py gen_plan "CLINT machine level timer interrupts" --openrouter-key "sk-or-v1-your-key" --deepseek-model "deepseek/deepseek-chat-v3-0324:free"

# Using global arguments
python main_orchestrator.py --openrouter-key "sk-or-v1-your-key" gen_plan "CLINT machine level timer interrupts"
```

#### 2. Generate C Tests from Plan (Updated)
```bash
# Using environment variables
python main_orchestrator.py gen_tests --plan_file "generated_outputs/verification_plans/verif_plan_CLINT_machine_level_timer_interrupts.md"

# Using command line arguments  
python main_orchestrator.py gen_tests --plan_file "generated_outputs/verification_plans/verif_plan_CLINT_machine_level_timer_interrupts.md" --openrouter-key "sk-or-v1-your-key" --deepseek-model "deepseek/deepseek-chat-v3-0324:free"
```

#### 3. Other Available Commands
All other commands remain unchanged:
- `populate_kb` - Process source documents and populate the RAG knowledge base
- `plan_to_excel` - Convert a Markdown verification plan to an Excel file
- `extract_features` - Extract design features from specification documents
- `generate_comprehensive` - Extract features and generate comprehensive verification plans and tests
- `generate_all` - Generate all verification artifacts (plan, tests, Excel) for features