# How to Run This Project

## Two Usage Modes Available

This project supports both **GUI Mode** (graphical user interface) and **CLI Mode** (command line interface):

### 🖥️ GUI Mode (Recommended for Interactive Use)
Launch the graphical interface for easy, interactive verification automation:

```sh
python main_orchestrator.py --gui
```

The GUI provides:
- **Knowledge Base Management**: Populate and manage verification knowledge base
- **Verification Plan Generation**: Interactive feature description and plan generation  
- **UVM Test Generation**: Generate UVM tests with coverage options
- **C Test Generation**: Generate C tests from verification plans
- **File Management**: Easy file selection and output directory management
- **Real-time Progress**: Live status updates and error handling

### 💻 CLI Mode (Recommended for Batch Processing)
Use command-line interface for automation, scripting, and batch operations:

1. **Clone the Repository**
    ```sh
    git clone <repository-url>
    cd asic_verification_automation
    ```

2. **Install Dependencies**
    ```sh
    # Activate Virtual Environment (Recommended)
    # On Windows
    venv\Scripts\activate

    # On macOS/Linux
    source venv/bin/activate

    pip install -r requirements.txt
    ```

3. **Run the Main Script**

    # Run the Main Script
    ```sh
    python convert_pdfs.py "knowledge_base_src\specs\CVA6_Testharness.pdf" --vision 

    python main_orchestrator.py populate_kb           
    ```
    python main_orchestrator.py gen_plan "CLINT timer interrupt"

    ```
    python main_orchestrator.py plan_to_excel -plan_file .\generated_outputs\verification_plans\verif_plan_CLINT_timer_interrupt.md --excel_file generated_outputs/excel_reports/report_clint.xlsx  

    ```
    python main_orchestrator.py gen_tests --plan_file generated_outputs/verification_plans/verif_plan_CLINT_timer_interrupt.md             

    python main_orchestrator.py gen_tests --plan_file "generated_outputs/verification_plans/verif_plan_APB_timer_verification.md" --output-dir "final_test_verification"
                                                  
    ```
    
    # Generate tests with custom output directory
    ```sh
    python main_orchestrator.py gen_tests --plan_file "generated_outputs/verification_plans/verif_plan_clint_registers_sanity.md" --output-dir "custom_test_directory"
    ```
    
    # Generate tests with address map file
    ```sh
    python main_orchestrator.py gen_tests --plan_file "generated_outputs/verification_plans/verif_plan_clint_registers_sanity.md" --addr_map_file "knowledge_base_src/regmaps/clint_registers.txt"
    ```

    python main_orchestrator.py generate_comprehensive "knowledge_base_src\specs\cva6_core_spec.txt" --memmap_file "knowledge_base_src\regmaps\cva6_csr_map.txt" --output_dir "generated_outputs\comprehensive_verification\cva6_test" --verbose

## UVM Test Generation Commands

### Generate UVM Verification Plan
Generate a comprehensive UVM verification plan from a feature description:

```sh
# Basic UVM verification plan generation
python main_orchestrator.py gen_uvm_plan "CLINT timer interrupt functionality"

python main_orchestrator.py gen_uvm_plan "AXI memory interface verification with burst transactions"

python main_orchestrator.py gen_uvm_plan "PLIC interrupt controller verification"

python main_orchestrator.py gen_uvm_plan "Cache coherency protocol verification"
```

### Generate UVM Tests from Verification Plan
Generate SystemVerilog UVM test files from an existing UVM verification plan:

```sh
# Generate UVM tests from verification plan
python main_orchestrator.py gen_uvm_tests "generated_outputs\uvm_verification_plans\uvm_verif_plan_CLINT_timer_interrupt_functionality.md"

python main_orchestrator.py gen_uvm_tests "generated_outputs\uvm_verification_plans\uvm_verif_plan_AXI_memory_interface_verification_with_burst_trans.md"

python main_orchestrator.py gen_uvm_tests "generated_outputs\uvm_verification_plans\uvm_verif_plan_PLIC_interrupt_controller_verification.md"
```

### Complete UVM Workflow Example
Here's a complete workflow from feature description to UVM tests:

```sh
# Step 1: Populate knowledge base (includes UVM examples)
python main_orchestrator.py populate_kb

# Step 2: Generate UVM verification plan
python main_orchestrator.py gen_uvm_plan "AXI4 slave interface verification with protocol compliance"

# Step 3: Generate UVM tests from the plan
python main_orchestrator.py gen_uvm_tests "generated_outputs\uvm_verification_plans\uvm_verif_plan_AXI4_slave_interface_verification_with_protocol_compliance.md"

python main_orchestrator.py gen_uvm_tests "generated_outputs\uvm_verification_plans\uvm_verif_plan_AXI4_memory_interface_verification_with_burst_tran.md" --coverage_enable --output "generated_outputs\uvm_tests_with_coverage"
```

### UVM Output Structure
The UVM commands generate the following outputs:

- **UVM Verification Plans**: `generated_outputs\uvm_verification_plans\`
  - Comprehensive test specifications with UVM methodology
  - Coverage requirements and UVM component definitions
  - Test case descriptions with sequences and stimulus

- **UVM Test Files**: `generated_outputs\uvm_tests\`
  - Complete SystemVerilog UVM test implementations
  - Proper UVM class hierarchy and phase management
  - Coverage groups, assertions, and self-checking mechanisms
  - Integration with project sequences from knowledge base

### Advanced UVM Examples

```sh
# Generate verification plan for complex memory subsystem
python main_orchestrator.py gen_uvm_plan "Multi-level cache coherency with MESI protocol verification"

# Generate verification plan for high-speed interface
python main_orchestrator.py gen_uvm_plan "PCIe Gen4 x16 interface verification with error injection"

# Generate verification plan for security features
python main_orchestrator.py gen_uvm_plan "Memory protection unit verification with privilege level checking"

# Generate verification plan for performance testing
python main_orchestrator.py gen_uvm_plan "DMA controller verification with concurrent multi-channel operations"
```

## Comprehensive Test Generation Command

    python main_orchestrator.py generate_comprehensive "knowledge_base_src\specs\cva6_core_spec.txt" --memmap_file "knowledge_base_src\regmaps\cva6_csr_map.txt" --output_dir "generated_outputs\comprehensive_verification\cva6_test" --verbose


> Replace `<repository-url>` with the actual URL of the repository.

gen_plan "PLIC registers access" --deepseek-model(--llm-model) "deepseek/deepseek-chat-v3-0324:free"