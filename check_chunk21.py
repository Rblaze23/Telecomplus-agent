"""See the full content of Chunk 21."""

from src.load_pdfs import load_and_split_pdfs

chunks = load_and_split_pdfs()

print("=" * 80)
print("CHUNK 21 - FULL CONTENT")
print("=" * 80)

if len(chunks) > 21:
    chunk21 = chunks[21]
    print(chunk21.page_content)
else:
    print(f"Only {len(chunks)} chunks available")
    
print("\n" + "=" * 80)
print("SEARCHING FOR Q9")
print("=" * 80)

for i, chunk in enumerate(chunks):
    if "Q9" in chunk.page_content and "payment method" in chunk.page_content.lower():
        print(f"\nFound in Chunk {i}:")
        print(chunk.page_content)
        break