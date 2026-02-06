
import json
import sys
from pathlib import Path

def check_quality(file_path):
    """
    Checks the captured forms for empty critical fields.
    Fails if > 2% of records are missing Engine, Color, or Model.
    """
    p = Path(file_path)
    if not p.exists():
        print(f"File {file_path} not found.")
        return 0 # No data yet, technically not a failure of quality
    
    with open(p, 'r') as f:
        data = json.load(f)
        
    pages = data.get("pages", {})
    total = len(pages)
    if total == 0:
        print("No pages captured.")
        return 0
        
    missing_count = 0
    for url, info in pages.items():
        fields = info.get("fields", {})
        # Check if fields are present and not empty
        has_engine = fields.get("#txt_engine_no", {}).get("value")
        has_color = fields.get("#txt_color", {}).get("value")
        has_model = fields.get("#txt_model", {}).get("value")
        
        if not (has_engine and has_color and has_model):
            missing_count += 1
            
    failure_rate = (missing_count / total) * 100
    print(f"Total Records: {total}")
    print(f"Missing Critical Fields: {missing_count}")
    print(f"Failure Rate: {failure_rate:.2f}%")
    
    if failure_rate > 2.0:
        print("FAILURE: Critical field missing rate > 2%")
        sys.exit(1)
    else:
        print("SUCCESS: Quality standards met.")
        sys.exit(0)

if __name__ == "__main__":
    check_quality("captured_forms.json")
