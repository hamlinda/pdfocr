import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Default folders to ignore to speed up scanning and prevent traversing package directories
DEFAULT_IGNORE_DIRS = {
    "venv", "node_modules", ".git", "__pycache__", ".idea", ".vscode", 
    ".cache", ".pytest_cache", "env", ".env", "dist", "build"
}

def scan_directory_for_pdfs(
    directory: Path, 
    ocr_subfolder: str, 
    on_update=None
) -> list[Path]:
    """
    Recursively scans the directory for PDF files.
    Prunes the configured OCR subfolder and common dependency folders from traversal.
    
    on_update: Optional callback function with signature:
               on_update(dirs_scanned: int, files_scanned: int, pdfs_found: int, current_dir: str)
    
    Returns a sorted list of Path objects for all found PDF files.
    """
    pdf_files = []
    if not directory.exists() or not directory.is_dir():
        logger.warning(f"Scan target is not an existing directory: {directory}")
        return pdf_files

    resolved_dir = directory.resolve()
    
    dir_count = 0
    file_count = 0
    pdf_count = 0
    
    for root, dirs, files in os.walk(resolved_dir):
        # Prune the OCR subfolder and other common directories to speed up scanning
        # Modifying dirs in-place prevents os.walk from entering them
        to_prune = [d for d in dirs if d == ocr_subfolder or d in DEFAULT_IGNORE_DIRS]
        for d in to_prune:
            dirs.remove(d)
            
        dir_count += 1
        file_count += len(files)
        
        # Identify PDFs
        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_files.append(Path(root) / file)
                pdf_count += 1
                
        # Report progress periodically (every 10 directories or the first directory)
        if on_update and (dir_count % 10 == 0 or dir_count == 1):
            # Show a shortened version of the current dir name for console layout
            short_path = root
            if len(short_path) > 40:
                short_path = "..." + short_path[-37:]
            on_update(dir_count, file_count, pdf_count, short_path)
            
    # Final update at the end
    if on_update:
        on_update(dir_count, file_count, pdf_count, "Finished scanning")
        
    return sorted(pdf_files)
