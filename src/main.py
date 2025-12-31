"""Main entry point for the TelecomPlus agent with monitoring.

This module initializes all components and provides the main answer() function.
"""

from src.orchestrator import main_agent
from src.vector_db import build_vector_db
from src.load_data import load_dataframes
from src.load_pdfs import load_and_split_pdfs
from src.monitoring import get_monitor

# Initialize data once at startup
print("[INIT] Loading data...")
dfs_excel = load_dataframes()
print(f"[INIT] Loaded {len(dfs_excel)} Excel tables")

print("[INIT] Loading and splitting PDFs...")
chunks_pdf = load_and_split_pdfs()
print(f"[INIT] Loaded {len(chunks_pdf)} PDF chunks")

print("[INIT] Building vector database...")
db_pdf = build_vector_db(chunks_pdf)
print("[INIT] Vector database ready")

# Initialize monitor
monitor = get_monitor()
print("[INIT] Monitoring system ready")
print("[INIT] Initialization complete!\n")


def answer(question: str) -> str:
    """Answer a customer question using the intelligent agent system.
    
    This is the main entry point for the application. It:
    1. Starts monitoring for the query
    2. Routes the question to the appropriate agent
    3. Logs all activities
    4. Returns a natural language response
    
    Args:
        question: Customer's question in French
        
    Returns:
        Natural language response string
    """
    # Start monitoring
    query_id = monitor.start_query(question)
    
    try:
        # Call the main agent - it returns a string directly
        response = main_agent(question, db_pdf, dfs_excel)
        
        # main_agent ALWAYS returns a string now
        # Don't try to format lists or dicts - that was the old behavior
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
        Dictionary of metrics
    """
    return monitor.get_metrics()


def print_agent_summary():
    """Print monitoring summary to console."""
    monitor.print_summary()


def save_agent_metrics():
    """Save metrics to file."""
    monitor.save_metrics()


# For testing
if __name__ == "__main__":
    # Test questions
    test_questions = [
        "Quels modes de paiement acceptez-vous?",
        "Y a-t-il des frais de résiliation si je suis engagé?",
        "Combien de clients avez-vous?"
    ]
    
    print("Testing agent with sample questions...\n")
    
    for q in test_questions:
        print(f"Q: {q}")
        resp = answer(q)
        print(f"A: {resp}\n")
        print("-" * 80 + "\n")
    
    # Print summary
    print_agent_summary()
    save_agent_metrics()