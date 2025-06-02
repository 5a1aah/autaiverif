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
### Test Case: MOD_FUNC_001
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