"""Find available Gemini models."""

import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load API key
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

print("=" * 80)
print("AVAILABLE GEMINI MODELS")
print("=" * 80)

try:
    # List all available models
    models = genai.list_models()
    
    print("\nModels that support generateContent:")
    print("-" * 80)
    
    for model in models:
        if 'generateContent' in model.supported_generation_methods:
            print(f"\n✓ {model.name}")
            print(f"  Display name: {model.display_name}")
            print(f"  Description: {model.description[:100]}...")
            
    print("\n" + "=" * 80)
    print("RECOMMENDED MODELS TO TRY:")
    print("=" * 80)
    
    # Try these common names
    recommended = [
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-pro",
        "models/gemini-1.5-flash",
        "models/gemini-pro"
    ]
    
    for name in recommended:
        try:
            test_model = genai.GenerativeModel(name)
            response = test_model.generate_content("Hello")
            print(f"✓ WORKS: {name}")
        except Exception as e:
            print(f"✗ FAILED: {name} - {str(e)[:50]}")
    
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 80)