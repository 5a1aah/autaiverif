import argparse
import sys
from pathlib import Path
import json
import os
from datetime import datetime

# Add project root to sys.path to allow `from scripts import ...`
PROJECT_ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT_DIR))

from scripts import common_utils # For early RAG initialization
from scripts.populate_kb import populate_knowledge_base
# These now act as wrappers for the automator class methods
from scripts.generate_verif_plan import generate_verification_plan
from scripts.generate_c_tests import generate_c_tests_from_plan # Renamed function for clarity
from scripts.plan_to_excel import convert_plan_to_excel # <--- NEW IMPORT

# Add these imports at the top
from scripts.feature_extractor import SpecFeatureExtractor
from scripts.unified_generator import UnifiedVerificationGenerator
from scripts.batch_processor import BatchProcessor

def main():
    parser = argparse.ArgumentParser(description="ASIC Verification Automation Orchestrator")
    
    # Add environment configuration arguments
    parser.add_argument('--openrouter-key', 
                      type=str, 
                      default=os.getenv('OPENROUTER_API_KEY', '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'),
                      help='OpenRouter API key (default: env var or hardcoded)')
    parser.add_argument('--deepseek-model',
                      type=str, 
                      default=os.getenv('DEEPSEEK_MODEL_NAME_DEFAULT', 'deepseek/deepseek-chat-v3-0324:free'),
                      help='DeepSeek model name (default: env var or hardcoded)')

    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

    # Update command handlers to use these configurations
    def handle_generate_all(args):
        common_utils.OPENROUTER_API_KEY = args.openrouter_key
        common_utils.DEEPSEEK_MODEL_NAME_DEFAULT = args.deepseek_model
        if not args.spec_files and not args.features_file:
            print("Error: You must provide either --spec_files or --features_file for generate_all.")
            return
        if args.spec_files:
            print(f"Starting unified generation from specification files: {', '.join(args.spec_files)}...")
        if args.features_file:
            print(f"Starting unified generation using features file: {args.features_file}...")
        if args.hal_file:
            print(f"Using HAL file for context: {args.hal_file}")
        if args.memmap_file:
            print(f"Using memory map file for context: {args.memmap_file}")
        if args.test_example_file:
            print(f"Using test example file for context: {args.test_example_file}")

        generator = UnifiedVerificationGenerator()
        
        if args.unified:
            print("Generating a single unified plan and associated tests...")
            if args.features_file:
                try:
                    with open(args.features_file, 'r', encoding='utf-8') as f:
                        features = json.load(f)
                except Exception as e:
                    print(f"Error loading features file {args.features_file}: {e}")
                    return
            elif args.spec_files: # Should always be true if features_file is not provided, due to check above
                extractor = SpecFeatureExtractor() # We need an extractor if using spec_files
                features = extractor.extract_features_from_files(
                    file_paths=args.spec_files,
                    hal_path=args.hal_file,
                    memmap_path=args.memmap_file,
                    test_example_path=args.test_example_file
                )
            else: # This case should ideally not be reached if the initial check is robust
                 print("Error: Insufficient input for unified generation. Provide specs or a feature file.")
                 return

            results = generator.generate_unified_plan_and_tests(
                features=features,
                output_dir=args.output_dir,
                hal_file=args.hal_file,
                memmap_file=args.memmap_file,
                test_example_file=args.test_example_file
            )
            print(f"\\nUnified generation completed. Results:")
            print(f"  - Unified Plan: {results.get('plan_file', 'N/A')}")
            print(f"  - Test Files: {len(results.get('test_files', []))} generated.")
            # Add more details from results as needed, e.g., path to test files
            print(f"  - Excel Report: {results.get('excel_file', 'N/A')}")
            print(f"  - Features Covered: {results.get('features_count', 'N/A')}")

        else:
            print("Generating verification artifacts for each feature individually...")
            # This path implies using generate_all_from_specs which handles feature extraction internally
            # if spec_files are provided, or loads from features_file.
            results = generator.generate_all_from_specs(
                spec_files=args.spec_files if args.spec_files else [], # Pass empty list if not provided
                output_dir=args.output_dir,
                extract_features=not bool(args.features_file), # Extract if no features_file
                features_file=args.features_file,
                hal_file=args.hal_file,
                memmap_file=args.memmap_file,
                test_example_file=args.test_example_file
            )
            print(f"\\nIndividual artifact generation completed. Summary:")
            print(f"  - Total Features Processed: {results.get('total_features', 'N/A')}")
            print(f"  - Successful Plans: {results.get('successful_plans', 'N/A')}")
            print(f"  - Successful Test Sets: {results.get('successful_tests', 'N/A')}") # Assuming this counts sets of tests
            print(f"  - Successful Excel Reports: {results.get('successful_excel', 'N/A')}")
            if results.get('failed_features'):
                print(f"  - Failed Features: {len(results['failed_features'])}")
                # for failed in results['failed_features'][:3]: # Sample of failed features
                #     print(f"    - {failed.get('name', 'Unknown Feature')}: {failed.get('error', 'Unknown Error')}")
            print(f"  Check the directory \'{args.output_dir}\' for detailed outputs and summary report.")

    parser_populate = subparsers.add_parser("populate_kb", help="Process source documents and populate the RAG knowledge base.")
    parser_populate.set_defaults(func=handle_populate_kb)

    parser_gen_plan = subparsers.add_parser("gen_plan", help="Generate a verification plan for an ASIC feature.")
    parser_gen_plan.add_argument("feature_description", type=str, help="Description of the ASIC feature.")
    parser_gen_plan.add_argument("--spec_file", type=str, help="Optional: Path to a specific ASIC specification file to use as primary context.")
    parser_gen_plan.add_argument("--addr_map_file", type=str, help="Optional: Path to a specific address map file to use as primary context.")
    # Add API configuration arguments
    parser_gen_plan.add_argument('--openrouter-key', 
                              type=str, 
                              default=os.getenv('OPENROUTER_API_KEY', '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'),
                              help='OpenRouter API key (default: env var or hardcoded)')
    parser_gen_plan.add_argument('--llm-model',
                              type=str, 
                              default=os.getenv('DEEPSEEK_MODEL_NAME_DEFAULT', 'deepseek/deepseek-chat-v3-0324:free'),
                              help='DeepSeek model name (default: env var or hardcoded)')    # output_format is now handled by the prompt to the LLM within automator. Output is .md
    parser_gen_plan.set_defaults(func=handle_gen_plan)
    
    parser_gen_tests = subparsers.add_parser("gen_tests", help="Generate C tests from a verification plan.")
    parser_gen_tests.add_argument("--plan_file", required=True, type=str, help="Path to a verification plan file (e.g., .md generated by gen_plan).")
    parser_gen_tests.add_argument("--addr_map_file", type=str, help="Optional: Path to an address map file if not well-covered by RAG from plan context.")
    parser_gen_tests.add_argument("--output-dir", type=str, help="Optional: Custom output directory for generated C test files. If not specified, uses default generated_outputs/c_tests/c_tests_generated.")
    # Add API configuration arguments
    parser_gen_tests.add_argument('--openrouter-key', 
                              type=str, 
                              default=os.getenv('OPENROUTER_API_KEY', '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'),
                              help='OpenRouter API key (default: env var or hardcoded)')
    parser_gen_tests.add_argument('--deepseek-model',
                              type=str, 
                              default=os.getenv('DEEPSEEK_MODEL_NAME_DEFAULT', 'deepseek/deepseek-chat-v3-0324:free'),
                              help='DeepSeek model name (default: env var or hardcoded)')
    parser_gen_tests.set_defaults(func=handle_gen_tests)

    # --- Add new subparser for plan_to_excel ---
    parser_plan_to_excel = subparsers.add_parser("plan_to_excel", help="Convert a Markdown verification plan to an Excel file.")
    parser_plan_to_excel.add_argument("--plan_file", required=True, type=str, help="Path to the input Markdown verification plan file.")
    parser_plan_to_excel.add_argument("--excel_file", required=True, type=str, help="Path for the output Excel file (e.g., generated_outputs/excel_reports/report.xlsx).")
    parser_plan_to_excel.set_defaults(func=handle_plan_to_excel)
    # --- End of new subparser ---
    
    # --- Add new subparser for feature extraction ---
    parser_extract_features = subparsers.add_parser("extract_features", help="Extract design features from specification documents.")
    parser_extract_features.add_argument("spec_files", nargs='+', type=str, help="Paths to the ASIC specification files (e.g., *.pdf, *.txt).")
    parser_extract_features.add_argument("--hal_file", type=str, help="Optional: Path to a Hardware Abstraction Layer (HAL) file.")
    parser_extract_features.add_argument("--memmap_file", type=str, help="Optional: Path to a memory map file.")
    parser_extract_features.add_argument("--test_example_file", type=str, help="Optional: Path to a test example file.")
    parser_extract_features.add_argument("--output", type=str, default="generated_outputs/extracted_features", help="Base path to save the extracted features (extension will be added based on format).")
    parser_extract_features.add_argument("--format", type=str, choices=['json', 'csv', 'all'], default='all', help="Output format for the features file: json, csv, or all (default: all).")
    parser_extract_features.add_argument("--verbose", action="store_true", help="Enable verbose output with detailed feature information.")    
    parser_extract_features.set_defaults(func=handle_extract_features)
    # --- End of new subparser ---

    # --- Add new subparser for comprehensive verification ---
    parser_generate_comprehensive = subparsers.add_parser("generate_comprehensive", help="Extract features and generate comprehensive verification plans and tests for all features.")
    parser_generate_comprehensive.add_argument("spec_files", nargs='+', type=str, help="Paths to the ASIC specification files (e.g., *.pdf, *.txt).")
    parser_generate_comprehensive.add_argument("--hal_file", type=str, help="Optional: Path to a Hardware Abstraction Layer (HAL) file.")
    parser_generate_comprehensive.add_argument("--memmap_file", type=str, help="Optional: Path to a memory map file.")
    parser_generate_comprehensive.add_argument("--test_example_file", type=str, help="Optional: Path to a test example file.")
    parser_generate_comprehensive.add_argument("--output_dir", type=str, default="generated_outputs/comprehensive_verification", help="Base directory to save all generated artifacts.")
    parser_generate_comprehensive.add_argument("--unified_plan", action="store_true", help="Generate a single unified verification plan for all features (default: individual plans per feature).")
    parser_generate_comprehensive.add_argument("--verbose", action="store_true", help="Enable verbose output with detailed information.")
    parser_generate_comprehensive.set_defaults(func=handle_generate_comprehensive)
    # --- End of comprehensive verification subparser ---

    # --- Add new subparser for unified generation ---
    parser_generate_all = subparsers.add_parser("generate_all", help="Generate all verification artifacts (plan, tests, Excel) for features.")
    parser_generate_all.add_argument("--spec_files", nargs='*', type=str, help="Paths to ASIC specification files (required if --features_file is not used).")
    parser_generate_all.add_argument("--features_file", type=str, help="Optional: Path to a JSON file containing pre-extracted features.")
    parser_generate_all.add_argument("--hal_file", type=str, help="Optional: Path to a Hardware Abstraction Layer (HAL) file to be used as context.")
    parser_generate_all.add_argument("--memmap_file", type=str, help="Optional: Path to a memory map file to be used as context.")
    parser_generate_all.add_argument("--test_example_file", type=str, help="Optional: Path to a test example file to be used as context.")
    parser_generate_all.add_argument("--output_dir", type=str, default="generated_outputs/unified_generation", help="Directory to save all generated artifacts.")
    parser_generate_all.add_argument("--unified", action="store_true", help="Generate a single unified plan and test suite for all features. If not set, generates artifacts per feature.")
    parser_generate_all.set_defaults(func=handle_generate_all)
    # --- End of new subparser ---    

    # --- Add new subparser for UVM verification plan generation ---
    parser_gen_uvm_plan = subparsers.add_parser("gen_uvm_plan", help="Generate a UVM verification plan for an ASIC feature.")
    parser_gen_uvm_plan.add_argument("feature_description", type=str, help="Description of the ASIC feature to verify with UVM.")
    parser_gen_uvm_plan.add_argument("--spec_file", type=str, help="Optional: Path to the ASIC specification file for additional context.")
    parser_gen_uvm_plan.add_argument("--address_map_file", type=str, help="Optional: Path to the address map file for register-level testing context.")
    parser_gen_uvm_plan.add_argument("--output", type=str, default="generated_outputs/uvm_verification_plans", help="Directory to save the generated UVM verification plan.")
    parser_gen_uvm_plan.set_defaults(func=handle_gen_uvm_plan)

    # --- Add new subparser for UVM test generation ---
    parser_gen_uvm_tests = subparsers.add_parser("gen_uvm_tests", help="Generate UVM test files from a verification plan.")
    parser_gen_uvm_tests.add_argument("plan_file", type=str, help="Path to the UVM verification plan file (Markdown format).")
    parser_gen_uvm_tests.add_argument("--output", type=str, default="generated_outputs/uvm_tests", help="Directory to save the generated UVM test files.")
    parser_gen_uvm_tests.set_defaults(func=handle_gen_uvm_tests)
    # --- End of UVM subparsers ---

    args = parser.parse_args()
    
    # Set API configuration from command line arguments for all commands
    if hasattr(args, 'openrouter_key'):
        common_utils.OPENROUTER_API_KEY = args.openrouter_key
        print(f"Using API key: {args.openrouter_key[:20]}..." if args.openrouter_key else "No API key provided")
    
    if hasattr(args, 'deepseek_model'):
        common_utils.DEEPSEEK_MODEL_NAME_DEFAULT = args.deepseek_model
        print(f"Using model: {args.deepseek_model}")
    
    # Initialize common utilities only if not doing plan_to_excel,
    # as it doesn't need RAG or LLM calls for that specific task.
    if args.command != "plan_to_excel":
        print("Initializing common utilities (e.g., ChromaDB client)...")
        common_utils.initialize_chromadb_client_and_collection() # Ensures RAG is ready
        print("Initialization complete.")
    else:
        # This else block is optional, just for a different message for excel conversion
        print(f"Executing '{args.command}' command...")


    args.func(args)

