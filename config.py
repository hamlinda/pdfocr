import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

class Config:
    def __init__(self):
        # Scan directories: comma-separated list. Convert to path objects and strip whitespace.
        scan_dirs_str = os.getenv("SCAN_DIRECTORIES", "")
        if scan_dirs_str:
            self.scan_directories = [
                Path(d.strip()).resolve() for d in scan_dirs_str.split(",") if d.strip()
            ]
        else:
            self.scan_directories = []

        # OCR subfolder name (default: _newOCR)
        self.ocr_subfolder = os.getenv("OCR_SUBFOLDER", "_newOCR").strip()
        
        # Log file path (default: pdf_ocr.log)
        self.log_file = Path(os.getenv("LOG_FILE", "pdf_ocr.log").strip()).resolve()
        
        # OCR Language (default: eng)
        self.ocr_lang = os.getenv("OCR_LANG", "eng").strip()
        
        # Force OCR (default: False)
        self.force_ocr = os.getenv("FORCE_OCR", "False").strip().lower() in ("true", "1", "yes")

    def validate(self):
        """
        Validates the current configuration.
        Returns a list of error strings, or an empty list if valid.
        """
        errors = []
        if not self.scan_directories:
            errors.append("SCAN_DIRECTORIES is empty or not set in the environment variables.")
        else:
            for d in self.scan_directories:
                if not d.exists():
                    errors.append(f"Scan directory does not exist: {d}")
                elif not d.is_dir():
                    errors.append(f"Scan path is not a directory: {d}")
        
        # Check subfolder name validity
        if not self.ocr_subfolder:
            errors.append("OCR_SUBFOLDER cannot be empty.")
        elif "/" in self.ocr_subfolder or "\\" in self.ocr_subfolder:
            errors.append("OCR_SUBFOLDER should be a simple folder name, not a path.")

        return errors

    def __repr__(self):
        return (
            f"Config(scan_directories={self.scan_directories}, "
            f"ocr_subfolder='{self.ocr_subfolder}', "
            f"log_file={self.log_file}, "
            f"ocr_lang='{self.ocr_lang}', "
            f"force_ocr={self.force_ocr})"
        )
