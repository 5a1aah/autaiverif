import os
from pathlib import Path
import json # Or CSV parsing if plan is in CSV
from .common_utils import call_deepseek_api, retrieve_relevant_chunks, load_prompt_template

GENERATED_TESTS_PATH = Path(__file__).resolve().parent.parent / "generated_outputs" / "c_tests"

# Placeholder for parsing the verification plan.
# In a real system, this would parse a file (JSON, CSV, YAML, etc.)
# For this example, we'll assume a list of test case dictionaries.
def parse_verification_plan_from_text(plan_text: str) -> list[dict]:
    """
    Parses a structured text verification plan into a list of test case dictionaries.
    This is a very basic parser and highly dependent on the LLM's output format.
    It looks for "Test ID:" as a separator.
    """
    test_cases = []
    current_case_lines = []
    for line in plan_text.splitlines():
        if line.startswith("Test ID:") and current_case_lines:
            # Process previous case
            case_dict = {}
            full_case_text = "\n".join(current_case_lines)
            # Simple parsing - extract fields based on keywords
            for field_line in full_case_text.splitlines():
                if ":" in field_line:
                    key, value = field_line.split(":", 1)
                    key = key.strip().lower().replace(" ", "_").replace(":", "")
                    value = value.strip()
                    if key == "test_id": # Clean up test_id for function names
                        value = value.replace(" ", "_").replace("-", "_")
                    case_dict[key] = value
            if "test_id" in case_dict and "test_description" in case_dict: # Basic validation
                 test_cases.append(case_dict)
            current_case_lines = [line]
        else:
            current_case_lines.append(line)
    
    # Process the last case
    if current_case_lines:
        case_dict = {}
        full_case_text = "\n".join(current_case_lines)
        for field_line in full_case_text.splitlines():
            if ":" in field_line:
                key, value = field_line.split(":", 1)
                key = key.strip().lower().replace(" ", "_").replace(":", "")
                value = value.strip()
                if key == "test_id":
                    value = value.replace(" ", "_").replace("-", "_")
                case_dict[key] = value
        if "test_id" in case_dict and "test_description" in case_dict:
            test_cases.append(case_dict)
            
    print(f"Parsed {len(test_cases)} test cases from the plan.")
    if test_cases:
        print(f"First parsed test case ID: {test_cases[0].get('test_id')}")
    return test_cases


def generate_c_test_from_description(test_case: dict, preferred_c_example_source: str = None):
    """
    Generates a C test function for a single test case description.
    test_case should be a dictionary with keys like 'test_id', 'test_description', etc.
    """
    test_id = test_case.get("test_id", "unknown_test_id")
    test_description = test_case.get("test_description", "No description provided.")
    stimulus = test_case.get("stimulus", "Not specified.")
    expected_outcome = test_case.get("expected_outcome", "Not specified.")

    print(f"\nGenerating C test for Test ID: {test_id}")
    print(f"Description: {test_description[:100]}...")

    # 1. Retrieve relevant context using RAG
    hal_query = f"C HAL API functions for {test_description}"
    hal_context_chunks = retrieve_relevant_chunks(query_text=hal_query, top_k=3, doc_type_filter="hal_code") # or "hal_doc"
    if not hal_context_chunks: # Fallback if no hal_code found
        hal_context_chunks = retrieve_relevant_chunks(query_text=hal_query, top_k=3, doc_type_filter="hal_doc")

    regmap_query = f"Register details for {test_description}"
    regmap_context_chunks = retrieve_relevant_chunks(query_text=regmap_query, top_k=2, doc_type_filter="regmap")

    # Retrieve C test example
    example_c_source_description = "dynamically retrieved example"
    if preferred_c_example_source and (Path(preferred_c_example_source).is_file() or Path("knowledge_base_src/c_test_examples/") / preferred_c_example_source).is_file() :
        example_file_path_kb = Path("knowledge_base_src/c_test_examples/") / preferred_c_example_source
        example_file_path_abs = Path(preferred_c_example_source)

        actual_path = None
        if example_file_path_abs.is_file():
            actual_path = example_file_path_abs
        elif example_file_path_kb.is_file():
            actual_path = example_file_path_kb
        
        if actual_path:
            try:
                with open(actual_path, 'r', encoding='utf-8') as f:
                    c_example_context_chunks = [f.read()]
                example_c_source_description = f"user-specified file: {actual_path.name}"
                print(f"Using user-specified C example: {actual_path.name}")
            except IOError:
                print(f"Warning: Could not read user-specified example {actual_path}. Falling back to RAG.")
                c_example_context_chunks = retrieve_relevant_chunks(query_text=test_description, top_k=1, doc_type_filter="c_example")
        else:
            print(f"Warning: User-specified example '{preferred_c_example_source}' not found. Falling back to RAG.")
            c_example_context_chunks = retrieve_relevant_chunks(query_text=test_description, top_k=1, doc_type_filter="c_example")

    else:
        c_example_query = f"C test code example for {test_description}"
        c_example_context_chunks = retrieve_relevant_chunks(query_text=c_example_query, top_k=1, doc_type_filter="c_example")


    retrieved_hal_context = "\n\n---\n\n".join(hal_context_chunks) if hal_context_chunks else "No specific HAL details retrieved. Please ensure HAL functions are well-known or described in the test case."
    retrieved_regmap_context = "\n\n---\n\n".join(regmap_context_chunks) if regmap_context_chunks else "No specific register map details retrieved."
    retrieved_c_example_context = c_example_context_chunks[0] if c_example_context_chunks else "// No specific C test example retrieved. Adhere to general best practices for C tests."
    
    if not c_example_context_chunks and example_c_source_description == "dynamically retrieved example":
         example_c_source_description = "None found via RAG"


    # 2. Load prompt template
    prompt_template = load_prompt_template("stage2_c_test_gen_prompt.txt")
    if not prompt_template:
        print("Error: Could not load C test generation prompt template.")
        return

    # 3. Populate the prompt
    # Ensure test_id is clean for use in C function names
    clean_test_id = "".join(c if c.isalnum() or c == '_' else '_' for c in test_id)
    if not clean_test_id or clean_test_id[0].isdigit(): # C identifiers cannot start with a digit
        clean_test_id = "test_" + clean_test_id


    formatted_prompt = prompt_template.replace("{{test_id}}", clean_test_id)
    formatted_prompt = formatted_prompt.replace("{{test_description}}", test_description)
    formatted_prompt = formatted_prompt.replace("{{stimulus}}", stimulus)
    formatted_prompt = formatted_prompt.replace("{{expected_outcome}}", expected_outcome)
    formatted_prompt = formatted_prompt.replace("{{hal_context}}", retrieved_hal_context)
    formatted_prompt = formatted_prompt.replace("{{regmap_context}}", retrieved_regmap_context)
    formatted_prompt = formatted_prompt.replace("{{example_c_source_description}}", example_c_source_description)
    formatted_prompt = formatted_prompt.replace("{{example_c_code_context}}", retrieved_c_example_context)


    # 4. Call the LLM API
    print("Sending request to LLM for C test generation...")
    try:
        llm_response = call_deepseek_api(formatted_prompt, temperature=0.4, max_tokens=2048) # Temperature can be lower for code
    except Exception as e:
        print(f"Error calling LLM API: {e}")
        return

    if not llm_response or llm_response.startswith("Error:"):
        print(f"LLM API call failed or returned an error: {llm_response}")
        return

    # 5. Save the generated C test
    GENERATED_TESTS_PATH.mkdir(parents=True, exist_ok=True)
    output_filename = GENERATED_TESTS_PATH / f"test_{clean_test_id}.c"
    
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(llm_response)
        print(f"\nC test function saved successfully to: {output_filename}")
        print("\n--- Generated C Test Snippet ---")
        print(llm_response[:500] + "..." if len(llm_response) > 500 else llm_response)
        print("--- End of Snippet ---")
    except IOError as e:
        print(f"Error saving C test to file: {e}")

    return llm_response


