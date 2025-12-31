"""Load and split PDF documents into chunks for RAG.

This module loads all PDFs from data/pdfs folder and splits them
into manageable chunks for vector search.
"""

import os
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_and_split_pdfs(chunk_size=1500, chunk_overlap=200):
    """Load all PDFs and split them into chunks.
    
    Args:
        chunk_size: Size of each text chunk in characters (increased from 800)
        chunk_overlap: Overlap between consecutive chunks (increased from 80)
        
    Returns:
        List of LangChain Document objects (chunks with metadata)
    """
    # Get the PDFs folder path
    current_dir = Path(__file__).parent
    pdf_folder = current_dir.parent / "data" / "pdfs"
    
    if not pdf_folder.exists():
        raise FileNotFoundError(f"PDF folder not found: {pdf_folder}")
    
    # Initialize text splitter with LARGER chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    all_chunks = []
    
    # Load each PDF file
    pdf_files = list(pdf_folder.glob("*.pdf"))
    
    if not pdf_files:
        print(f"[WARNING] No PDF files found in {pdf_folder}")
        return []
    
    print(f"[PDF] Found {len(pdf_files)} PDF files")
    
    for pdf_file in pdf_files:
        try:
            # Load PDF
            loader = PyPDFLoader(str(pdf_file))
            pdf_docs = loader.load()
            
            # Split into chunks
            chunks = splitter.split_documents(pdf_docs)
            all_chunks.extend(chunks)
            
            print(f"[PDF] Loaded {pdf_file.name}: {len(pdf_docs)} pages → {len(chunks)} chunks")
            
        except Exception as e:
            print(f"[ERROR] Failed to load {pdf_file.name}: {e}")
    
    print(f"[PDF] Total chunks created: {len(all_chunks)}")
    
    return all_chunks


# Test if run directly
if __name__ == "__main__":
    print("Testing PDF loading...")
    chunks = load_and_split_pdfs()
    
    if chunks:
        print(f"\nTotal chunks: {len(chunks)}")
        print(f"\nFirst chunk example:")
        print(f"Content: {chunks[0].page_content[:200]}...")
        print(f"Metadata: {chunks[0].metadata}")
    else:
        print("No chunks loaded!")