def handle_populate_kb(args):
    print("Starting Knowledge Base Population...")
    populate_knowledge_base() # From scripts.populate_kb
    print("Knowledge Base Population finished.")

def handle_gen_plan(args):
    # Set API configuration from command line arguments
    if hasattr(args, 'openrouter_key'):
        common_utils.OPENROUTER_API_KEY = args.openrouter_key
        print(f"Using API key: {args.openrouter_key[:20]}..." if args.openrouter_key else "No API key provided")
    
    if hasattr(args, 'deepseek_model'):
        common_utils.DEEPSEEK_MODEL_NAME_DEFAULT = args.deepseek_model
        print(f"Using model: {args.deepseek_model}")
    
    print(f"Starting Verification Plan Generation for feature: {args.feature_description}")
    generate_verification_plan( # From scripts.generate_verif_plan
        feature_description=args.feature_description
        # asic_spec_file_path=args.spec_file,
        # address_map_file_path=args.addr_map_file
    )
    print("Verification Plan Generation finished.")

def handle_gen_tests(args):
    print(f"DEBUG: handle_gen_tests called with args: {args}")
    print(f"DEBUG: args.plan_file = {args.plan_file}")
    print(f"DEBUG: hasattr(args, 'addr_map_file') = {hasattr(args, 'addr_map_file')}")
    
    # Set API configuration from command line arguments
    if hasattr(args, 'openrouter_key'):
        common_utils.OPENROUTER_API_KEY = args.openrouter_key
        print(f"Using API key: {args.openrouter_key[:20]}..." if args.openrouter_key else "No API key provided")
    if hasattr(args, 'deepseek_model'):
        common_utils.DEEPSEEK_MODEL_NAME_DEFAULT = args.deepseek_model
        print(f"Using model: {args.deepseek_model}")
    
    print("Starting C Test Generation...")
    plan_file_path = Path(args.plan_file)
    if not plan_file_path.is_file():
        print(f"Error: Verification plan file not found at {plan_file_path}")
        return
    
    try:
        with open(plan_file_path, 'r', encoding='utf-8') as f:
            plan_content = f.read()
        
        print(f"DEBUG: Plan content length: {len(plan_content)} characters")
        print(f"DEBUG: Plan content preview: {plan_content[:200]}...")
        print(f"DEBUG: args.addr_map_file = {getattr(args, 'addr_map_file', 'NOT_SET')}")
        print(f"DEBUG: args.output_dir = {getattr(args, 'output_dir', 'NOT_SET')}")
        
        generate_c_tests_from_plan( # From scripts.generate_c_tests
            verification_plan_text=plan_content,
            address_map_file_path=args.addr_map_file,
            output_dir=getattr(args, 'output_dir', None)
        )
    except Exception as e:
        print(f"Error processing plan file {plan_file_path} for C test generation: {e}")

    print("C Test Generation finished.")

