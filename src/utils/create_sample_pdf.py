from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from pathlib import Path

def create_sample_pdf():
    """Create a sample PDF file with test content"""
    output_path = Path("example.pdf")
    
    # Create a new PDF with ReportLab
    c = canvas.Canvas(str(output_path), pagesize=letter)
    
    # Add some text to the PDF
    c.drawString(100, 750, "Sample PDF Document")
    c.drawString(100, 700, "This is a test PDF file created for text extraction.")
    c.drawString(100, 650, "It contains multiple lines of text")
    c.drawString(100, 600, "to test the PDF parser functionality.")
    
    # Add some text on a new page
    c.showPage()
    c.drawString(100, 750, "Page 2")
    c.drawString(100, 700, "This is the second page of our test document.")
    
    # Save the PDF
    c.save()
    
    print(f"Sample PDF created at: {output_path.absolute()}")

if __name__ == "__main__":
    create_sample_pdf() 