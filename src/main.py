"""Main entry point for the TelecomPlus agent with LangSmith monitoring.

This module initializes all components and provides the main answer() function.
LangSmith tracing enabled via @traceable decorator when API key is configured.
"""

from src.orchestrator import main_agent
from src.vector_db import build_vector_db
from src.load_data import load_dataframes
from src.load_pdfs import load_and_split_pdfs
from src.monitoring import get_monitor, traceable, LANGSMITH_ENABLED

# Initialize data once at startup
print("[INIT] Loading data...")
dfs_excel = load_dataframes()
print(f"[INIT] Loaded {len(dfs_excel)} Excel tables")

print("[INIT] Loading and splitting PDFs...")
chunks_pdf = load_and_split_pdfs()
print(f"[INIT] Loaded {len(chunks_pdf)} PDF chunks")

print("[INIT] Building vector database...")
try:
    from pathlib import Path
    if not Path("faiss_index").exists():
        db_pdf = build_vector_db(chunks_pdf)
        print("[INIT] Vector database built successfully")
    else:
        from src.vector_db import load_vector_db
        db_pdf = load_vector_db()
        print("[INIT] Vector database loaded from disk")
except Exception as e:
    print(f"[ERROR] Vector database initialization failed: {e}")
    db_pdf = build_vector_db(chunks_pdf)

# Initialize monitor
monitor = get_monitor()
print("[INIT] Monitoring system ready")

if LANGSMITH_ENABLED:
    print("[INIT] ✓ LangSmith tracing enabled - view at https://smith.langchain.com/")
else:
    print("[INIT] LangSmith disabled - using JSONL logs only")

print("[INIT] Initialization complete!\n")


@traceable(
    name="telecomplus_agent",
    run_type="chain",
    metadata={
        "version": "1.0",
        "model": "gemini-2.5-flash",
        "architecture": "rag-orchestrator"
    }
)
def answer(question: str) -> str:
    """Answer a customer question using the intelligent agent system.
    
    This is the main entry point for the application. It:
    1. Starts monitoring for the query (JSONL + LangSmith)
    2. Routes the question to the appropriate agent
    3. Logs all activities
    4. Returns a natural language response
    
    LangSmith tracing:
    - Automatically tracks when LANGCHAIN_API_KEY is set in .env
    - Captures input/output, latency, nested LLM calls
    - View traces at https://smith.langchain.com/
    
    Args:
        question: Customer's question in French
        
    Returns:
        Natural language response string
    """
    # Start monitoring (JSONL logs)
    query_id = monitor.start_query(question)
    
    try:
        # Call the main agent
        # LangSmith will automatically trace nested LLM calls if they use @traceable
        response = main_agent(question, db_pdf, dfs_excel)
        
        # Ensure response is string
        if not isinstance(response, str):
            print(f"[WARNING] main_agent returned {type(response)}, converting to string")
            response = str(response)
        
        # End monitoring with success
        monitor.end_query(response, success=True)
        
        return response
        
    except Exception as e:
        error_msg = f"Erreur lors du traitement de votre question: {str(e)}"
        print(f"[ERROR] {error_msg}")
        
        import traceback
        traceback.print_exc()
        
        # Log error
        monitor.end_query(error_msg, success=False, error=str(e))
        
        return error_msg


def get_agent_stats():
    """Get current agent statistics.
    
    Returns:
        Dictionary of metrics including LangSmith status
    """
    return monitor.get_metrics()


def print_agent_summary():
    """Print monitoring summary to console.
    
    Includes both JSONL logs and LangSmith status.
    """
    monitor.print_summary()


def save_agent_metrics():
    """Save metrics to JSON file."""
    monitor.save_metrics()


# For testing
if __name__ == "__main__":
    # Test questions covering all types
    test_questions = [
        # FAQ questions
        "Quels modes de paiement acceptez-vous?",
        "Y a-t-il des frais de résiliation si je suis engagé?",
        
        # Personalized questions
        "Je m'appelle Jean Bertrand. Quelle est ma consommation data ce mois-ci?",
        "Je m'appelle Jean Bertrand. Combien dois-je payer pour ma prochaine facture?",
        
        # Hybrid question
        "Je m'appelle Jean Bertrand. Je pars en Italie 10 jours, dois-je changer de forfait?",
    ]
    
    print("=" * 80)
    print("TESTING TELECOMPLUS AGENT WITH MONITORING")
    print("=" * 80)
    print(f"LangSmith: {'✓ Enabled' if LANGSMITH_ENABLED else '✗ Disabled'}")
    print("=" * 80 + "\n")
    
    for i, q in enumerate(test_questions, 1):
        print(f"\n[TEST {i}/{len(test_questions)}]")
        print(f"Q: {q}")
        
        resp = answer(q)
        
        print(f"A: {resp}")
        print("-" * 80)
    
    # Print summary
    print("\n")
    print_agent_summary()
    save_agent_metrics()
    
    if LANGSMITH_ENABLED:
        print("\n✓ View detailed traces at: https://smith.langchain.com/")