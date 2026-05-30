import os
from pathlib import Path
from reportlab.pdfgen import canvas

def main():
    test_dir = Path("test_docs")
    test_dir.mkdir(exist_ok=True)
    
    # 1. Create searchable PDF
    searchable_path = test_dir / "searchable_sample.pdf"
    c1 = canvas.Canvas(str(searchable_path))
    c1.setFont("Helvetica", 12)
    c1.drawString(50, 700, "This is a pre-existing searchable document.")
    c1.drawString(50, 680, "It contains machine-readable text lines.")
    c1.drawString(50, 660, "The application should detect this and skip OCR processing.")
    c1.showPage()
    c1.save()
    print(f"Generated searchable PDF at: {searchable_path}")
    
    # 2. Create scanned PDF (no text)
    scanned_path = test_dir / "scanned_sample.pdf"
    c2 = canvas.Canvas(str(scanned_path))
    c2.setFillColorRGB(0.9, 0.9, 0.9)
    c2.rect(50, 100, 500, 600, stroke=1, fill=1) # Draw a big box simulating a scanned page
    c2.showPage()
    c2.save()
    print(f"Generated scanned PDF (no text layer) at: {scanned_path}")
    
    # 3. Create corrupted PDF
    broken_path = test_dir / "broken_sample.pdf"
    with open(broken_path, "wb") as f:
        f.write(b"%PDF-1.4\n%corrupted\nThis is not a real PDF file!")
    print(f"Generated broken PDF at: {broken_path}")

if __name__ == "__main__":
    main()
