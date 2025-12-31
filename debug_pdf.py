"""Debug script to see what the PDF search is returning."""

from src.load_pdfs import load_and_split_pdfs
from src.vector_db import build_vector_db, query_pdf

print("=" * 80)
print("DEBUG: PDF SEARCH")
print("=" * 80)

# Load and build
print("\nLoading PDFs...")
chunks = load_and_split_pdfs()
print(f"Total chunks: {len(chunks)}")

print("\nBuilding vector DB...")
db = build_vector_db(chunks, persist_path="debug_faiss")

# Test questions
test_questions = [
    "Quels modes de paiement acceptez-vous?",
    "Comment configurer mes MMS?",
    "Y a-t-il des frais de résiliation?"
]

for question in test_questions:
    print("\n" + "=" * 80)
    print(f"QUESTION: {question}")
    print("=" * 80)
    
    # Get raw results
    results = query_pdf(question, db, k=10)
    
    print(f"\nFound {len(results)} results:")
    
    for i, result in enumerate(results, 1):
        print(f"\n--- Result {i} ---")
        # Show first 200 chars
        clean = result.split("(Source:")[0].strip()
        print(clean[:200])
        print("...")
        
    print("\n" + "-" * 80)

print("\n" + "=" * 80)
print("ANALYSIS")
print("=" * 80)
print("\nIf results look wrong:")
print("1. Chunks might not contain the right info")
print("2. Search isn't finding relevant chunks")
print("3. Answer extraction is broken")
print("\nCheck the first result for each question above.")
print("Does it contain the answer to the question?")