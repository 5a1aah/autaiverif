# scripts/plan_to_excel.py
import re
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional

def parse_plan_for_excel(markdown_text: str) -> List[Dict[str, Any]]:
    """
    Parses the Markdown verification plan to extract relevant fields for Excel.
    The Excel "ID" will be a sequential number.
    The Excel "Name" will be the derived C test filename.
    The Excel "Description" will be a concatenation of all test case details.
    """
    excel_rows_data: List[Dict[str, Any]] = []
    # Split the entire plan by "---" which seems to be the main separator
    raw_test_blocks = re.split(r'\n---\s*\n', markdown_text)
    
    print(f"DEBUG (plan_to_excel): Number of raw blocks found: {len(raw_test_blocks)}")
    
    sequential_id_counter = 1 # For the new Excel "ID" column

    for block_index, block_content in enumerate(raw_test_blocks):
        block_content = block_content.strip()
        if not block_content or block_content.lower().startswith("{{output_format}}"):
            continue

        print(f"\nDEBUG (plan_to_excel): Processing Block {block_index + 1}...")

        parsed_fields: Dict[str, str] = {} 
        original_test_id = None 
        original_test_title_from_header = "" # To store the full title like "MTIP_001 Timer Basic"

        lines = block_content.splitlines()
        if not lines:
            continue

        # First line: "### Test Case: MTIP_001 [Optional Full Name]"
        title_line = lines[0].strip()
        title_match = re.match(r"### Test Case:\s*([^\s]+)(?:\s*(.*))?", title_line)
        
        if title_match:
            original_test_id = title_match.group(1).strip().replace("-", "_")
            if title_match.group(2) and title_match.group(2).strip():
                 original_test_title_from_header = f"{original_test_id} {title_match.group(2).strip()}"
            else:
                 original_test_title_from_header = original_test_id
            parsed_fields["original_test_title_from_header"] = original_test_title_from_header # Store for later use if needed for Name
            print(f"DEBUG (plan_to_excel): Parsed Original Test ID: {original_test_id}, Full Title: {original_test_title_from_header}")
        else:
            print(f"DEBUG (plan_to_excel): Could not parse Original Test ID from title line: '{title_line}'. Skipping block.")
            continue 

        current_field_key: Optional[str] = None
        current_field_value_lines: List[str] = []

        for line_content in lines[1:]: 
            line_strip = line_content.strip()
            field_match = re.match(r"-\s*\*\*(.+?):\*\*\s*(.*)", line_strip) 
            
            if field_match: 
                if current_field_key and current_field_value_lines:
                    parsed_fields[current_field_key] = "\n".join(current_field_value_lines).strip()
                
                current_field_key = field_match.group(1).strip().lower().replace(" ", "_").replace(":", "") # ensure no colon in key
                current_field_value_lines = [field_match.group(2).strip()]
            elif current_field_key and line_strip.startswith("- "): 
                current_field_value_lines.append(line_strip.lstrip("- ").strip())
            elif current_field_key and line_strip: 
                current_field_value_lines.append(line_strip)
            elif current_field_key and not line_strip: # Preserve empty lines within a field's value
                current_field_value_lines.append("")


        if current_field_key and current_field_value_lines: 
            parsed_fields[current_field_key] = "\n".join(current_field_value_lines).strip()

        # Construct the output dictionary for Excel
        if original_test_id:
            excel_row = {}
            excel_row["ID"] = sequential_id_counter
            
            c_test_name_base = "".join(c if c.isalnum() or c == '_' else '_' for c in original_test_id)
            if not c_test_name_base or c_test_name_base[0].isdigit():
                c_test_name_base = "test_" + c_test_name_base
            excel_row["Name"] = f"test_{c_test_name_base.lower()}.c"
            
            # --- Consolidate all details into the "Description" field ---
            description_parts = []
            # Define the order and display names for the fields in the Description
            fields_to_include_in_description = [
                ("Test Category", "test_category"),
                ("Feature Being Tested", "feature_being_tested"),
                ("Test Description", "test_description"),
                ("Stimulus", "stimulus"),
                ("Expected Outcome", "expected_outcome"), # LLM outputted "Expected Outcome"
                ("Coverage Points", "coverage_points")
            ]

            # Add the original full title/ID line at the beginning of the description
            description_parts.append(f"Test Case: {original_test_title_from_header}")


            for display_name, field_key in fields_to_include_in_description:
                if field_key in parsed_fields and parsed_fields[field_key]:
                    # For multi-line fields (like stimulus, expected_outcome), format them nicely
                    field_value = parsed_fields[field_key]
                    if '\n' in field_value:
                        # Indent sub-lines for readability
                        sub_lines = field_value.split('\n')
                        formatted_value = sub_lines[0] # First line as is
                        if len(sub_lines) > 1:
                             # Prepend each subsequent line with "- " if it's not already a bullet
                            formatted_value += "\n" + "\n".join([f"  - {s.lstrip('- ')}" if not s.strip().startswith('-') else f"  {s}" for s in sub_lines[1:] if s.strip()])
                        description_parts.append(f"\n- **{display_name}:** {formatted_value.strip()}")
                    else:
                        description_parts.append(f"\n- **{display_name}:** {field_value.strip()}")
            
            excel_row["Description"] = "".join(description_parts).strip()
            # --- End of Description consolidation ---
            
            excel_rows_data.append(excel_row)
            print(f"DEBUG (plan_to_excel): Added to Excel data: Seq_ID='{excel_row['ID']}', C_Test_Name='{excel_row['Name']}'")
            sequential_id_counter += 1
        else:
            print(f"DEBUG (plan_to_excel): Skipped block due to missing original_test_id. Title line: '{title_line}'")
            
    print(f"Final count of test cases extracted for Excel: {len(excel_rows_data)}")
    return excel_rows_data


