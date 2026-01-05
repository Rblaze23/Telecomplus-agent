"""Comprehensive test suite for TelecomPlus agent.

This script tests all major functionality and verifies the system works correctly.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test 1: Verify all imports work."""
    print("\n" + "="*80)
    print("TEST 1: Imports")
    print("="*80)
    
    try:
        import pandas as pd
        import google.generativeai as genai
        from langchain_community.vectorstores import FAISS
        from langchain_huggingface import HuggingFaceEmbeddings
        print("✅ All core libraries imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("Run: pip install -r requirements.txt")
        return False


def test_data_files():
    """Test 2: Verify Excel data files exist and are readable."""
    print("\n" + "="*80)
    print("TEST 2: Data Files")
    print("="*80)
    
    import pandas as pd
    
    expected_files = [
        'clients.xlsx',
        'forfaits.xlsx',
        'abonnements.xlsx',
        'consommation.xlsx',
        'factures.xlsx',
        'tickets_support.xlsx'
    ]
    
    data_dir = Path('data/xlsx')
    
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        print("Run: python3 generate_sample_data.py")
        return False
    
    all_ok = True
    for filename in expected_files:
        filepath = data_dir / filename
        if filepath.exists():
            try:
                df = pd.read_excel(filepath)
                print(f"✅ {filename}: {len(df)} rows")
            except Exception as e:
                print(f"❌ {filename}: Error reading - {e}")
                all_ok = False
        else:
            print(f"❌ {filename}: Not found")
            all_ok = False
    
    return all_ok


def test_client_extraction():
    """Test 3: Client name extraction."""
    print("\n" + "="*80)
    print("TEST 3: Client Name Extraction")
    print("="*80)
    
    try:
        from src.orchestrator import extract_client_name
        
        test_cases = [
            ("Je m'appelle Jean Bertrand. Test.", "Jean Bertrand"),
            ("Je suis Marie Dubois.", "Marie Dubois"),
            ("Mon nom est Pierre Richard.", "Pierre Richard"),
            ("Bonjour, comment ça va?", None),
        ]
        
        all_passed = True
        for question, expected in test_cases:
            result = extract_client_name(question)
            status = "✅" if result == expected else "❌"
            print(f"{status} '{question[:40]}...' → {result} (expected: {expected})")
            if result != expected:
                all_passed = False
        
        return all_passed
        
    except ImportError as e:
        print(f"❌ Cannot import orchestrator: {e}")
        return False


def test_client_lookup():
    """Test 4: Client ID lookup."""
    print("\n" + "="*80)
    print("TEST 4: Client ID Lookup")
    print("="*80)
    
    try:
        from src.orchestrator import find_client_id
        from src.load_data import load_dataframes
        
        dfs = load_dataframes()
        
        if 'clients' not in dfs:
            print("❌ Clients table not loaded")
            return False
        
        test_cases = [
            ("Jean Bertrand", 1),
            ("Marie Dubois", 2),
            ("Pierre Richard", 3),
            ("Unknown Person", None),
        ]
        
        all_passed = True
        for name, expected_id in test_cases:
            result = find_client_id(name, dfs['clients'])
            status = "✅" if result == expected_id else "❌"
            print(f"{status} '{name}' → client_id={result} (expected: {expected_id})")
            if result != expected_id:
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vector_db():
    """Test 5: Vector database functionality."""
    print("\n" + "="*80)
    print("TEST 5: Vector Database")
    print("="*80)
    
    try:
        from src.load_pdfs import load_and_split_pdfs
        from src.vector_db import build_vector_db, query_pdf
        
        # Check if already built
        if Path('faiss_index').exists():
            print("✅ Vector DB already exists")
            from src.vector_db import load_vector_db
            db = load_vector_db()
        else:
            print("Building vector DB (first time only)...")
            chunks = load_and_split_pdfs()
            if not chunks:
                print("❌ No PDF chunks loaded")
                return False
            db = build_vector_db(chunks)
            print("✅ Vector DB built")
        
        # Test query
        test_query = "modes de paiement"
        results = query_pdf(test_query, db, k=3)
        
        if results and len(results) > 0:
            print(f"✅ Query returned {len(results)} results")
            print(f"   First result preview: {results[0][:100]}...")
            return True
        else:
            print("❌ Query returned no results")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_end_to_end():
    """Test 6: End-to-end question answering."""
    print("\n" + "="*80)
    print("TEST 6: End-to-End Question Answering")
    print("="*80)
    
    try:
        from src.main_improved import answer
        
        test_questions = [
            {
                'question': 'Quels modes de paiement acceptez-vous?',
                'type': 'FAQ',
                'keywords': ['carte', 'bancaire', 'prélèvement', 'paiement']
            },
            {
                'question': 'Je m\'appelle Jean Bertrand. Quelle est ma consommation data ce mois-ci?',
                'type': 'SQL - Personal',
                'keywords': ['3.20', 'GB', '5GB', 'consommé']
            },
            {
                'question': 'Je m\'appelle Jean Bertrand. Combien dois-je payer pour ma prochaine facture?',
                'type': 'SQL - Personal',
                'keywords': ['9.99', '€', 'facture', '15/12']
            }
        ]
        
        all_passed = True
        
        for test_case in test_questions:
            q = test_case['question']
            keywords = test_case['keywords']
            
            print(f"\n[{test_case['type']}]")
            print(f"Q: {q}")
            
            try:
                response = answer(q)
                print(f"A: {response}")
                
                # Check if response contains expected keywords
                response_lower = response.lower()
                found_keywords = [kw for kw in keywords if kw.lower() in response_lower]
                
                if len(found_keywords) >= 2:  # At least 2 keywords should match
                    print(f"✅ Response contains keywords: {found_keywords}")
                else:
                    print(f"⚠️  Response missing expected keywords. Found: {found_keywords}")
                    all_passed = False
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                all_passed = False
        
        return all_passed
        
    except ImportError as e:
        print(f"❌ Cannot import main_improved: {e}")
        print("Make sure src/main_improved.py exists")
        return False


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "="*80)
    print("TELECOMPLUS AGENT - COMPREHENSIVE TEST SUITE")
    print("="*80)
    
    tests = [
        ("Imports", test_imports),
        ("Data Files", test_data_files),
        ("Client Extraction", test_client_extraction),
        ("Client Lookup", test_client_lookup),
        ("Vector Database", test_vector_db),
        ("End-to-End", test_end_to_end),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results[test_name] = passed
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed_count = sum(1 for p in results.values() if p)
    total_count = len(results)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 ALL TESTS PASSED! System is ready.")
        print("\nNext steps:")
        print("1. Run: streamlit run app.py")
        print("2. Run: python3 evaluate.py")
        return True
    else:
        print("\n⚠️  Some tests failed. Please fix issues above.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)