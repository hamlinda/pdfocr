import shutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def process_ocr(pdf_path: Path, subfolder_name: str, language: str = "eng") -> tuple[bool, str]:
    """
    Copies the unsearchable PDF to the configured subfolder, and then runs OCR on it.
    
    Returns (success, message).
    """
    try:
        # 1. Create subfolder inside the PDF's parent directory
        parent_dir = pdf_path.parent
        ocr_dir = parent_dir / subfolder_name
        ocr_dir.mkdir(parents=True, exist_ok=True)
        
        # 2. Define target paths in the subfolder
        # Original copy path: subfolder/filename.pdf
        original_copy_path = ocr_dir / pdf_path.name
        # OCR output path: subfolder/ocr_filename.pdf
        ocr_output_path = ocr_dir / f"ocr_{pdf_path.name}"
        
        # Copy original to the subfolder
        shutil.copy2(pdf_path, original_copy_path)
        logger.info(f"Copied original file to {original_copy_path}")
        
        # 3. Perform OCR using ocrmypdf
        try:
            import ocrmypdf
        except ImportError:
            msg = "Python package 'ocrmypdf' is not installed. Run 'pip install ocrmypdf'."
            logger.error(msg)
            return False, msg
            
        # Run ocrmypdf.ocr
        # We disable ocrmypdf's own progress bar so it doesn't mess with our CLI UI
        ocrmypdf.ocr(
            original_copy_path,
            ocr_output_path,
            language=[language],
            progress_bar=False,
            jobs=1
        )
        
        return True, f"Successfully processed OCR. Searchable PDF saved to {ocr_output_path}"
        
    except Exception as e:
        err_msg = f"OCR processing failed for {pdf_path.name}: {e}"
        logger.error(err_msg)
        return False, err_msg
