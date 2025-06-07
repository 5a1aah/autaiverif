#!/usr/bin/env python3
"""
UVM Verification Plan Generator

This script generates UVM-specific verification plans using the RAG approach.
It retrieves relevant context from specifications, register maps, and UVM examples
to create comprehensive UVM verification plans.
"""

import os
import sys
import logging
from pathlib import Path

# Add the parent directory to the path so we can import from scripts
sys.path.append(str(Path(__file__).parent.parent))

from scripts.common_utils import load_template, setup_logging, get_openrouter_client
from scripts.automator import ASICVerificationAutomator


def generate_uvm_verification_plan(feature_description, output_dir="generated_outputs/uvm_verification_plans"):
    """
    Generate a UVM verification plan for the given feature description.
    
    Args:
        feature_description (str): Description of the ASIC feature to verify
        output_dir (str): Directory to save the generated verification plan
        
    Returns:
        str: Path to the generated verification plan file
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize the automator
        automator = ASICVerificationAutomator()
        
        # Load the UVM verification plan prompt template
        template_path = Path(__file__).parent.parent / "prompts" / "stage1_uvm_verif_plan_prompt.txt"
        if not template_path.exists():
            raise FileNotFoundError(f"UVM verification plan template not found: {template_path}")
        
        prompt_template = load_template(str(template_path))
        
        # Retrieve relevant context using RAG
        logger.info("Retrieving relevant context for UVM verification plan...")
        
        # Get specification context
        spec_context = automator.retrieve_context(
            feature_description, 
            "specs", 
            top_k=5
        )
        
        # Get register map context
        regmap_context = automator.retrieve_context(
            feature_description, 
            "regmaps", 
            top_k=5
        )
        
        # Get UVM examples context
        uvm_context = automator.retrieve_context(
            feature_description, 
            "uvm_examples", 
            top_k=3
        )
        
        # Format the prompt
        formatted_prompt = prompt_template.format(
            feature_description=feature_description,
            retrieved_spec_context=spec_context,
            retrieved_regmap_context=regmap_context,
            retrieved_uvm_context=uvm_context
        )
        
        # Generate the verification plan using LLM
        logger.info("Generating UVM verification plan...")
        client = get_openrouter_client()
        
        response = client.chat.completions.create(
            model="deepseek/deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert UVM verification engineer. Generate comprehensive UVM verification plans following the exact format specified."
                },
                {
                    "role": "user", 
                    "content": formatted_prompt
                }
            ],
            temperature=0.2,
            max_tokens=4000
        )
        
        verification_plan = response.choices[0].message.content
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename
        safe_feature_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in feature_description)
        safe_feature_name = safe_feature_name[:50]  # Limit length
        filename = f"uvm_verif_plan_{safe_feature_name}.md"
        output_path = os.path.join(output_dir, filename)
        
        # Save the verification plan
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# UVM Verification Plan: {feature_description}\n\n")
            f.write(f"**Generated on:** {automator.get_timestamp()}\n\n")
            f.write("---\n\n")
            f.write(verification_plan)
        
        logger.info(f"UVM verification plan generated successfully: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error generating UVM verification plan: {str(e)}")
        raise


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python generate_uvm_verif_plan.py <feature_description>")
        print("Example: python generate_uvm_verif_plan.py 'CLINT timer interrupt functionality'")
        sys.exit(1)
    
    feature_desc = sys.argv[1]
    try:
        output_file = generate_uvm_verification_plan(feature_desc)
        print(f"UVM verification plan generated: {output_file}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
