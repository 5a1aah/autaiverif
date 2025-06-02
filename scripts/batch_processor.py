import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from .generate_verif_plan import generate_verification_plan
from .generate_c_tests import generate_c_tests_from_plan
from .plan_to_excel import convert_plan_to_excel

class BatchProcessor:
    """Handles batch processing of verification plans and C tests for multiple design features."""
    
    def __init__(self):
        self.results = {
            "plans": [],
            "tests": [],
            "excel_reports": [],
            "errors": []
        }
    
    def process_features_from_file(self, features_file: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """Process features from a JSON or text file."""
        features = []
        file_path = Path(features_file)
        
        if file_path.suffix.lower() == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                features = json.load(f)
        else:
            # Assume text file with one feature per line
            with open(file_path, 'r', encoding='utf-8') as f:
                features = [line.strip() for line in f if line.strip()]
        
        return self.process_features(features, output_dir)
    
    def process_features(self, features: List[str], output_dir: Optional[str] = None) -> Dict[str, Any]:
        """Process a list of feature descriptions."""
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        for feature in features:
            try:
                # Generate verification plan
                feature_desc = feature if isinstance(feature, str) else feature.get('description', '')
                plan_file = generate_verification_plan(
                    feature_description=feature_desc,
                    output_dir=output_dir
                )
                self.results["plans"].append(plan_file)
                
                # Generate C tests from the plan
                with open(plan_file, 'r', encoding='utf-8') as f:
                    plan_content = f.read()
                
                test_files = generate_c_tests_from_plan(
                    verification_plan_text=plan_content,
                    output_dir=output_dir
                )
                self.results["tests"].extend(test_files)
                
                # Generate Excel report
                if output_dir:
                    excel_file = os.path.join(output_dir, f"{Path(plan_file).stem}_report.xlsx")
                else:
                    excel_file = f"{Path(plan_file).stem}_report.xlsx"
                
                convert_plan_to_excel(plan_file, excel_file)
                self.results["excel_reports"].append(excel_file)
                
            except Exception as e:
                error_info = {
                    "feature": feature,
                    "error": str(e)
                }
                self.results["errors"].append(error_info)
                print(f"Error processing feature '{feature}': {e}")
        
        return self.results
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the batch processing results."""
        return {
            "total_plans": len(self.results["plans"]),
            "total_tests": len(self.results["tests"]),
            "total_excel_reports": len(self.results["excel_reports"]),
            "total_errors": len(self.results["errors"]),
            "plans": self.results["plans"],
            "tests": self.results["tests"],
            "excel_reports": self.results["excel_reports"],
            "errors": self.results["errors"]
        }