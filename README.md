# PDF OCR Scanner and Processor

A Python application that recursively scans configured directories for PDF files, checks if they contain a machine-readable text layer, and automatically performs OCR on scanned (non-searchable) PDFs.

## How It Works

1. **Scan**: Reads `SCAN_DIRECTORIES` from the `.env` file and scans them recursively for PDF files (excluding any `_newOCR` folders to prevent loops).
2. **Readability Check**: Opens each PDF using `pypdf` and checks if it contains a searchable text layer.
3. **Skip or OCR**:
   - If the PDF is already searchable, it is marked as **ALREADY SEARCHABLE** and skipped.
   - If it lacks a text layer, it creates a subfolder (default `_newOCR`) inside the PDF's directory, copies the original PDF there, and generates a new searchable PDF (`ocr_<filename>`) using `ocrmypdf`.
4. **Logging**: All successes, failures, and skipped files are logged to a configured log file (default `pdf_ocr.log`).
5. **Terminal Progress**: Displays terminal-based progress bars using the `rich` library showing the indexing and processing percentage of each folder.

---

## Prerequisites (System Dependencies)

To perform OCR, the Python package `ocrmypdf` relies on external system binaries. Please install them before running the OCR process:

### Debian / Ubuntu
```bash
sudo apt update
sudo apt install -y tesseract-ocr ghostscript
```

### Fedora / Red Hat / CentOS
```bash
sudo dnf install -y tesseract ghostscript
```

### macOS (using Homebrew)
```bash
brew install tesseract ghostscript
```

---

## Installation & Setup

1. **Clone or Navigate to Project Directory**
   Ensure you are in the application root directory `/home/dlh/dlhdev/pdfocr`.

2. **Create a Virtual Environment**
   ```bash
   python3 -m venv venv
   ```

3. **Activate the Virtual Environment**
   - On Linux/macOS:
     ```bash
     source venv/bin/activate
     ```
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```

4. **Install Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

---

## Configuration

Configure the application by modifying the `.env` file in the root directory:

```env
# List of directories to scan, comma-separated
SCAN_DIRECTORIES=/mnt/backup/LinkedInLearning

# Subfolder where non-searchable files will be copied and processed (default: _newOCR)
OCR_SUBFOLDER=_newOCR

# Path to the log file (default: pdf_ocr.log)
LOG_FILE=pdf_ocr.log

# Language for OCR (default: eng)
OCR_LANG=eng

# Force OCR even if text is already present in the PDF (True or False)
FORCE_OCR=False
```

---

## Running the Application

Make sure your virtual environment is active, then run:

```bash
python app.py
```

---

## Running Tests

A comprehensive test suite is provided. To run the tests, execute:

```bash
python -m unittest test_app.py
```

### Test PDF Generator Helper
To generate some sample PDFs for testing, run:
```bash
python generate_test_environment.py
```
This generates a folder named `test_docs` containing:
- `searchable_sample.pdf` (contains text, will be skipped by the app)
- `scanned_sample.pdf` (contains only an image-like rectangle, will be OCR'd)
- `broken_sample.pdf` (a corrupted file, will log check failure)
