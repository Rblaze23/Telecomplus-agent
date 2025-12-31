"""Test the complete flow to see what LLM receives."""

from src.load_pdfs import load_and_split_pdfs
from src.vector_db import build_vector_db, query_pdf

chunks = load_and_split_pdfs()
db = build_vector_db(chunks, "test_faiss")

question = "Quels modes de paiement acceptez-vous?"

print("=" * 80)
print("TESTING COMPLETE FLOW")
print("=" * 80)
print(f"\nQuestion: {question}\n")

# Get results
results = query_pdf(question, db, k=10)

print(f"Got {len(results)} results\n")

for i, result in enumerate(results[:3], 1):
    print(f"\n{'=' * 80}")
    print(f"RESULT {i}")
    print('=' * 80)
    
    # Show what will be sent to LLM (after cleaning)
    clean = result.split("(Source:")[0].strip()
    
    # Show first 500 chars
    print(clean[:500])
    print("...")
    
    # Check if Q9 is there
    if "Q9" in clean:
        print("\n✓ Q9 IS IN THIS RESULT!")
    if "payment method" in clean.lower():
        print("✓ 'payment method' IS IN THIS RESULT!")

print("\n" + "=" * 80)
print("If Q9 and 'payment method' are in Result 1, the problem is the LLM prompt.")
print("If not, the search/extraction is still broken.")
print("=" * 80)