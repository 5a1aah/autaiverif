import requests
import json
import os
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

# Import RAG utilities and API constants from common_utils
from .common_utils import (
    OPENROUTER_API_KEY,
    OPENROUTER_API_URL,
    DEEPSEEK_MODEL_NAME_DEFAULT,
    retrieve_relevant_chunks,
    load_prompt_template,
    initialize_chromadb_client_and_collection # Ensure RAG is ready if not already
)

class ASICVerificationAutomator:
    def __init__(self, api_key: str = OPENROUTER_API_KEY, model_name: str = DEEPSEEK_MODEL_NAME_DEFAULT):
        # if not api_key or api_key == "sk-or-v1-YOUR_PLACEHOLDER_API_KEY_REPLACE_ME": # Use your actual placeholder
        #     api_key_env = os.getenv("OPENROUTER_API_KEY")
        #     if api_key_env and api_key_env != "sk-or-v1-YOUR_PLACEHOLDER_API_KEY_REPLACE_ME":
        #         self.api_key = api_key_env
        #         print("INFO: Loaded API Key from environment variable inside Automator init.")
        #     else:
        #         raise ValueError("ERROR: API Key is not set or is using the placeholder. Please configure OPENROUTER_API_KEY.")
        # else:
        #     self.api_key = api_key
        self.api_key = api_key
        self.model_name = model_name
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        initialize_chromadb_client_and_collection()
    
    def _call_llm_api(self, prompt: str, max_tokens: int =4000, temperature: float = 0.3) -> str:
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        print(f"\n--- Sending request to OpenRouter (Model: {self.model_name}) ---")
        try:
            response = requests.post(OPENROUTER_API_URL, headers=self.headers, json=payload, timeout=180)
            response.raise_for_status()
            result = response.json()
            
            if result.get("choices") and len(result["choices"]) > 0:
                content = result["choices"][0].get("message", {}).get("content")
                if content:
                    print("--- Successfully received response from OpenRouter ---")
                    return content.strip()
            
            print(f"Unexpected API response structure: {result}")
            raise ValueError("API response did not contain expected content or was empty.")

        except requests.exceptions.Timeout as e:
            print(f"Error: API request timed out. {e}")
            return f"Error: API request timed out. {e}"
        except requests.exceptions.RequestException as e:
            print(f"Error calling LLM API: {e}")
            error_response_text = ""
            if hasattr(e, 'response') and e.response is not None:
                error_response_text = e.response.text
                print(f"Response Status: {e.response.status_code}, Response Text: {error_response_text}")
            return f"Error: LLM API call failed. {e}. Response: {error_response_text}"
        except ValueError as e:
            print(f"Error processing API response: {e}")
            return f"Error: Processing API response failed. {e}"
        except Exception as e:
            print(f"An unexpected error occurred during API call: {e}")
            return f"Error: An unexpected error occurred. {e}"

    def preprocess_address_map_text(self, address_map_text: str) -> str:
        processed_text = re.sub(r'`([0-9xA-Fa-f]+)`', r'\1', address_map_text)
        base_addresses = {}
        base_match = re.findall(r'\|\s*([A-Za-z0-9_]+)\s*\|\s*(0x[0-9A-Fa-f]+)\s*\|', processed_text)
        for name, addr in base_match:
            base_addresses[name] = addr
        for name, addr in base_addresses.items():
            processed_text = processed_text.replace(f"(Base: {name})", f"(Base: {addr})")
        return processed_text
    
    def generate_verification_plan(self, 
                                   feature_description: str, 
                                   asic_spec_text: str = "", 
                                   address_map_text: str = "", 
                                   hal_text: str = "",
                                   test_example_text: str = "",
                                   output_file: Optional[str] = None) -> str:
        print(f"\nGenerating verification plan for feature: {feature_description} using RAG.")

        retrieved_spec_context = "No specification context provided directly or via RAG."
        if asic_spec_text:
            retrieved_spec_context = asic_spec_text
        else:
            spec_chunks = retrieve_relevant_chunks(
                query_text=f"ASIC specification details for {feature_description}",
                top_k=3, doc_type_filter="spec"
            )
            if spec_chunks:
                retrieved_spec_context = "\n\n---\n\n".join(spec_chunks)

        processed_address_map = "No address map provided."
        if address_map_text:
            processed_address_map = self.preprocess_address_map_text(address_map_text)
        else:
            addr_map_chunks = retrieve_relevant_chunks(
                 query_text=f"Address map or register map relevant to {feature_description}",
                 top_k=1, doc_type_filter="regmap"
            )
            if addr_map_chunks:
                processed_address_map = self.preprocess_address_map_text("\n\n---\n\n".join(addr_map_chunks))

        # Prepare HAL context
        hal_context = "No HAL context provided."
        if hal_text:
            hal_context = hal_text
        else:
            # Optionally, try to retrieve from RAG if no direct text and RAG is set up for HAL
            # hal_chunks = retrieve_relevant_chunks(query_text=f"HAL details for {feature_description}", top_k=1, doc_type_filter="hal")
            # if hal_chunks: hal_context = "\n\n---\n\n".join(hal_chunks)
            pass # For now, only use provided text

        # Prepare Test Example context
        test_example_context = "No test example context provided."
        if test_example_text:
            test_example_context = test_example_text
        else:
            # Optionally, try to retrieve from RAG
            # test_ex_chunks = retrieve_relevant_chunks(query_text=f"Test examples for {feature_description}", top_k=1, doc_type_filter="test_example")
            # if test_ex_chunks: test_example_context = "\n\n---\n\n".join(test_ex_chunks)
            pass # For now, only use provided text

        prompt_template = load_prompt_template("stage1_verif_plan_prompt.txt")
        if not prompt_template:
            error_msg = "Error: Could not load verification plan prompt template."
            print(error_msg)
            return error_msg
        
        # Example test structure (from your stage1_verif_plan_prompt.txt)
        # Ensure this matches the example given to the LLM in the prompt file
        example_test_structure_in_prompt = """
### Test Case: MOD_FUNC_NAME
- **Test Category:** Category Name
- **Feature Being Tested:** Specific Feature Aspect
- **Test Description:** Detailed step-by-step explanation...
- **Stimulus:** High-level inputs...
- **Expected Outcome:** ASIC behavior, expected data...
- **Coverage Points:** Functional coverage points...
        """ # This is illustrative, your prompt should define this.

        # These placeholders should exist in your stage1_verif_plan_prompt.txt
        formatted_prompt = prompt_template.replace("{{feature_description}}", feature_description)
        formatted_prompt = formatted_prompt.replace("{{retrieved_spec_context}}", retrieved_spec_context)
        formatted_prompt = formatted_prompt.replace("{{retrieved_regmap_context}}", processed_address_map)
        formatted_prompt = formatted_prompt.replace("{{hal_context}}", hal_context)
        formatted_prompt = formatted_prompt.replace("{{test_example_context}}", test_example_context)
        # If your prompt includes {{output_format}}, you might need to handle it or remove if not used by automator
        # formatted_prompt = formatted_prompt.replace("{{output_format}}", "structured markdown using '### Test Case:' for each test")

        print("Sending RAG-augmented request to LLM for verification plan generation...")
        verification_plan = self._call_llm_api(formatted_prompt, max_tokens=2600)

        if verification_plan.startswith("Error:"):
            print(f"Failed to generate verification plan: {verification_plan}")
            return verification_plan
    
        # Validate and fix the format if needed
        if verification_plan.strip().startswith("{"): # JSON format detected
            print("Warning: Verification plan was generated in JSON format. Converting to required Markdown format...")
            try:
                # Try to parse the JSON
                plan_data = json.loads(verification_plan)
                # Extract the test cases
                test_cases = []
                for key, value in plan_data.items():
                    if isinstance(value, list):
                        test_cases = value
                        break
                
                # Convert to Markdown format
                markdown_plan = "{{output_format}}\n\n"
                
                for test in test_cases:
                    markdown_plan += "---\n\n"
                    markdown_plan += f"### Test Case: {test.get('Test ID', 'UNKNOWN')}\n"
                    for field, value in test.items():
                        if field != 'Test ID':
                            markdown_plan += f"- **{field}:** {value}\n"
                    markdown_plan += "\n"
                
                verification_plan = markdown_plan
                print("Successfully converted JSON format to Markdown format.")
            except Exception as e:
                print(f"Warning: Failed to convert JSON format to Markdown: {e}. Proceeding with original format.")
        
        if output_file:
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(verification_plan)
                print(f"Verification plan generated and saved to {output_file}")
            except IOError as e:
                error_msg = f"Error saving verification plan to file: {e}"
                print(error_msg)
        
        return verification_plan

    def _parse_test_cases_from_plan(self, verification_plan_text: str) -> List[Dict[str, Any]]:
        """Helper to parse structured test cases from plan text (Markdown format)."""
        test_cases: List[Dict[str, Any]] = []
        # Split the entire plan by "---" which seems to be the main separator in your example
        raw_test_blocks = re.split(r'\n---\s*\n', verification_plan_text)
        
        print(f"DEBUG (_parse_test_cases_from_plan): Number of raw blocks after splitting by '---': {len(raw_test_blocks)}")

        for block_index, block_content in enumerate(raw_test_blocks):
            block_content = block_content.strip()
            if not block_content or block_content.lower() == "{{output_format}}": # Ignore empty blocks or leftover placeholders
                continue

            print(f"\nDEBUG (_parse_test_cases_from_plan): Processing Block {block_index + 1}...")
            # print(block_content[:300] + "...") # Snippet for debugging

            case_data: Dict[str, Any] = {}
            lines = block_content.splitlines()

            if not lines:
                continue

            # First line: "### Test Case: MTIP_001"
            title_line = lines[0].strip()
            title_match = re.match(r"### Test Case:\s*([^\s]+)(?:\s*(.*))?", title_line)
            
            if title_match:
                case_data["test_id"] = title_match.group(1).strip().replace("-", "_")
                # case_data["test_title"] = title_match.group(2).strip() if title_match.group(2) else case_data["test_id"] # Optional full title
                print(f"DEBUG (_parse_test_cases_from_plan): Parsed Test ID: {case_data['test_id']}")
            else:
                print(f"DEBUG (_parse_test_cases_from_plan): Could not parse Test ID from title line: '{title_line}'. Skipping block.")
                continue

            # Process subsequent lines for fields: "- **Field Name:** Value"
            current_field_key: Optional[str] = None
            current_field_value_lines: List[str] = []

            for line_content in lines[1:]: # Start from the second line
                line_strip = line_content.strip()
                field_match = re.match(r"-\s*\*\*(.+?):\*\*\s*(.*)", line_strip) # Non-greedy key match
                
                if field_match: # New field started
                    if current_field_key and current_field_value_lines: # Save previous field's data
                        case_data[current_field_key] = "\n".join(current_field_value_lines).strip()
                        # print(f"DEBUG: Stored field '{current_field_key}'")
                    
                    current_field_key = field_match.group(1).strip().lower().replace(" ", "_")
                    current_field_value_lines = [field_match.group(2).strip()]
                elif current_field_key and line_strip.startswith("- "): # Continuation of a list under current field
                    current_field_value_lines.append(line_strip.lstrip("- ").strip())
                elif current_field_key and line_strip: # Continuation of multi-line text for current field
                    current_field_value_lines.append(line_strip)
                # If line is empty or doesn't match, it might be spacing between fields, or end of a field's content

            # Save the last processed field
            if current_field_key and current_field_value_lines:
                case_data[current_field_key] = "\n".join(current_field_value_lines).strip()
                # print(f"DEBUG: Stored last field '{current_field_key}'")

            # Basic validation and adding to list
            if "test_id" in case_data and case_data.get("test_description"): # Ensure essential fields are present
                test_cases.append(case_data)
                print(f"DEBUG (_parse_test_cases_from_plan): Successfully parsed and added test case: {case_data['test_id']}")
                # print(f"DEBUG data: {case_data}") # For more detail
            else:
                print(f"DEBUG (_parse_test_cases_from_plan): Skipping block for Test ID '{case_data.get('test_id', 'N/A')}' due to missing critical fields (e.g., description). Parsed data: {case_data}")
        
        if not test_cases and verification_plan_text.strip() and verification_plan_text.lower() != "{{output_format}}":
            print("Warning (_parse_test_cases_from_plan): No structured test cases were successfully parsed after processing all blocks.")
            
        print(f"Final count of parsed test cases: {len(test_cases)}")
        return test_cases

    def generate_c_tests(self, 
                         verification_plan_text: str, 
                         address_map_text: str = "", 
                         hal_text: str = "",
                         test_example_text: str = "",
                         output_dir: str = "c_tests") -> List[str]:
        """Generates C test files from a verification plan using RAG and an LLM."""
        print(f"\nGenerating C tests from verification plan. Output directory: {output_dir}")
        
        parsed_test_cases = self._parse_test_cases_from_plan(verification_plan_text)
        if not parsed_test_cases:
            print("Error: No valid test cases found in the verification plan.")
            return []

        # Prepare Address Map context (once for all tests if not already embedded in plan)
        processed_address_map = "No address map provided."
        if address_map_text:
            processed_address_map = self.preprocess_address_map_text(address_map_text)
        else:
            # Try RAG for a general address map if not given
            addr_map_chunks = retrieve_relevant_chunks(query_text="General CPU or SoC Address Map", top_k=1, doc_type_filter="regmap")
            if addr_map_chunks:
                processed_address_map = self.preprocess_address_map_text("\n\n---\n\n".join(addr_map_chunks))
        
        # Prepare HAL context (once for all tests)
        hal_context = "No HAL context provided."
        if hal_text:
            hal_context = hal_text
        # else: # Optional RAG retrieval for HAL if needed globally
            # hal_chunks = retrieve_relevant_chunks(query_text="General HAL functions and API", top_k=2, doc_type_filter="hal")
            # if hal_chunks: hal_context = "\n\n---\n\n".join(hal_chunks)

        # Prepare Test Example context (once for all tests)
        test_example_context = "No test example context provided."
        if test_example_text:
            test_example_context = test_example_text
        # else: # Optional RAG retrieval for test examples
            # test_ex_chunks = retrieve_relevant_chunks(query_text="General C test structure or examples", top_k=1, doc_type_filter="test_example")
            # if test_ex_chunks: test_example_context = "\n\n---\n\n".join(test_ex_chunks)

        generated_files: List[str] = []
        output_path = Path(output_dir)
        prompt_template_c = load_prompt_template("stage2_c_test_gen_prompt.txt")
        if not prompt_template_c:
            print("Error: Could not load C test generation prompt template. Aborting C test generation.")
            return []

        for test_case in parsed_test_cases:
            test_id = test_case.get("test_id", f"unknown_test_{len(generated_files)}")
            clean_test_id = "".join(c if c.isalnum() or c == '_' else '_' for c in test_id)
            if not clean_test_id or clean_test_id[0].isdigit():
                clean_test_id = "test_" + clean_test_id
            
            test_description = test_case.get("test_description", "No description provided in parsed data.")
            rag_query = f"{test_id} - {test_description}" # Used for RAG context fetching

            print(f"\n--- Generating C test for: {clean_test_id} ---")

            hal_context_chunks = retrieve_relevant_chunks(rag_query, top_k=2, doc_type_filter="hal_code")
            if not hal_context_chunks: 
                hal_context_chunks = retrieve_relevant_chunks(rag_query, top_k=2, doc_type_filter="hal_doc")
            retrieved_hal_context = "\n\n---\n\n".join(hal_context_chunks) if hal_context_chunks else "No specific HAL details retrieved via RAG."
            
            # Use processed_address_map if provided, otherwise try RAG for regmap
            retrieved_regmap_context = processed_address_map
            if "No address map context provided" in processed_address_map: # If it wasn't passed directly
                 regmap_chunks = retrieve_relevant_chunks(rag_query, top_k=1, doc_type_filter="regmap")
                 if regmap_chunks:
                     retrieved_regmap_context = "\n\n---\n\n".join(regmap_chunks)

            c_example_chunks = retrieve_relevant_chunks(rag_query, top_k=1, doc_type_filter="c_example")
            retrieved_c_example_context = c_example_chunks[0] if c_example_chunks else "// No C example retrieved via RAG. Adhere to general C test best practices."
            
            current_prompt = prompt_template_c.replace("{{test_id}}", clean_test_id)
            current_prompt = current_prompt.replace("{{test_description}}", test_description)
            current_prompt = current_prompt.replace("{{stimulus}}", test_case.get("stimulus", "Refer to test description."))
            current_prompt = current_prompt.replace("{{expected_outcome}}", test_case.get("expected_outcome", test_case.get("expected_results", "Refer to test description."))) # Check for expected_results too
            current_prompt = current_prompt.replace("{{hal_context}}", retrieved_hal_context)
            current_prompt = current_prompt.replace("{{regmap_context}}", retrieved_regmap_context)
            current_prompt = current_prompt.replace("{{example_c_source_description}}", "RAG retrieved example or a general guideline")
            current_prompt = current_prompt.replace("{{example_c_code_context}}", retrieved_c_example_context)
            current_prompt = current_prompt.replace("{{hal_context}}", hal_context)
            current_prompt = current_prompt.replace("{{test_example_context}}", test_example_context)
            
            print(f"Sending RAG-augmented request to LLM for C test generation ({clean_test_id})...")
            c_test_code = self._call_llm_api(current_prompt, max_tokens=2048, temperature=0.3)

            if c_test_code.startswith("Error:"):
                print(f"Failed to generate C code for {clean_test_id}: {c_test_code}")
                continue            
            c_test_code = re.sub(r"^```c\s*?\n", "", c_test_code, flags=re.MULTILINE)
            c_test_code = re.sub(r"\n```\s*$", "", c_test_code, flags=re.MULTILINE)
            
            # Import and apply LLM artifact cleanup
            from .generate_c_tests import clean_llm_artifacts
            c_test_code = clean_llm_artifacts(c_test_code)
            
            c_test_code = c_test_code.strip()
            
            filename = output_path / f"test_{clean_test_id.lower()}.c"
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(c_test_code)
                generated_files.append(str(filename))
                print(f"Generated C test file: {filename}")
            except IOError as e:
                print(f"Error saving C test file {filename}: {e}")
                
        print(f"\nSuccessfully generated {len(generated_files)} C test files.")
        return generated_files

    def generate_uvm_verification_plan(self, feature_description: str, 
                                     spec_text: str = None, 
                                     address_map_text: str = None) -> str:
        """
        Generate a UVM verification plan for the given feature description.
        
        Args:
            feature_description (str): Description of the ASIC feature to verify
            spec_text (str, optional): Specification text context
            address_map_text (str, optional): Address map text context
            
        Returns:
            str: Generated UVM verification plan content
        """
        print(f"\n--- Generating UVM Verification Plan for: {feature_description} ---")
        
        # Retrieve relevant context using RAG
        retrieved_spec_context = "No specification context provided."
        if not spec_text:
            spec_chunks = retrieve_relevant_chunks(
                query_text=f"ASIC specification details for {feature_description}",
                top_k=5, doc_type_filter="spec"
            )
            if spec_chunks:
                retrieved_spec_context = "\n\n---\n\n".join(spec_chunks)
        else:
            retrieved_spec_context = spec_text

        processed_address_map = "No address map provided."
        if address_map_text:
            processed_address_map = self.preprocess_address_map_text(address_map_text)
        else:
            addr_map_chunks = retrieve_relevant_chunks(
                 query_text=f"Address map or register map relevant to {feature_description}",
                 top_k=5, doc_type_filter="regmap"
            )
            if addr_map_chunks:
                processed_address_map = self.preprocess_address_map_text("\n\n---\n\n".join(addr_map_chunks))        # Retrieve UVM context - Multiple queries to get comprehensive sequence coverage
        uvm_chunks = []
        
        # Query 1: General UVM sequences for the feature
        uvm_chunks_general = retrieve_relevant_chunks(
            query_text=f"UVM sequences and examples for {feature_description}",
            top_k=3, doc_type_filter="uvm_example"
        )
        if uvm_chunks_general:
            uvm_chunks.extend(uvm_chunks_general)
        
        # Query 2: Specific sequence types based on feature description
        sequence_keywords = []
        if any(keyword in feature_description.lower() for keyword in ['axi', 'memory', 'interface']):
            sequence_keywords.extend(['axi_read_sequence', 'axi_write_sequence', 'axi_burst'])
        if any(keyword in feature_description.lower() for keyword in ['register', 'csr', 'clint']):
            sequence_keywords.extend(['csr_access_sequence', 'register'])
        if any(keyword in feature_description.lower() for keyword in ['interrupt', 'timer']):
            sequence_keywords.extend(['interrupt_sequence'])
        if any(keyword in feature_description.lower() for keyword in ['cache']):
            sequence_keywords.extend(['cache_coherency_sequence'])
        
        for keyword in sequence_keywords:
            seq_chunks = retrieve_relevant_chunks(
                query_text=f"{keyword} sequence implementation",
                top_k=2, doc_type_filter="uvm_example"
            )
            if seq_chunks:
                uvm_chunks.extend(seq_chunks)
        
        # Query 3: Get all available sequences for reference
        all_seq_chunks = retrieve_relevant_chunks(
            query_text="class extends uvm_sequence sequence",
            top_k=5, doc_type_filter="uvm_example"
        )
        if all_seq_chunks:
            uvm_chunks.extend(all_seq_chunks)
          # Remove duplicates while preserving order
        seen = set()
        unique_uvm_chunks = []
        for chunk in uvm_chunks:
            if chunk not in seen:
                seen.add(chunk)
                unique_uvm_chunks.append(chunk)
        
        retrieved_uvm_context = "\n\n---\n\n".join(unique_uvm_chunks) if unique_uvm_chunks else "No UVM context retrieved."

        # Extract available UVM sequences dynamically
        available_uvm_sequences = self._extract_available_uvm_sequences()

        # Load UVM verification plan template
        prompt_template = load_prompt_template("stage1_uvm_verif_plan_prompt.txt")
        if not prompt_template:
            error_msg = "Error: Could not load UVM verification plan prompt template."
            print(error_msg)
            return error_msg
          # Replace placeholders in template
        current_prompt = prompt_template.replace("{{feature_description}}", feature_description)
        current_prompt = current_prompt.replace("{{retrieved_spec_context}}", retrieved_spec_context)
        current_prompt = current_prompt.replace("{{retrieved_regmap_context}}", processed_address_map)
        current_prompt = current_prompt.replace("{{retrieved_uvm_context}}", retrieved_uvm_context)
        current_prompt = current_prompt.replace("{{available_uvm_sequences}}", available_uvm_sequences)
        
        print("Sending request to LLM for UVM verification plan generation...")
        verification_plan = self._call_llm_api(current_prompt, max_tokens=4000, temperature=0.2)
        
        return verification_plan

    def generate_uvm_tests_from_plan(self, verification_plan_content: str, 
                                   output_path: Path = None, coverage_enable: bool = False) -> List[str]:
        """
        Generate UVM test files from a verification plan.
        
        Args:
            verification_plan_content (str): Content of the verification plan
            output_path (Path, optional): Directory to save generated tests
            coverage_enable (bool, optional): Enable comprehensive coverage points in tests
            
        Returns:
            List[str]: List of paths to generated UVM test files
        """
        if output_path is None:
            output_path = Path("generated_outputs/uvm_tests")
        
        output_path.mkdir(parents=True, exist_ok=True)
        
        print(f"\n--- Generating UVM Tests from Verification Plan ---")
        
        # Parse test cases from verification plan
        test_cases = self._parse_uvm_test_cases(verification_plan_content)
        print(f"Found {len(test_cases)} test cases in verification plan")
        
        if not test_cases:
            print("No test cases found in verification plan")
            return []
        
        # Load UVM test generation template
        prompt_template_uvm = load_prompt_template("stage2_uvm_test_gen_prompt.txt")
        if not prompt_template_uvm:
            print("Error: Could not load UVM test generation prompt template.")
            return []
        
        generated_files = []
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"Generating UVM test {i}/{len(test_cases)}: {test_case['test_id']}")
            
            try:
                # Create RAG query from test case
                rag_query = f"{test_case['test_id']} {test_case['content'][:200]}"
                
                # Retrieve relevant context
                spec_chunks = retrieve_relevant_chunks(rag_query, top_k=3, doc_type_filter="spec")
                retrieved_spec_context = "\n\n---\n\n".join(spec_chunks) if spec_chunks else "No specification context retrieved."
                
                regmap_chunks = retrieve_relevant_chunks(rag_query, top_k=3, doc_type_filter="regmap")
                retrieved_regmap_context = "\n\n---\n\n".join(regmap_chunks) if regmap_chunks else "No register map context retrieved."
                
                uvm_chunks = retrieve_relevant_chunks(rag_query, top_k=2, doc_type_filter="uvm_example")
                retrieved_uvm_context = "\n\n---\n\n".join(uvm_chunks) if uvm_chunks else "No UVM context retrieved."
                  # Format prompt
                current_prompt = prompt_template_uvm.replace("{{test_case}}", test_case['full_content'])
                current_prompt = current_prompt.replace("{{retrieved_spec_context}}", retrieved_spec_context)
                current_prompt = current_prompt.replace("{{retrieved_regmap_context}}", retrieved_regmap_context)
                current_prompt = current_prompt.replace("{{retrieved_uvm_context}}", retrieved_uvm_context)
                  # Add coverage requirements if enabled
                if coverage_enable:
                    coverage_requirements = """

COMPREHENSIVE COVERAGE REQUIREMENTS:
Generate extensive coverage points including:

1. **Functional Coverage:**
   - Cover all major functional scenarios and corner cases
   - Create covergroups for transaction types, data patterns, and protocol states
   - Include cross-coverage between different signals and conditions
   - Add coverage for error conditions and recovery scenarios

2. **Protocol Coverage:**
   - Cover all valid protocol combinations and sequences
   - Include coverage for timing relationships and handshake protocols
   - Add coverage for different burst types, sizes, and address patterns
   - Cover all valid and invalid protocol transitions

3. **Data Coverage:**
   - Cover data patterns (all 0s, all 1s, alternating, random)
   - Include address boundary coverage (aligned, unaligned, wraparound)
   - Add coverage for different data sizes and byte enables
   - Cover special values and edge cases

4. **Implementation Details:**
   - Use `covergroup` constructs with proper `coverpoint` and `cross` statements
   - Include `bins` for discrete values and `ignore_bins` for invalid cases
   - Add proper `iff` conditions for sampling coverage
   - Use meaningful coverage group names and comments

Example coverage structure to include:
```systemverilog
covergroup protocol_cg;
    addr_cp: coverpoint transaction.addr {
        bins low_addr = {[0:1023]};
        bins mid_addr = {[1024:2047]};  
        bins high_addr = {[2048:4095]};
    }
    
    size_cp: coverpoint transaction.size {
        bins byte_access = {0};
        bins halfword = {1};
        bins word = {2};
    }
    
    cross addr_cp, size_cp;
endgroup
```

IMPORTANT: Implement these coverage points as covergroups within the test class and ensure they are properly instantiated and sampled.
"""
                else:
                    coverage_requirements = "Basic coverage points will be included as per standard UVM practice."
                
                # Replace coverage placeholder
                current_prompt = current_prompt.replace("{{coverage_requirements}}", coverage_requirements)
                
                print(f"Sending RAG-augmented request to LLM for UVM test generation ({test_case['test_id']})...")
                uvm_test_code = self._call_llm_api(current_prompt, max_tokens=3000, temperature=0.1)

                if uvm_test_code.startswith("Error:"):
                    print(f"Failed to generate UVM code for {test_case['test_id']}: {uvm_test_code}")
                    continue
                
                # Clean the generated UVM code
                uvm_test_code = self._clean_uvm_test_code(uvm_test_code)
                
                # Generate safe filename
                clean_test_id = re.sub(r'[^\w\-_]', '_', test_case['test_id'])
                filename = output_path / f"test_{clean_test_id}.sv"
                
                # Add file header
                file_header = f"""// filepath: {filename}
 /**
 * @file test_{clean_test_id}.sv
 * @brief UVM test for {test_case['test_id']}
 * 
 * Generated on: {self.get_timestamp()}
 */

"""
                
                try:
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(file_header + uvm_test_code)
                    generated_files.append(str(filename))
                    print(f"Generated UVM test file: {filename}")
                except IOError as e:
                    print(f"Error saving UVM test file {filename}: {e}")
                    
            except Exception as e:
                print(f"Error generating UVM test {test_case['test_id']}: {str(e)}")
                continue
                
        print(f"\nSuccessfully generated {len(generated_files)} UVM test files.")
        return generated_files

    def _parse_uvm_test_cases(self, verification_plan_content: str) -> List[Dict[str, str]]:
        """
        Parse test cases from UVM verification plan content.
        
        Args:
            verification_plan_content (str): Content of the verification plan
            
        Returns:
            List[Dict[str, str]]: List of dictionaries containing test case information
        """
        test_cases = []
        
        # Pattern to match test cases
        test_case_pattern = r'### Test Case: ([^\n]+)\n(.*?)(?=### Test Case:|$)'
        matches = re.findall(test_case_pattern, verification_plan_content, re.DOTALL)
        
        for test_id, content in matches:
            test_case = {
                'test_id': test_id.strip(),
                'content': content.strip(),
                'full_content': f"### Test Case: {test_id}\n{content}".strip()
            }
            test_cases.append(test_case)
        
        return test_cases

    def _clean_uvm_test_code(self, code_content: str) -> str:
        """
        Clean and validate UVM SystemVerilog test code.
        
        Args:
            code_content (str): Raw UVM test code
            
        Returns:
            str: Cleaned UVM test code
        """
        # Remove any markdown code block markers
        code_content = re.sub(r'```systemverilog\n?', '', code_content)
        code_content = re.sub(r'```\n?', '', code_content)
        
        # Remove any extra explanatory text that might be included
        lines = code_content.split('\n')
        cleaned_lines = []
        inside_code = False
        
        for line in lines:
            # Start collecting from the first meaningful SystemVerilog line
            if (not inside_code and 
                (line.strip().startswith('//') or 
                 line.strip().startswith('`include') or
                 line.strip().startswith('import') or
                 line.strip().startswith('class') or
                 line.strip().startswith('module'))):
                inside_code = True
            
            if inside_code:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()

    def retrieve_context(self, query: str, context_type: str, top_k: int = 3) -> str:
        """
        Retrieve relevant context using RAG for a given query and context type.
        
        Args:
            query (str): Search query
            context_type (str): Type of context to retrieve (specs, regmaps, uvm_examples, etc.)
            top_k (int): Number of top results to retrieve
            
        Returns:
            str: Retrieved context as formatted string
        """
        doc_type_map = {
            "specs": "spec",
            "regmaps": "regmap", 
            "uvm_examples": "uvm_example",
            "hal": "hal",
            "c_examples": "c_example"
        }
        
        doc_type_filter = doc_type_map.get(context_type, context_type)
        
        chunks = retrieve_relevant_chunks(
            query_text=query,
            top_k=top_k,
            doc_type_filter=doc_type_filter
        )
        
        if chunks:
            return "\n\n---\n\n".join(chunks)
        else:
            return f"No {context_type} context retrieved."

    def get_timestamp(self) -> str:
        """Get current timestamp string."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _extract_available_uvm_sequences(self) -> str:
        """
        Dynamically extract all available UVM sequence names from the knowledge base.
        
        Returns:
            str: Formatted list of available UVM sequence names
        """
        # Query all UVM examples to find sequence definitions
        all_uvm_chunks = retrieve_relevant_chunks(
            query_text="class extends uvm_sequence",
            top_k=20, doc_type_filter="uvm_example"
        )
        
        sequence_names = set()
        
        # Extract class names that extend uvm_sequence
        for chunk in all_uvm_chunks:
            lines = chunk.split('\n')
            for line in lines:
                line = line.strip()
                # Look for class definitions that extend uvm_sequence or similar patterns
                if 'class ' in line and ('extends' in line or ':' in line):
                    # Pattern: class sequence_name extends base_class
                    import re
                    patterns = [
                        r'class\s+(\w+)\s+extends\s+\w*sequence',
                        r'class\s+(\w+)\s+extends\s+base_sequence',
                        r'class\s+(\w+)\s+extends\s+axi_base_seq',
                        r'class\s+(\w+)\s*:\s*',  # For other inheritance patterns
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, line, re.IGNORECASE)
                        if match:
                            seq_name = match.group(1)
                            # Filter out base classes and utility classes
                            if not seq_name.endswith('_base') and 'base' not in seq_name.lower():
                                sequence_names.add(seq_name)
                            break
        
        # Format the sequence list
        if sequence_names:
            sequence_list = sorted(list(sequence_names))
            formatted_sequences = "Available UVM Sequences:\n"
            for seq in sequence_list:
                formatted_sequences += f"- {seq}\n"
            formatted_sequences += "\nSequence Descriptions:\n"
            
            # Add brief descriptions based on naming patterns
            for seq in sequence_list:
                if 'axi' in seq.lower() and 'read' in seq.lower():
                    formatted_sequences += f"- {seq}: For AXI read operations\n"
                elif 'axi' in seq.lower() and 'write' in seq.lower():
                    formatted_sequences += f"- {seq}: For AXI write operations\n"
                elif 'axi' in seq.lower() and 'burst' in seq.lower():
                    formatted_sequences += f"- {seq}: For AXI burst transactions\n"
                elif 'csr' in seq.lower() or 'register' in seq.lower():
                    formatted_sequences += f"- {seq}: For CSR/register access operations\n"
                elif 'interrupt' in seq.lower():
                    formatted_sequences += f"- {seq}: For interrupt testing scenarios\n"
                elif 'cache' in seq.lower():
                    formatted_sequences += f"- {seq}: For cache coherency testing\n"
                elif 'memory' in seq.lower():
                    formatted_sequences += f"- {seq}: For memory operations\n"
                elif 'pipeline' in seq.lower():
                    formatted_sequences += f"- {seq}: For instruction pipeline testing\n"
                else:
                    formatted_sequences += f"- {seq}: Available for verification scenarios\n"
            
            return formatted_sequences
        else:
            return "No UVM sequences found in knowledge base."