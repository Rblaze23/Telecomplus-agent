"""Search directly for payment methods in chunks."""

from src.load_pdfs import load_and_split_pdfs

chunks = load_and_split_pdfs()

print("=" * 80)
print("SEARCHING FOR 'PAYMENT METHODS' IN CHUNKS")
print("=" * 80)

found = []

for i, chunk in enumerate(chunks):
    content = chunk.page_content.lower()
    if "payment method" in content:
        found.append((i, chunk))
        print(f"\n--- CHUNK {i} ---")
        print(f"Source: {chunk.metadata.get('source', 'Unknown')}")
        print(f"Page: {chunk.metadata.get('page', 'Unknown')}")
        print(chunk.page_content[:400])
        print("...")

if not found:
    print("\n❌ NO CHUNKS CONTAIN 'payment method'!")
    print("\nSearching for 'payment'...")
    
    for i, chunk in enumerate(chunks):
        content = chunk.page_content.lower()
        if "payment" in content and ("accept" in content or "method" in content):
            print(f"\n--- CHUNK {i} ---")
            print(chunk.page_content[:300])
            print("...")

print(f"\n\nTotal chunks with 'payment method': {len(found)}")