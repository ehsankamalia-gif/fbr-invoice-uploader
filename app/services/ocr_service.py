import re
import os
import sys
from PIL import Image

try:
    import cv2
    import numpy as np
    import pytesseract
    OCR_AVAILABLE = True
    IMPORT_ERROR = None
except ImportError as e:
    OCR_AVAILABLE = False
    IMPORT_ERROR = str(e)
    # Define dummy modules or handle in class
    cv2 = None
    np = None
    pytesseract = None

class OCRService:
    def __init__(self):
        self.tesseract_cmd = None
        if OCR_AVAILABLE:
            self.tesseract_cmd = self._find_tesseract()
            if self.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

    def is_available(self):
        """Returns True if OCR dependencies are installed and Tesseract is found."""
        return OCR_AVAILABLE and self.tesseract_cmd is not None

    def get_error(self):
        """Returns the initialization error message."""
        if not OCR_AVAILABLE:
            return f"Missing dependencies: {IMPORT_ERROR}"
        if not self.tesseract_cmd:
            return "Tesseract-OCR not found on system."
        return None

    def _find_tesseract(self):
        """Attempts to locate the Tesseract executable."""
        # 1. Check PATH
        import shutil
        if shutil.which("tesseract"):
            return "tesseract"
            
        # 2. Check common Windows paths
        common_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"),
            os.path.expandvars(r"%ProgramFiles%\Tesseract-OCR\tesseract.exe")
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
                
        return None

    def preprocess_image(self, image_path):
        """Loads and preprocesses an image for OCR."""
        if not OCR_AVAILABLE:
            raise RuntimeError(f"OCR dependencies missing: {IMPORT_ERROR}")
            
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply simple thresholding to clear up noise
        # Otsu's thresholding
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        
        return gray

    def extract_text(self, image_path):
        """Extracts raw text from an image."""
        if not OCR_AVAILABLE:
            raise RuntimeError(f"OCR dependencies missing: {IMPORT_ERROR}")
            
        if not self.tesseract_cmd:
            raise RuntimeError("Tesseract-OCR is not found. Please install it from https://github.com/UB-Mannheim/tesseract/wiki")

        processed_img = self.preprocess_image(image_path)
        
        # Configure tesseract for better accuracy
        # --psm 6: Assume a single uniform block of text.
        custom_config = r'--oem 3 --psm 6' 
        text = pytesseract.image_to_string(processed_img, config=custom_config, lang='eng')
        return text

    def parse_cnic_data(self, front_img_path, back_img_path=None):
        """
        Extracts CNIC details from front (and optionally back) images.
        Returns a dict with found fields.
        """
        result = {
            "cnic": None,
            "name": None,
            "father_name": None,
            "address": None
        }

        # --- Process Front ---
        try:
            front_text = self.extract_text(front_img_path)
            # Normalize text
            lines = [line.strip() for line in front_text.split('\n') if line.strip()]
            
            # 1. Find CNIC (XXXXX-XXXXXXX-X)
            # Regex allows for some OCR errors (e.g. O instead of 0, space instead of dash)
            # But strict format is 5-7-1
            cnic_pattern = re.compile(r'\b\d{5}[- ]?\d{7}[- ]?\d{1}\b')
            
            for line in lines:
                match = cnic_pattern.search(line)
                if match:
                    # Standardize format to dashes
                    raw_cnic = match.group(0).replace(' ', '-')
                    if len(raw_cnic) == 13: # if dashes missing
                        raw_cnic = f"{raw_cnic[:5]}-{raw_cnic[5:12]}-{raw_cnic[12]}"
                    result["cnic"] = raw_cnic
                    break

            # 2. Find Name & Father Name
            # Heuristic: Look for "Name" keyword, next line is the name.
            # Look for "Father Name" keyword, next line is father name.
            # Also consider that ID cards have Urdu, but we are looking for English.
            
            for i, line in enumerate(lines):
                line_lower = line.lower()
                
                # Name
                if "name" in line_lower and "father" not in line_lower and "husband" not in line_lower:
                    # The name might be on the same line "Name: John Doe" or next line
                    clean_line = re.sub(r'name[:\.]?', '', line, flags=re.IGNORECASE).strip()
                    if len(clean_line) > 3:
                        result["name"] = clean_line
                    elif i + 1 < len(lines):
                        result["name"] = lines[i+1]

                # Father/Husband Name
                if "father" in line_lower or "husband" in line_lower:
                    clean_line = re.sub(r'(father|husband)[ \']?name[:\.]?', '', line, flags=re.IGNORECASE).strip()
                    if len(clean_line) > 3:
                        result["father_name"] = clean_line
                    elif i + 1 < len(lines):
                        result["father_name"] = lines[i+1]
                        
        except Exception as e:
            print(f"OCR Error (Front): {e}")

        # --- Process Back (mainly for address) ---
        if back_img_path:
            try:
                back_text = self.extract_text(back_img_path)
                # Address is usually the longest block of text or follows "Address"
                # Note: Pakistani addresses are often in Urdu on old cards, but Smart Cards have English.
                # We will try to find "Present Address" or "Permanent Address"
                
                # Simple heuristic: Take the longest line that contains "House" or "Street" or "Road" or "District"
                lines = [l.strip() for l in back_text.split('\n') if l.strip()]
                address_candidates = []
                
                for line in lines:
                    if any(x in line.lower() for x in ["house", "street", "road", "block", "sector", "district", "flat", "town"]):
                        address_candidates.append(line)
                
                if address_candidates:
                    # Join them if they look like parts of one address
                    result["address"] = ", ".join(address_candidates)
                
            except Exception as e:
                print(f"OCR Error (Back): {e}")

        return result

ocr_service = OCRService()
