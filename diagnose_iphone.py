"""Diagnostic script to check iPhone price data in vector database.

Run this to see what chunks are being retrieved for iPhone queries.
"""

import sys
import os



from src.vector_db import query_pdf, load_vector_db

print("="*80)
print("DIAGNOSTIC: iPhone Price Query")
print("="*80)

# Load database
print("\nLoading vector database...")
db = load_vector_db()

# Test query
question = "Quel est le prix de l'iPhone 15 en 256GB?"
print(f"\nQuery: {question}")
print("\n" + "="*80)

# Get results
results = query_pdf(question, db, k=15)
print(f"\nRetrieved {len(results)} chunks")

# Analyze each chunk
for i, chunk in enumerate(results[:10], 1):
    print(f"\n{'='*80}")
    print(f"CHUNK {i}:")
    print('='*80)
    
    # Show full chunk (first 1500 chars)
    print(chunk[:1500])
    
    # Check for price indicators
    has_price = "1099" in chunk or "€" in chunk
    has_iphone15 = "iPhone 15" in chunk or "iphone 15" in chunk.lower()
    has_256 = "256" in chunk
    has_price_table = "prix" in chunk.lower() or "price" in chunk.lower()
    
    print(f"\n📊 Analysis:")
    print(f"  - Contains '1099': {'✅' if '1099' in chunk else '❌'}")
    print(f"  - Contains 'iPhone 15': {'✅' if has_iphone15 else '❌'}")
    print(f"  - Contains '256': {'✅' if has_256 else '❌'}")
    print(f"  - Contains 'prix/price': {'✅' if has_price_table else '❌'}")
    print(f"  - Contains '€': {'✅' if '€' in chunk else '❌'}")
    
    if has_price and has_iphone15 and has_256:
        print("\n🎯 THIS CHUNK HAS THE ANSWER!")

print("\n" + "="*80)
print("\nDIAGNOSTIC SUMMARY:")
print("="*80)

# Check if ANY chunk has the price
any_has_1099 = any("1099" in chunk for chunk in results)
any_has_price = any("€" in chunk for chunk in results)

if not any_has_1099 and not any_has_price:
    print("\n❌ PROBLEM: No chunks contain price data!")
    print("\nPossible causes:")
    print("1. PDF table was not extracted properly during load_pdfs.py")
    print("2. Vector database needs to be rebuilt")
    print("3. PDF has prices in images/non-text format")
    print("\n💡 SOLUTION: Rebuild vector database with better PDF extraction")
else:
    print("\n✅ Price data EXISTS in some chunks")
    print("❌ But vector search is NOT ranking them highly")
    print("\n💡 SOLUTION: Improve search query or ranking")

print("\n" + "="*80)