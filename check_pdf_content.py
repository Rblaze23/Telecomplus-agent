"""Check what's actually in the PDF files."""

from langchain_community.document_loaders import PyPDFLoader
import os

PDF_FOLDER = "data/pdfs"

# Check specific PDFs
pdfs_to_check = [
    "FAQ_Facturation_et_Paiements.pdf",  # Should have payment methods
    "FAQ_Support_Technique.pdf"  # Should have MMS config
]

for pdf_name in pdfs_to_check:
    pdf_path = os.path.join(PDF_FOLDER, pdf_name)
    
    print("=" * 80)
    print(f"PDF: {pdf_name}")
    print("=" * 80)
    
    if not os.path.exists(pdf_path):
        print(f"ERROR: File not found: {pdf_path}")
        continue
    
    # Load PDF
    loader = PyPDFLoader(pdf_path)
    pages = loader.load()
    
    print(f"Total pages: {len(pages)}\n")
    
    # Show content of each page
    for i, page in enumerate(pages):
        print(f"\n--- PAGE {i+1} ---")
        content = page.page_content[:500]  # First 500 chars
        print(content)
        print("...\n")
        
        # Search for keywords
        if "paiement" in page.page_content.lower():
            print("✓ Contains 'paiement'")
        if "carte" in page.page_content.lower():
            print("✓ Contains 'carte'")
        if "mms" in page.page_content.lower():
            print("✓ Contains 'mms'")
        if "configur" in page.page_content.lower():
            print("✓ Contains 'configur'")
    
    print("\n" + "=" * 80)