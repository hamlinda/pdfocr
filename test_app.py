import unittest
import shutil
import tempfile
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import reportlab to generate test PDFs
from reportlab.pdfgen import canvas

# Import our modules
from pdf_checker import is_pdf_searchable
from scanner import scan_directory_for_pdfs
from ocr_processor import process_ocr
from config import Config

class TestPDFOCRApp(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test files
        self.test_dir = Path(tempfile.mkdtemp())
        self.ocr_subfolder = "_newOCR"
        
        # Paths for test files
        self.searchable_path = self.test_dir / "searchable.pdf"
        self.non_searchable_path = self.test_dir / "non_searchable.pdf"
        self.corrupted_path = self.test_dir / "corrupted.pdf"
        
        # 1. Generate searchable PDF
        c = canvas.Canvas(str(self.searchable_path))
        c.drawString(100, 750, "This is a document with searchable text. Hello World!")
        c.showPage()
        c.save()
        
        # 2. Generate non-searchable PDF (rectangle only, no text)
        c2 = canvas.Canvas(str(self.non_searchable_path))
        c2.rect(100, 100, 300, 300, stroke=1, fill=1)
        c2.showPage()
        c2.save()
        
        # 3. Generate corrupted PDF
        with open(self.corrupted_path, "wb") as f:
            f.write(b"%PDF-1.4\n%corrupted\nThis is not a real PDF file!")

    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    def test_pdf_searchability_checker(self):
        # Searchable PDF should return True
        self.assertTrue(is_pdf_searchable(self.searchable_path))
        
        # Non-searchable PDF should return False
        self.assertFalse(is_pdf_searchable(self.non_searchable_path))
        
        # Corrupted PDF should raise an exception
        with self.assertRaises(Exception):
            is_pdf_searchable(self.corrupted_path)

    def test_directory_scanner(self):
        # Create nested directory structure
        nested_dir = self.test_dir / "nested"
        nested_dir.mkdir()
        nested_pdf = nested_dir / "nested_file.pdf"
        
        # Generate another searchable PDF inside nested
        c = canvas.Canvas(str(nested_pdf))
        c.drawString(100, 750, "Nested PDF text")
        c.showPage()
        c.save()
        
        # Create an OCR subfolder (which should be ignored by the scanner)
        ocr_dir = self.test_dir / self.ocr_subfolder
        ocr_dir.mkdir()
        ocr_pdf = ocr_dir / "should_be_ignored.pdf"
        shutil.copy2(self.searchable_path, ocr_pdf)
        
        # Scan the directory
        pdfs = scan_directory_for_pdfs(self.test_dir, self.ocr_subfolder)
        
        # Verify result filenames
        pdf_names = [p.name for p in pdfs]
        self.assertIn("searchable.pdf", pdf_names)
        self.assertIn("non_searchable.pdf", pdf_names)
        self.assertIn("corrupted.pdf", pdf_names)
        self.assertIn("nested_file.pdf", pdf_names)
        
        # Check that the file inside _newOCR was ignored
        self.assertNotIn("should_be_ignored.pdf", pdf_names)
        self.assertEqual(len(pdfs), 4)

    @patch('ocrmypdf.ocr')
    def test_ocr_processor_success(self, mock_ocr):
        # Mock ocrmypdf.ocr to succeed and create a dummy output file
        def side_effect(input_file, output_file, **kwargs):
            # Create the expected output file
            Path(output_file).touch()
            return True
            
        mock_ocr.side_effect = side_effect
        
        # Process the non-searchable PDF
        success, message = process_ocr(self.non_searchable_path, self.ocr_subfolder, "eng")
        
        self.assertTrue(success)
        self.assertIn("Successfully processed OCR", message)
        
        # Verify that the original copy exists in the subfolder
        copied_original = self.test_dir / self.ocr_subfolder / self.non_searchable_path.name
        self.assertTrue(copied_original.exists())
        
        # Verify that the OCR output file exists in the subfolder
        ocr_output = self.test_dir / self.ocr_subfolder / f"ocr_{self.non_searchable_path.name}"
        self.assertTrue(ocr_output.exists())

    @patch('ocrmypdf.ocr')
    def test_ocr_processor_failure(self, mock_ocr):
        # Mock ocrmypdf.ocr to throw an exception
        mock_ocr.side_effect = Exception("Tesseract engine not found")
        
        # Process the non-searchable PDF
        success, message = process_ocr(self.non_searchable_path, self.ocr_subfolder, "eng")
        
        self.assertFalse(success)
        self.assertIn("OCR processing failed", message)
        self.assertIn("Tesseract engine not found", message)
        
        # Original copy should still exist (it gets copied before OCR is run)
        copied_original = self.test_dir / self.ocr_subfolder / self.non_searchable_path.name
        self.assertTrue(copied_original.exists())
        
        # OCR output file should NOT exist because OCR failed
        ocr_output = self.test_dir / self.ocr_subfolder / f"ocr_{self.non_searchable_path.name}"
        self.assertFalse(ocr_output.exists())

if __name__ == "__main__":
    unittest.main()
