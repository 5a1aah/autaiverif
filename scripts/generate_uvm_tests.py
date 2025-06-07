#!/usr/bin/env python3
"""
UVM Test Generator

This script generates SystemVerilog UVM test files from verification plans.
It parses UVM verification plans and generates complete UVM test code for each test case.
"""

import os
import sys
import re
import logging
from pathlib import Path

# Add the parent directory to the path so we can import from scripts
sys.path.append(str(Path(__file__).parent.parent))

from scripts.common_utils import load_template, setup_logging, get_openrouter_client
from scripts.automator import ASICVerificationAutomator


def parse_uvm_test_cases(verification_plan_content):
    """
    Parse test cases from UVM verification plan content.
    
    Args:
        verification_plan_content (str): Content of the verification plan
        
    Returns:
        list: List of dictionaries containing test case information
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


def clean_uvm_test_code(code_content):
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
    
    return '\n'.join(cleaned_lines)


def generate_uvm_tests_from_plan(verification_plan_path, output_dir="generated_outputs/uvm_tests"):
    """
    Generate UVM test files from a verification plan.
    
    Args:
        verification_plan_path (str): Path to the verification plan file
        output_dir (str): Directory to save generated UVM tests
        
    Returns:
        list: List of paths to generated UVM test files
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Read the verification plan
        if not os.path.exists(verification_plan_path):
            raise FileNotFoundError(f"Verification plan not found: {verification_plan_path}")
        
        with open(verification_plan_path, 'r', encoding='utf-8') as f:
            plan_content = f.read()
        
        # Parse test cases from the plan
        test_cases = parse_uvm_test_cases(plan_content)
        logger.info(f"Found {len(test_cases)} test cases in verification plan")
        
        if not test_cases:
            logger.warning("No test cases found in verification plan")
            return []
        
        # Initialize the automator
        automator = ASICVerificationAutomator()
        
        # Load the UVM test generation prompt template
        template_path = Path(__file__).parent.parent / "prompts" / "stage2_uvm_test_gen_prompt.txt"
        if not template_path.exists():
            raise FileNotFoundError(f"UVM test generation template not found: {template_path}")
        
        prompt_template = load_template(str(template_path))
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        generated_files = []
        client = get_openrouter_client()
        
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"Generating test {i}/{len(test_cases)}: {test_case['test_id']}")
            
            try:
                # Extract feature description from test case for context retrieval
                feature_desc = test_case['test_id'] + " " + test_case['content'][:200]
                
                # Retrieve relevant context using RAG
                spec_context = automator.retrieve_context(feature_desc, "specs", top_k=3)
                regmap_context = automator.retrieve_context(feature_desc, "regmaps", top_k=3)
                uvm_context = automator.retrieve_context(feature_desc, "uvm_examples", top_k=2)
                
                # Format the prompt
                formatted_prompt = prompt_template.format(
                    test_case=test_case['full_content'],
                    retrieved_spec_context=spec_context,
                    retrieved_regmap_context=regmap_context,
                    retrieved_uvm_context=uvm_context
                )
                
                # Generate the UVM test using LLM
                response = client.chat.completions.create(
                    model="deepseek/deepseek-chat",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert UVM verification engineer. Generate complete, syntactically correct SystemVerilog UVM test code."
                        },
                        {
                            "role": "user",
                            "content": formatted_prompt
                        }
                    ],
                    temperature=0.1,
                    max_tokens=3000
                )
                
                uvm_test_code = response.choices[0].message.content
                
                # Clean the generated code
                cleaned_code = clean_uvm_test_code(uvm_test_code)
                
                # Generate filename
                safe_test_id = "".join(c if c.isalnum() or c in "_-" else "_" for c in test_case['test_id'])
                filename = f"test_{safe_test_id}.sv"
                output_path = os.path.join(output_dir, filename)
                
                # Add file header
                file_header = f"""// filepath: {output_path}
/**
 * @file {filename}
 * @brief UVM test for {test_case['test_id']}
 * 
 * Generated on: {automator.get_timestamp()}
 * From verification plan: {verification_plan_path}
 */

"""
                
                # Save the UVM test file
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(file_header + cleaned_code)
                
                generated_files.append(output_path)
                logger.info(f"Generated UVM test: {output_path}")
                
            except Exception as e:
                logger.error(f"Error generating test {test_case['test_id']}: {str(e)}")
                continue
        
        logger.info(f"Generated {len(generated_files)} UVM test files")
        return generated_files
        
    except Exception as e:
        logger.error(f"Error generating UVM tests from plan: {str(e)}")
        raise


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python generate_uvm_tests.py <verification_plan_path>")
        print("Example: python generate_uvm_tests.py ../generated_outputs/uvm_verification_plans/plan.md")
        sys.exit(1)
    
    plan_path = sys.argv[1]
    try:
        output_files = generate_uvm_tests_from_plan(plan_path)
        print(f"Generated {len(output_files)} UVM test files:")
        for file_path in output_files:
            print(f"  - {file_path}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