# --- Add new handler function for excel conversion ---
def handle_plan_to_excel(args):
    print(f"Converting Markdown plan '{args.plan_file}' to Excel '{args.excel_file}'...")
    convert_plan_to_excel(args.plan_file, args.excel_file) # From scripts.plan_to_excel
    print("Plan to Excel conversion finished.")
# --- End of new handler function ---

def handle_extract_features(args):
    print(f"Extracting features from specification files: {', '.join(args.spec_files)}")
    if args.hal_file:
        print(f"Including HAL file: {args.hal_file}")
    if args.memmap_file:
        print(f"Including memory map file: {args.memmap_file}")
    if args.test_example_file:
        print(f"Including test example file: {args.test_example_file}")
    
    print(f"Output format: {args.format}")
    print(f"Output base path: {args.output}")

    extractor = SpecFeatureExtractor()
    features = extractor.extract_features_from_files(
        file_paths=args.spec_files,
        hal_path=args.hal_file,
        memmap_path=args.memmap_file,
        test_example_path=args.test_example_file
    )
    
    print(f"\nSaving extracted features...")
    extractor.save_features_to_file(features, args.output, format=args.format)
    print(f"Extracted {len(features)} features and saved in {args.format} format(s)")
    
    # Print detailed summary if verbose or show basic summary
    if args.verbose:
        print(f"\nDETAILED FEATURE SUMMARY:")
        print(f"=" * 40)
        
        # Group by category for verbose output
        categories = {}
        for feature in features:
            cat = feature['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(feature)
        
        for category, cat_features in categories.items():
            print(f"\n{category.upper()} ({len(cat_features)} features):")
            for feature in cat_features:
                print(f"  • Name: {feature['name']}")
                print(f"    Priority: {feature.get('priority', 'N/A')}")
                print(f"    Source: {feature.get('source_file', 'N/A')}")
                if feature.get('context'):
                    print(f"    Context: {feature['context'][:100]}...")
                print()
    else:        # Basic summary
        print(f"\nBASIC SUMMARY:")
        print(f"=" * 20)
        categories = {}
        for feature in features:
            cat = feature['category']
            categories[cat] = categories.get(cat, 0) + 1
        
        for category, count in categories.items():
            print(f"  {category}: {count} features")
        
        # Show sample features
        print(f"\nSample features (first 5):")
        for feature in features[:5]:
            print(f"  • {feature['name']} ({feature['category']}) - {feature.get('source_file', 'N/A')}")
        if len(features) > 5:
            print(f"  ... and {len(features)-5} more.")
        
        print(f"\nUse --verbose flag for detailed feature information.")

def handle_generate_comprehensive(args):
    """Generate comprehensive verification artifacts for all extracted features"""
    print("=" * 60)
    print("COMPREHENSIVE VERIFICATION GENERATION")
    print("=" * 60)
    
    # Set API configuration
    common_utils.OPENROUTER_API_KEY = args.openrouter_key
    common_utils.DEEPSEEK_MODEL_NAME_DEFAULT = args.deepseek_model
    
    print(f"Processing specification files: {', '.join(args.spec_files)}")
    if args.hal_file:
        print(f"Including HAL file: {args.hal_file}")
    if args.memmap_file:
        print(f"Including memory map file: {args.memmap_file}")
    if args.test_example_file:
        print(f"Including test example file: {args.test_example_file}")
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Extract features
    print(f"\n{'='*50}")
    print("STEP 1: EXTRACTING FEATURES")
    print(f"{'='*50}")
    
    extractor = SpecFeatureExtractor()
    features = extractor.extract_features_from_files(
        file_paths=args.spec_files,
        hal_path=args.hal_file,
        memmap_path=args.memmap_file,
        test_example_path=args.test_example_file
    )
    
    if not features:
        print("No features extracted. Exiting.")
        return
    
    # Save extracted features
    features_file = output_dir / "extracted_features.json"
    extractor.save_features_to_file(features, str(features_file), format='json')
    print(f"Extracted {len(features)} features and saved to {features_file}")
    
    if args.verbose:
        print("\nExtracted features:")
        for i, feature in enumerate(features, 1):
            print(f"  {i}. {feature['name']} ({feature['category']}) - Priority: {feature.get('priority', 'N/A')}")
    
    # Step 2: Generate verification plans
    print(f"\n{'='*50}")
    print("STEP 2: GENERATING VERIFICATION PLANS")
    print(f"{'='*50}")
    
    plans_dir = output_dir / "verification_plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    
    tests_dir = output_dir / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    
    excel_dir = output_dir / "excel_reports" 
    excel_dir.mkdir(parents=True, exist_ok=True)
    
    if args.unified_plan:
        # Generate single unified plan for all features
        print("Generating unified verification plan for all features...")
        unified_plan_file = plans_dir / "unified_verification_plan.md"
        unified_excel_file = excel_dir / "unified_verification_report.xlsx"
        
        # Create unified feature description
        unified_description = f"Comprehensive verification for {len(features)} features:\n"
        for feature in features:
            unified_description += f"- {feature['name']} ({feature['category']})\n"
        
        try:
            # Generate unified plan
            generate_verification_plan(
                feature_description=unified_description,
                asic_spec_file_path=args.spec_files[0] if args.spec_files else None,
                address_map_file_path=args.memmap_file,
                output_file=str(unified_plan_file)
            )
            print(f"  ✓ Unified plan generated: {unified_plan_file}")
            
            # Generate tests for unified plan
            with open(unified_plan_file, 'r', encoding='utf-8') as f:
                plan_content = f.read()
            
            unified_tests_dir = tests_dir / "unified_tests"
            unified_tests_dir.mkdir(parents=True, exist_ok=True)
            
            generate_c_tests_from_plan(
                verification_plan_text=plan_content,
                address_map_file_path=args.memmap_file,
                output_dir=str(unified_tests_dir)
            )
            print(f"  ✓ Tests generated in: {unified_tests_dir}")
            
            # Convert to Excel
            convert_plan_to_excel(str(unified_plan_file), str(unified_excel_file))
            print(f"  ✓ Excel report generated: {unified_excel_file}")
            
        except Exception as e:
            print(f"  ✗ Error generating unified plan: {e}")
    
    else:
        # Generate individual plans for each feature
        print(f"Generating individual verification plans for {len(features)} features...")
        
        successful_plans = 0
        successful_tests = 0
        successful_excel = 0
        failed_features = []
        
        for i, feature in enumerate(features, 1):
            feature_name = feature['name']
            safe_name = "".join(c for c in feature_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_name = safe_name.replace(' ', '_')[:50]  # Limit length
            
            print(f"  Processing feature {i}/{len(features)}: {feature_name}")
            
            try:
                # Generate verification plan
                plan_file = plans_dir / f"verif_plan_{safe_name}.md"
                excel_file = excel_dir / f"verif_report_{safe_name}.xlsx"
                feature_tests_dir = tests_dir / f"tests_{safe_name}"
                feature_tests_dir.mkdir(parents=True, exist_ok=True)
                
                # Create detailed feature description
                feature_description = f"""
Feature: {feature['name']}
Category: {feature['category']}
Priority: {feature.get('priority', 'medium')}
Source: {feature.get('source_file', 'N/A')}

Context:
{feature.get('context', 'No additional context available.')}
"""
                
                # Generate verification plan
                generate_verification_plan(
                    feature_description=feature_description,
                    asic_spec_file_path=args.spec_files[0] if args.spec_files else None,
                    address_map_file_path=args.memmap_file,
                    output_file=str(plan_file)
                )
                successful_plans += 1
                
                if args.verbose:
                    print(f"    ✓ Plan: {plan_file}")
                
                # Generate tests from plan
                with open(plan_file, 'r', encoding='utf-8') as f:
                    plan_content = f.read()
                
                generate_c_tests_from_plan(
                    verification_plan_text=plan_content,
                    address_map_file_path=args.memmap_file,
                    output_dir=str(feature_tests_dir)
                )
                successful_tests += 1
                
                if args.verbose:
                    print(f"    ✓ Tests: {feature_tests_dir}")
                
                # Convert to Excel
                convert_plan_to_excel(str(plan_file), str(excel_file))
                successful_excel += 1
                
                if args.verbose:
                    print(f"    ✓ Excel: {excel_file}")
                
            except Exception as e:
                print(f"    ✗ Error processing feature '{feature_name}': {e}")
                failed_features.append({
                    'name': feature_name,
                    'category': feature['category'],
                    'error': str(e)
                })
    
    # Step 3: Generate summary report
    print(f"\n{'='*50}")
    print("STEP 3: GENERATING SUMMARY REPORT")
    print(f"{'='*50}")
    
    summary_file = output_dir / "comprehensive_summary.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("COMPREHENSIVE VERIFICATION GENERATION SUMMARY\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Generation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Specification Files: {', '.join(args.spec_files)}\n")
        if args.hal_file:
            f.write(f"HAL File: {args.hal_file}\n")
        if args.memmap_file:
            f.write(f"Memory Map File: {args.memmap_file}\n")
        f.write(f"Output Directory: {output_dir}\n\n")
        
        f.write("RESULTS:\n")
        f.write("-" * 30 + "\n")
        f.write(f"Total Features Extracted: {len(features)}\n")
        
        if args.unified_plan:
            f.write("Verification Mode: Unified Plan\n")
            f.write(f"Unified Plan: {plans_dir / 'unified_verification_plan.md'}\n")
            f.write(f"Unified Tests: {tests_dir / 'unified_tests'}\n")
            f.write(f"Unified Excel: {excel_dir / 'unified_verification_report.xlsx'}\n")
        else:
            f.write("Verification Mode: Individual Plans\n")
            f.write(f"Successful Plans: {successful_plans}/{len(features)}\n")
            f.write(f"Successful Test Generations: {successful_tests}/{len(features)}\n")
            f.write(f"Successful Excel Reports: {successful_excel}/{len(features)}\n")
            
            if failed_features:
                f.write(f"\nFAILED FEATURES ({len(failed_features)}):\n")
                f.write("-" * 20 + "\n")
                for failed in failed_features:
                    f.write(f"- {failed['name']} ({failed['category']}): {failed['error']}\n")
        
        f.write(f"\nFEATURES BY CATEGORY:\n")
        f.write("-" * 20 + "\n")
        categories = {}
        for feature in features:
            cat = feature['category']
            categories[cat] = categories.get(cat, 0) + 1
        
        for category, count in categories.items():
            f.write(f"{category}: {count} features\n")
    
    print(f"Summary report generated: {summary_file}")
      # Final summary
    print(f"\n{'='*60}")
    print("COMPREHENSIVE VERIFICATION GENERATION COMPLETE")
    print(f"{'='*60}")
    print(f"Total Features: {len(features)}")
    print(f"Output Directory: {output_dir}")

def handle_gen_uvm_plan(args):
    """Handle UVM verification plan generation command."""
    print("DEBUG: handle_gen_uvm_plan called")
    common_utils.OPENROUTER_API_KEY = args.openrouter_key
    common_utils.DEEPSEEK_MODEL_NAME_DEFAULT = args.deepseek_model
    
    print(f"Generating UVM verification plan for: {args.feature_description}")
    
    # Read optional context files
    spec_text = None
    if args.spec_file:
        try:
            with open(args.spec_file, 'r', encoding='utf-8') as f:
                spec_text = f.read()
            print(f"Loaded specification context from: {args.spec_file}")
        except Exception as e:
            print(f"Warning: Could not read spec file {args.spec_file}: {e}")
    
    address_map_text = None
    if args.address_map_file:
        try:
            with open(args.address_map_file, 'r', encoding='utf-8') as f:
                address_map_text = f.read()
            print(f"Loaded address map context from: {args.address_map_file}")
        except Exception as e:
            print(f"Warning: Could not read address map file {args.address_map_file}: {e}")
    
    try:
        from scripts.automator import ASICVerificationAutomator
        from datetime import datetime
        
        # Initialize automator
        automator = ASICVerificationAutomator(
            api_key=args.openrouter_key,
            model_name=args.deepseek_model
        )
        
        # Generate UVM verification plan
        verification_plan = automator.generate_uvm_verification_plan(
            feature_description=args.feature_description,
            spec_text=spec_text,
            address_map_text=address_map_text
        )
        
        # Create output directory
        os.makedirs(args.output, exist_ok=True)
        
        # Generate filename
        safe_feature_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in args.feature_description)
        safe_feature_name = safe_feature_name[:50]  # Limit length
        filename = f"uvm_verif_plan_{safe_feature_name}.md"
        output_path = os.path.join(args.output, filename)
        
        # Save the verification plan
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# UVM Verification Plan: {args.feature_description}\n\n")
            f.write(f"**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            f.write(verification_plan)
        
        print(f"UVM verification plan generated successfully: {output_path}")
        
    except Exception as e:
        print(f"Error generating UVM verification plan: {e}")
        sys.exit(1)

def handle_gen_uvm_tests(args):
    """Handle UVM test generation command."""
    common_utils.OPENROUTER_API_KEY = args.openrouter_key
    common_utils.DEEPSEEK_MODEL_NAME_DEFAULT = args.deepseek_model
    
    print(f"Generating UVM tests from plan: {args.plan_file}")
    
    # Check if plan file exists
    if not os.path.exists(args.plan_file):
        print(f"Error: Verification plan file not found: {args.plan_file}")
        sys.exit(1)
    
    try:
        from scripts.automator import ASICVerificationAutomator
        from pathlib import Path
        
        # Initialize automator
        automator = ASICVerificationAutomator(
            api_key=args.openrouter_key,
            model_name=args.deepseek_model
        )
        
        # Read verification plan
        with open(args.plan_file, 'r', encoding='utf-8') as f:
            plan_content = f.read()
          # Generate UVM tests
        output_path = Path(args.output)
        generated_files = automator.generate_uvm_tests_from_plan(
            verification_plan_content=plan_content,
            output_path=output_path
        )
        
        print(f"\nUVM test generation completed!")
        print(f"Generated {len(generated_files)} UVM test files:")
        for file_path in generated_files:
            print(f"  - {file_path}")
        
    except Exception as e:
        print(f"Error generating UVM tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
