"""Detailed debugging of the search process."""

from src.load_pdfs import load_and_split_pdfs
from src.vector_db import build_vector_db
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

print("=" * 80)
print("DETAILED SEARCH DEBUG")
print("=" * 80)

# Load
chunks = load_and_split_pdfs()
print(f"\nTotal chunks: {len(chunks)}")

# Build
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
db = FAISS.from_documents(chunks, embeddings)

# Test question
question = "Quels modes de paiement acceptez-vous?"
print(f"\nQuestion: {question}")

# Try BOTH French and English searches
print("\n" + "=" * 80)
print("SEARCH 1: Original French")
print("=" * 80)
results_fr = db.similarity_search(question, k=10)
for i, doc in enumerate(results_fr[:3]):
    print(f"\n[{i+1}] {doc.page_content[:150]}...")

print("\n" + "=" * 80)
print("SEARCH 2: English Translation")
print("=" * 80)
english_query = "payment methods accepted"
results_en = db.similarity_search(english_query, k=10)
for i, doc in enumerate(results_en[:3]):
    print(f"\n[{i+1}] {doc.page_content[:150]}...")

print("\n" + "=" * 80)
print("SEARCH 3: Combined Query")
print("=" * 80)
combined_query = f"{question} payment methods accepted"
results_combined = db.similarity_search(combined_query, k=10)
for i, doc in enumerate(results_combined[:3]):
    print(f"\n[{i+1}] {doc.page_content[:150]}...")

# Find Chunk 21
print("\n" + "=" * 80)
print("WHERE IS CHUNK 21 (payment methods)?")
print("=" * 80)

for i, chunk in enumerate(chunks):
    if "payment method" in chunk.page_content.lower():
        print(f"\nChunk {i} contains payment methods")
        print(f"Content start: {chunk.page_content[:200]}")
        
        # Check its rank in each search
        for j, doc in enumerate(results_fr):
            if doc.page_content[:100] == chunk.page_content[:100]:
                print(f"  → Rank in French search: {j+1}")
                break
        
        for j, doc in enumerate(results_en):
            if doc.page_content[:100] == chunk.page_content[:100]:
                print(f"  → Rank in English search: {j+1}")
                break