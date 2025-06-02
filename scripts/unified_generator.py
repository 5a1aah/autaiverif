import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from .feature_extractor import SpecFeatureExtractor
from .automator import ASICVerificationAutomator
from .plan_to_excel import convert_plan_to_excel
from .generate_verif_plan import generate_verification_plan
from .generate_c_tests import generate_c_tests_from_plan

class UnifiedVerificationGenerator:
    """Generate verification plans and C tests for all features in one command."""
    
    def __init__(self):
        self.feature_extractor = SpecFeatureExtractor()
        self.automator = ASICVerificationAutomator()
        
    def generate_all_from_specs(self, 
                               spec_files: List[str],
                               output_dir: str = "generated_outputs",
                               extract_features: bool = True,
                               features_file: Optional[str] = None,
                               hal_file: Optional[str] = None, 
                               memmap_file: Optional[str] = None, 
                               test_example_file: Optional[str] = None) -> Dict[str, Any]:
        """Generate all verification artifacts from specifications."""
        
        # Create output directories
        output_path = Path(output_dir)
        plans_dir = output_path / "verification_plans"
        tests_dir = output_path / "c_tests"
        excel_dir = output_path / "excel_reports"
        features_dir = output_path / "extracted_features"
        
        for dir_path in [plans_dir, tests_dir, excel_dir, features_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Extract or load features
        if extract_features:
            print("Extracting features from specifications...")
            features = self.feature_extractor.extract_features_from_files(
                spec_files,
                hal_path=hal_file, 
                memmap_path=memmap_file, 
                test_example_path=test_example_file
            )
            
            # Save extracted features
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            features_output = features_dir / f"extracted_features_{timestamp}.json"
            self.feature_extractor.save_features_to_file(features, str(features_output))
        else:
            if not features_file or not Path(features_file).exists():
                raise ValueError("Features file must be provided when extract_features=False")
            
            with open(features_file, 'r', encoding='utf-8') as f:
                features = json.load(f)
        
        print(f"Processing {len(features)} features...")
        
        # Generate verification plans and tests for each feature
        results = {
            "total_features": len(features),
            "successful_plans": 0,
            "successful_tests": 0,
            "successful_excel": 0,
            "failed_features": [],
            "generated_files": {
                "plans": [],
                "tests": [],
                "excel": []
            }
        }
        
        for i, feature in enumerate(features, 1):
            feature_name = feature["name"]
            print(f"\n[{i}/{len(features)}] Processing feature: {feature_name}")
            
            try:
                # Generate verification plan
                plan_filename = f"verif_plan_{feature_name.replace(' ', '_').replace('/', '_')}.md"
                plan_path = plans_dir / plan_filename
                
                print(f"  Generating verification plan...")
                plan_content = generate_verification_plan(
                    feature_description=f"{feature_name}: {feature.get('description', feature.get('context', ''))}",
                    output_file=str(plan_path),
                    asic_spec_file_path=feature.get('source_file'),
                    address_map_file_path=memmap_file,
                    hal_file_path=hal_file,
                    test_example_file_path=test_example_file
                )
                
                if plan_content:
                    results["successful_plans"] += 1
                    results["generated_files"]["plans"].append(str(plan_path))
                    
                    # Generate C tests from the plan
                    print(f"  Generating C tests...")
                    test_results = generate_c_tests_from_plan(
                        verification_plan_text=plan_content,
                        output_dir=str(tests_dir / f"{feature_name.replace(' ', '_')}_tests"),
                        address_map_file_path=memmap_file,
                        hal_file_path=hal_file,
                        test_example_file_path=test_example_file
                    )
                    
                    if test_results:
                        results["successful_tests"] += 1
                        results["generated_files"]["tests"].extend(test_results)
                    
                    # Generate Excel report
                    print(f"  Generating Excel report...")
                    excel_filename = f"{feature_name.replace(' ', '_')}_verification_report.xlsx"
                    excel_path = excel_dir / excel_filename
                    
                    try:
                        convert_plan_to_excel(str(plan_path), str(excel_path))
                        results["successful_excel"] += 1
                        results["generated_files"]["excel"].append(str(excel_path))
                    except Exception as e:
                        print(f"    Warning: Excel generation failed: {e}")
                
            except Exception as e:
                print(f"  Error processing feature {feature_name}: {e}")
                results["failed_features"].append({
                    "feature": feature_name,
                    "error": str(e)
                })
        
        # Generate summary report
        self._generate_summary_report(results, features, output_path)
        
        return results
    
    def generate_unified_plan_and_tests(self, 
                                        features: List[Dict[str, Any]], 
                                        output_dir: str,
                                        hal_file: Optional[str] = None, 
                                        memmap_file: Optional[str] = None, 
                                        test_example_file: Optional[str] = None) -> Dict[str, Any]:
        """Generate a unified verification plan and tests for all features"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create feature descriptions for the plan
        feature_descriptions = []
        for feature in features:
            description = (
                f"Feature: {feature['name']}\n"
                f"Category: {feature['category']}\n"
                f"Priority: {feature['priority']}\n"
                f"Context: {feature['context']}\n"
                f"Source: {feature['source_file']}\n"
            )
            feature_descriptions.append(description)
        
        # Generate unified verification plan
        plan_file = output_dir / "unified_verification_plan.md"
        plan_content = generate_verification_plan(
            feature_description="\n\n".join(feature_descriptions),
            output_file=str(plan_file),
            address_map_file_path=memmap_file,
            hal_file_path=hal_file,
            test_example_file_path=test_example_file
        )
        
        # Generate tests from the plan
        test_dir = output_dir / "tests"
        test_dir.mkdir(exist_ok=True)
        test_files = generate_c_tests_from_plan(
            verification_plan_text=plan_content,
            output_dir=str(test_dir),
            address_map_file_path=memmap_file,
            hal_file_path=hal_file,
            test_example_file_path=test_example_file
        )
        
        # Generate Excel report
        excel_file = output_dir / "verification_plan.xlsx"
        convert_plan_to_excel(str(plan_file), str(excel_file))
        
        return {
            'plan_file': str(plan_file),
            'test_files': test_files,
            'excel_file': str(excel_file),
            'features_count': len(features)
        }
    
    def _generate_summary_report(self, results: Dict[str, Any], features: List[Dict[str, Any]], output_path: Path):
        """Generate a summary report of the generation process."""
        
        summary_content = f"""# Verification Generation Summary Report

Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview
- Total Features Processed: {results['total_features']}
- Successful Verification Plans: {results['successful_plans']}
- Successful C Test Generations: {results['successful_tests']}
- Successful Excel Reports: {results['successful_excel']}
- Failed Features: {len(results['failed_features'])}

## Features Processed

| Feature Name | Category | Priority | Status |
|--------------|----------|----------|--------|
"""
        
        for feature in features:
            status = "✅ Success" if feature["name"] not in [f["feature"] for f in results["failed_features"]] else "❌ Failed"
            summary_content += f"| {feature['name']} | {feature['category']} | {feature['priority']} | {status} |\n"
        
        if results["failed_features"]:
            summary_content += "\n## Failed Features\n\n"
            for failed in results["failed_features"]:
                summary_content += f"- **{failed['feature']}**: {failed['error']}\n"
        
        summary_content += "\n## Generated Files\n\n"
        summary_content += f"### Verification Plans ({len(results['generated_files']['plans'])})\n"
        for plan in results["generated_files"]["plans"]:
            summary_content += f"- {plan}\n"
        
        summary_content += f"\n### C Test Files ({len(results['generated_files']['tests'])})\n"
        for test in results["generated_files"]["tests"]:
            summary_content += f"- {test}\n"
        
        summary_content += f"\n### Excel Reports ({len(results['generated_files']['excel'])})\n"
        for excel in results["generated_files"]["excel"]:
            summary_content += f"- {excel}\n"
        
        # Save summary report
        summary_path = output_path / "generation_summary.md"
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary_content)
        
        print(f"\nSummary report saved to: {summary_path}")