if __name__ == "__main__":
    # Example Usage:
    # This script can either process a full verification plan file
    # or a single hardcoded test case for demonstration.

    # Option 1: Process a verification plan file (e.g., generated by 02_generate_verif_plan.py)
    # Find the latest verification plan text file to process as an example
    plans_dir = Path(__file__).resolve().parent.parent / "generated_outputs" / "verification_plans"
    plan_files = sorted(plans_dir.glob("verif_plan_*.txt"), key=os.path.getmtime, reverse=True)

    if plan_files:
        latest_plan_file = plan_files[0]
        print(f"\nProcessing C tests from latest verification plan: {latest_plan_file.name}")
        try:
            with open(latest_plan_file, 'r', encoding='utf-8') as f:
                plan_content = f.read()
            
            test_cases_from_plan = parse_verification_plan_from_text(plan_content)
            
            if test_cases_from_plan:
                # Process only the first few test cases for this example run
                num_tests_to_generate = min(2, len(test_cases_from_plan)) # Limit to 2 for quick test
                print(f"Will generate C tests for the first {num_tests_to_generate} test cases from the plan.")
                for i in range(num_tests_to_generate):
                    generate_c_test_from_description(test_cases_from_plan[i])
                    print("-" * 50)
            else:
                print("No test cases could be parsed from the plan.")

        except Exception as e:
            print(f"Error processing plan file {latest_plan_file.name}: {e}")
            print("Consider using Option 2 (single test case) for testing C test generation.")

    else:
        print("\nNo verification plan files found in generated_outputs/verification_plans.")
        print("Consider running 02_generate_verif_plan.py first or use Option 2 below.")


    # Option 2: Define a single test case dictionary for quick testing
    # print("\n--- Testing with a single hardcoded test case ---")
    # example_single_test_case = {
    #     "test_id": "GPIO_TOGGLE_001",
    #     "test_category": "Basic IO",
    #     "feature_being_tested": "GPIO Output Toggle",
    #     "test_description": "Configure GPIO pin 5 as an output. Set GPIO pin 5 high. Read back GPIO data register to verify it is high. Set GPIO pin 5 low. Read back GPIO data register to verify it is low.",
    #     "stimulus": "1. Configure GPIO_CONF[5].DIR = OUTPUT. 2. Write GPIO_DATA[5] = 1. 3. Read GPIO_DATA[5]. 4. Write GPIO_DATA[5] = 0. 5. Read GPIO_DATA[5].",
    #     "expected_outcome": "1. GPIO_DATA[5] should read 1 after setting high. 2. GPIO_DATA[5] should read 0 after setting low.",
    #     "coverage_points": "GPIO output functionality. GPIO data register readback."
    # }
    # # You can also specify a C example file from your knowledge_base_src/c_test_examples/ directory
    # # e.g., generate_c_test_from_description(example_single_test_case, preferred_c_example_source="example_gpio_test.c")
    # generate_c_test_from_description(example_single_test_case)