def convert_plan_to_excel(markdown_file_path: str, excel_file_path: str):
    """
    Reads a Markdown verification plan, parses it, and saves selected fields to an Excel file.
    """
    md_path = Path(markdown_file_path)
    excel_path = Path(excel_file_path)

    if not md_path.is_file():
        print(f"Error: Markdown plan file not found at {md_path}")
        return

    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
    except Exception as e:
        print(f"Error reading Markdown file {md_path}: {e}")
        return

    parsed_data = parse_plan_for_excel(markdown_content)

    if not parsed_data:
        print("No data parsed from the verification plan. Excel file will not be created.")
        return

    try:
        df = pd.DataFrame(parsed_data)
        cols = []
        if "ID" in df.columns: cols.append("ID")
        if "Name" in df.columns: cols.append("Name")
        if "Description" in df.columns: cols.append("Description")
        
        df = df[cols] 
        
        excel_path.parent.mkdir(parents=True, exist_ok=True) 
        df.to_excel(excel_path, index=False, engine='openpyxl')
        print(f"Successfully converted verification plan to Excel: {excel_path}")
    except Exception as e:
        print(f"Error writing to Excel file {excel_path}: {e}")

if __name__ == '__main__':
    print("Testing plan_to_excel.py directly...")
    dummy_plan_content = """
{{output_format}}

---

### Test Case: MTIP_001 Timer Basic
- **Test Category:** Interrupts
- **Feature Being Tested:** mtime and mtimecmp Basic Interrupt
- **Test Description:** Verify basic timer interrupt generation.
  - Step 1: Configure mtimecmp.
  - Step 2: Enable timer interrupt in MIE.
- **Stimulus:**
  - Set mtimecmp to current_mtime + 1000.
  - Another stimulus line.
- **Expected Outcome:**
  - MTIP bit in MIP CSR becomes set.
  - Trap to mtvec occurs.
- **Coverage Points:**
  - Basic MTIP generation.

---

### Test Case: MTIP_002 Another Test
- **Test Category:** General
- **Feature Being Tested:** Some other feature
- **Test Description:** A different description.
- **Stimulus:**
  - Single line stimulus.
- **Expected Outcome:**
  - Single line outcome.
- **Coverage Points:**
  - Point A
  - Point B

---
    """
    test_plan_dir = Path(__file__).resolve().parent.parent / "generated_outputs" / "verification_plans"
    test_plan_dir.mkdir(parents=True, exist_ok=True)
    dummy_md_file = test_plan_dir / "dummy_plan_for_excel_test_full_desc.md"
    with open(dummy_md_file, "w", encoding="utf-8") as f:
        f.write(dummy_plan_content)

    output_excel_dir = Path(__file__).resolve().parent.parent / "generated_outputs" / "excel_reports"
    dummy_excel_file = output_excel_dir / "dummy_plan_report_full_desc.xlsx"

    convert_plan_to_excel(str(dummy_md_file), str(dummy_excel_file))