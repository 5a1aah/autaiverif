import os
from pathlib import Path
import json
from .common_utils import call_deepseek_api, retrieve_relevant_chunks, load_prompt_template

GENERATED_PLANS_PATH = Path(__file__).resolve().parent.parent / "generated_outputs" / "verification_plans"

def generate_verification_plan(feature_description: str, output_format: str = "structured text"):
    """
    Generates a verification plan for a given ASIC feature.
    """
    if not feature_description:
        print("Error: Feature description cannot be empty.")
        return

    print(f"\nGenerating verification plan for feature: {feature_description}")

    # 1. Retrieve relevant context using RAG
    spec_context_chunks = retrieve_relevant_chunks(
        query_text=f"ASIC specification details for {feature_description}",
        top_k=3,
        doc_type_filter="spec"
    )
    regmap_context_chunks = retrieve_relevant_chunks(
        query_text=f"Register map information relevant to {feature_description}",
        top_k=2,
        doc_type_filter="regmap"
    )

    retrieved_spec_context = "\n\n---\n\n".join(spec_context_chunks) if spec_context_chunks else "No specific specification details retrieved."
    retrieved_regmap_context = "\n\n---\n\n".join(regmap_context_chunks) if regmap_context_chunks else "No specific register map details retrieved."

    # 2. Load prompt template
    prompt_template = load_prompt_template("stage1_verif_plan_prompt.txt")
    if not prompt_template:
        print("Error: Could not load verification plan prompt template.")
        return

    # 3. Populate the prompt
    formatted_prompt = prompt_template.replace("{{feature_description}}", feature_description)
    formatted_prompt = formatted_prompt.replace("{{retrieved_spec_context}}", retrieved_spec_context)
    formatted_prompt = formatted_prompt.replace("{{retrieved_regmap_context}}", retrieved_regmap_context)
    formatted_prompt = formatted_prompt.replace("{{output_format}}", output_format)


    # 4. Call the LLM API
    print("Sending request to LLM for verification plan generation...")
    try:
        llm_response = call_deepseek_api(formatted_prompt, temperature=0.6, max_tokens=3500) # Increased max_tokens for plans
    except Exception as e:
        print(f"Error calling LLM API: {e}")
        return

    if not llm_response or llm_response.startswith("Error:"):
        print(f"LLM API call failed or returned an error: {llm_response}")
        return

    # 5. Save the generated plan
    GENERATED_PLANS_PATH.mkdir(parents=True, exist_ok=True)
    safe_feature_name = "".join(c if c.isalnum() else "_" for c in feature_description[:50])
    file_extension = ".txt" # Default
    if output_format.lower() == "json":
        file_extension = ".json"
    elif output_format.lower() == "csv": # Note: LLM might struggle with perfect CSV directly
        file_extension = ".csv"
    
    output_filename = GENERATED_PLANS_PATH / f"verif_plan_{safe_feature_name}{file_extension}"
    
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(llm_response)
        print(f"\nVerification plan saved successfully to: {output_filename}")
        print("\n--- Generated Verification Plan ---")
        print(llm_response[:1000] + "..." if len(llm_response) > 1000 else llm_response) # Print a snippet
        print("--- End of Snippet ---")

    except IOError as e:
        print(f"Error saving verification plan to file: {e}")

    return llm_response


if __name__ == "__main__":
    # Example Usage:
    # Ensure your KB is populated first by running 01_populate_kb.py
    # And that you have some documents in knowledge_base_src for RAG to find.

    # test_feature = "SPI controller master mode data transmission with DMA"
    test_feature = input("Enter the ASIC feature to generate a verification plan for (e.g., 'SPI controller interrupt logic'): ")
    
    if test_feature:
        generate_verification_plan(test_feature, output_format="structured text") # or "JSON" or "CSV"
    else:
        print("No feature description provided. Exiting.")