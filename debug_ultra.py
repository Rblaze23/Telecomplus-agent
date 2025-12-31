"""Ultra detailed debugging - print EVERYTHING."""

from src.load_pdfs import load_and_split_pdfs
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

chunks = load_and_split_pdfs()
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
db = FAISS.from_documents(chunks, embeddings)

question = "Quels modes de paiement acceptez-vous?"
english = "payment methods accepted"

print("=" * 80)
print("ULTRA DEBUG - STEP BY STEP")
print("=" * 80)

# Step 1: French search
print("\n1. FRENCH SEARCH")
docs_fr = db.similarity_search(question, k=20)
print(f"   Got {len(docs_fr)} results")
for i in range(min(5, len(docs_fr))):
    print(f"   [{i+1}] {docs_fr[i].page_content[:80]}...")

# Step 2: English search
print("\n2. ENGLISH SEARCH")
docs_en = db.similarity_search(english, k=20)
print(f"   Got {len(docs_en)} results")
for i in range(min(5, len(docs_en))):
    print(f"   [{i+1}] {docs_en[i].page_content[:80]}...")

# Step 3: Check if Chunk 21 is in English results
print("\n3. CHECKING FOR CHUNK 21")
target = "Q9. What payment methods"
for i, doc in enumerate(docs_en):
    if target in doc.page_content:
        print(f"   ✓ FOUND at position {i+1} in English search!")
        print(f"   Content: {doc.page_content[:200]}")
        break
else:
    print(f"   ✗ NOT FOUND in top 20 English results")

# Step 4: Combine
print("\n4. COMBINING RESULTS")
all_docs = []
seen = set()

for doc in docs_fr:
    sig = doc.page_content[:100]
    if sig not in seen:
        all_docs.append(doc)
        seen.add(sig)
        print(f"   Added from FR: {doc.page_content[:60]}...")

for doc in docs_en:
    sig = doc.page_content[:100]
    if sig not in seen:
        all_docs.append(doc)
        seen.add(sig)
        print(f"   Added from EN: {doc.page_content[:60]}...")

print(f"\n   Total combined: {len(all_docs)}")

# Step 5: Check final top 10
print("\n5. FINAL TOP 10")
for i in range(min(10, len(all_docs))):
    print(f"   [{i+1}] {all_docs[i].page_content[:80]}...")
    if target in all_docs[i].page_content:
        print(f"        ^ THIS IS CHUNK 21!")