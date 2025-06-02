import os
import json
import csv
from pathlib import Path
import fitz  # PyMuPDF
import re
from datetime import datetime

class SpecFeatureExtractor:
    def __init__(self):
        self.section_headers = {
            'register': ['register', 'csr', 'control status'],
            'interrupt': ['interrupt', 'exception', 'trap'],
            'memory': ['memory', 'mmu', 'cache', 'address space']
        }

    def extract_features_from_files(self, file_paths, hal_path=None, memmap_path=None, test_example_path=None):
        # Extract features only from specification documents
        features = self._analyze_document_structure(file_paths)
        
        return self._deduplicate_features(features)

    def _analyze_document_structure(self, file_paths):
        """Analyze document structure to extract features"""
        features = []
        
        for file_path in file_paths:
            path = Path(file_path)
            if not path.exists():
                print(f"Warning: File {file_path} not found")
                continue
                
            try:
                if path.suffix.lower() == '.pdf':
                    features.extend(self._extract_from_pdf(path))
                else:
                    features.extend(self._extract_from_text(path))
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
        
        return features

    def _extract_from_pdf(self, pdf_path):
        """Extract features from PDF document"""
        features = []
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                
                # Extract features based on section headers and patterns
                features.extend(self._extract_features_from_text(text, str(pdf_path)))
            
            doc.close()
        except Exception as e:
            print(f"Error reading PDF {pdf_path}: {e}")
        
        return features

    def _extract_from_text(self, text_path):
        """Extract features from text document"""
        features = []
        try:
            content = self._load_file_content(text_path)
            features.extend(self._extract_features_from_text(content, str(text_path)))
        except Exception as e:
            print(f"Error reading text file {text_path}: {e}")
        
        return features

    def _extract_features_from_text(self, text, source_file):
        """Extract features from text content using pattern matching"""
        features = []
        
        # Split text into sections
        sections = re.split(r'\n\s*\n', text)
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
                
            # Determine category based on content
            category = self._determine_category(section)
            
            # Extract feature name from section
            feature_name = self._extract_feature_name(section)
            
            if feature_name and category:
                features.append({
                    'name': feature_name,
                    'category': category,
                    'source': 'specification',
                    'priority': self._determine_priority(section),
                    'context': section[:200] + '...' if len(section) > 200 else section,
                    'source_file': source_file
                })
        
        return features

    def _determine_category(self, text):
        """Determine feature category based on text content"""
        text_lower = text.lower()
        
        for category, keywords in self.section_headers.items():
            if any(keyword in text_lower for keyword in keywords):
                return category
        
        # Default categories based on common patterns
        if any(word in text_lower for word in ['function', 'api', 'interface']):
            return 'function'
        elif any(word in text_lower for word in ['test', 'verify', 'validate']):
            return 'test'
        else:
            return 'general'
    
    def _extract_feature_name(self, text):
        """Extract a meaningful feature name from text"""
        lines = text.strip().split('\n')
        
        # Try to find a header or title line
        for line in lines[:3]:  # Check first 3 lines
            line = line.strip()
            if line and not line.startswith('#'):
                # Clean up the line to make a good feature name
                name = re.sub(r'[^\w\s-]', '', line)
                name = re.sub(r'\s+', ' ', name).strip()
                if len(name) > 5 and len(name) < 100:
                    return name
        
        # Fallback: use first meaningful words
        words = re.findall(r'\w+', text)
        if len(words) >= 2:
            return ' '.join(words[:5])
        
        return None
    
    def _determine_priority(self, context):
        """Determine feature priority based on context"""
        priority_indicators = {
            'high': ['critical', 'essential', 'required', 'must', 'shall'],
            'medium': ['should', 'recommended', 'important'],
            'low': ['optional', 'may', 'nice to have']
        }
        
        context = context.lower()
        for priority, indicators in priority_indicators.items():
            if any(indicator in context for indicator in indicators):
                return priority
        return 'medium'  # default priority
    
    def save_features_to_file(self, features, output_file, format='json'):
        """Save extracted features to a file in specified format"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format.lower() == 'json':
            self._save_features_json(features, output_path)
        elif format.lower() == 'csv':
            self._save_features_csv(features, output_path)
        elif format.lower() == 'all':
            # Save in multiple formats
            json_path = output_path.with_suffix('.json')
            csv_path = output_path.with_suffix('.csv')
            summary_path = output_path.with_suffix('.txt')
            
            self._save_features_json(features, json_path)
            self._save_features_csv(features, csv_path)
            self._save_features_summary(features, summary_path)
            
            print(f"  - JSON format: {json_path}")
            print(f"  - CSV format: {csv_path}")
            print(f"  - Summary report: {summary_path}")
        else:
            self._save_features_json(features, output_path)  # Default to JSON
    
    def _save_features_json(self, features, output_path):
        """Save features as JSON with metadata"""
        data = {
            'metadata': {
                'extraction_timestamp': datetime.now().isoformat(),
                'total_features': len(features),
                'feature_categories': list(set(f['category'] for f in features)),
                'source_files': list(set(f.get('source_file', 'unknown') for f in features))
            },
            'features': features
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def _save_features_csv(self, features, output_path):
        """Save features as CSV for easy analysis"""
        if not features:
            return
            
        fieldnames = ['name', 'category', 'source', 'priority', 'context', 'source_file']
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for feature in features:
                row = {field: feature.get(field, '') for field in fieldnames}
                writer.writerow(row)
    
    def _save_features_summary(self, features, output_path):
        """Save a human-readable summary of extracted features"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("EXTRACTED FEATURES SUMMARY\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Extraction Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Features: {len(features)}\n\n")
            
            # Group by category
            categories = {}
            for feature in features:
                cat = feature['category']
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(feature)
            
            f.write("FEATURES BY CATEGORY:\n")
            f.write("-" * 30 + "\n\n")
            
            for category, cat_features in categories.items():
                f.write(f"{category.upper()} ({len(cat_features)} features):\n")
                for feature in cat_features:
                    f.write(f"  • {feature['name']} (Priority: {feature.get('priority', 'N/A')})\n")
                    if feature.get('context'):
                        f.write(f"    Context: {feature['context'][:100]}...\n")
                f.write("\n")
            
            # Source file summary
            source_files = {}
            for feature in features:
                src = feature.get('source_file', 'unknown')
                if src not in source_files:
                    source_files[src] = 0
                source_files[src] += 1
            
            f.write("FEATURES BY SOURCE FILE:\n")
            f.write("-" * 30 + "\n")
            for src_file, count in source_files.items():
                f.write(f"  {src_file}: {count} features\n")

    def _load_file_content(self, path: Path) -> str:
        """Load and return text content from a file"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error loading {path}: {str(e)}")
            return ""

    def _deduplicate_features(self, features):
        """Remove duplicate features while preserving order"""
        seen = set()
        unique_features = []
        for feat in features:
            identifier = f"{feat['name']}-{feat['category']}"
            if identifier not in seen:
                seen.add(identifier)
                unique_features.append(feat)
        return unique_features