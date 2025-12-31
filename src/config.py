"""Configuration management for the TelecomPlus agent.

This module loads environment variables and provides configuration constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# API Keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError(
        "GOOGLE_API_KEY not found in environment variables. "
        "Please create a .env file with your API key."
    )

# Data paths
DATA_FOLDER = Path(__file__).parent.parent / "data"
XLSX_FOLDER = DATA_FOLDER / "xlsx"
PDF_FOLDER = DATA_FOLDER / "pdfs"
EVALUATION_FILE = DATA_FOLDER / "evaluation_questions.xlsx"

# Vector DB settings
VECTOR_DB_PATH = Path(__file__).parent.parent / "faiss_index"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# LLM settings
LLM_MODEL = "gemini-2.5-flash"
LLM_TEMPERATURE = 0.7
MAX_TOKENS = 1000

# RAG settings
PDF_CHUNK_SIZE = 800
PDF_CHUNK_OVERLAP = 80
PDF_RETRIEVAL_K = 3  # Number of chunks to retrieve

# Monitoring settings
LOG_FOLDER = Path(__file__).parent.parent / "logs"
LOG_FOLDER.mkdir(exist_ok=True)

# Evaluation settings
EVAL_SCORE_THRESHOLD = 6.0  # Out of 10
EVAL_PASS_PERCENTAGE = 60.0  # 60% to pass

print(f"[CONFIG] Configuration loaded successfully")
print(f"[CONFIG] API Key: {'✓ Set' if GOOGLE_API_KEY else '✗ Missing'}")
print(f"[CONFIG] Data folder: {DATA_FOLDER}")
print(f"[CONFIG] LLM Model: {LLM_MODEL}")
