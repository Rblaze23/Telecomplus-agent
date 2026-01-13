"""Monitoring and logging system with LangSmith + Custom JSONL logs.

This module provides dual-layer monitoring:
1. LangSmith - Cloud-based tracing for LLM calls
2. JSONL logs - Custom local logs for full control

Comprehensive logging of:
- Agent decisions and routing
- Data source queries
- Response generation
- Performance metrics (latency, token usage)
- Errors and exceptions
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
# LangSmith integration (optional - only if API key present)
LANGSMITH_ENABLED = False
try:
    from langsmith import Client
    from langsmith.run_helpers import traceable
    
    # Check if LangSmith API key is configured
    if os.getenv("LANGCHAIN_API_KEY"):
        langsmith_client = Client()
        LANGSMITH_ENABLED = True
        print("[MONITOR] ✓ LangSmith enabled (dual-layer monitoring)")
    else:
        print("[MONITOR] LangSmith disabled (no API key - using JSONL only)")
except ImportError:
    print("[MONITOR] LangSmith not installed (using JSONL logs only)")
    traceable = lambda *args, **kwargs: lambda f: f  # No-op decorator


class AgentMonitor:
    """Monitor and log agent activities for debugging and performance analysis.
    
    Provides dual-layer monitoring:
    - Layer 1: LangSmith (cloud-based, visual dashboard)
    - Layer 2: JSONL logs (local, full control, offline analysis)
    """

    def __init__(self, log_dir: str = "logs"):
        """Initialize the monitoring system.

        Args:
            log_dir: Directory to store log files
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Create daily log file
        today = datetime.now().strftime("%Y%m%d")
        self.log_file = self.log_dir / f"agent_log_{today}.jsonl"
        self.metrics_file = self.log_dir / f"metrics_{today}.json"

        # In-memory metrics
        self.session_metrics = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "total_latency": 0.0,
            "source_usage": {
                "faq": 0,
                "data": 0,
                "both": 0
            },
            "errors": [],
            "langsmith_enabled": LANGSMITH_ENABLED
        }
        
        # Current query tracking
        self.current_query = None

    def start_query(self, question: str) -> str:
        """Start tracking a new query.

        Args:
            question: User's question

        Returns:
            Query ID for tracking
        """
        query_id = f"q_{int(time.time() * 1000)}"

        self.current_query = {
            "query_id": query_id,
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "start_time": time.time(),
            "events": []
        }

        self.session_metrics["total_queries"] += 1

        return query_id

    def log_event(self, event_type: str, data: Dict[str, Any]):
        """Log an event during query processing.

        Args:
            event_type: Type of event (e.g., "classification", "pdf_query", "data_query")
            data: Event data
        """
        event = {
            "type": event_type,
            "timestamp": time.time(),
            "data": data
        }

        if self.current_query is not None:
            self.current_query["events"].append(event)

        # Update source usage metrics
        if event_type == "classification":
            source = data.get("source", "unknown")
            if source in self.session_metrics["source_usage"]:
                self.session_metrics["source_usage"][source] += 1

    def end_query(self, response: str, success: bool = True, error: Optional[str] = None):
        """End tracking for current query.

        Args:
            response: Agent's response
            success: Whether query was successful
            error: Error message if failed
        """
        if self.current_query is None:
            return

        end_time = time.time()
        latency = end_time - self.current_query["start_time"]

        self.current_query["end_time"] = end_time
        self.current_query["latency_seconds"] = latency
        self.current_query["response"] = response
        self.current_query["success"] = success

        if error:
            self.current_query["error"] = error
            self.session_metrics["errors"].append({
                "query_id": self.current_query["query_id"],
                "error": error,
                "timestamp": datetime.now().isoformat()
            })
            self.session_metrics["failed_queries"] += 1
        else:
            self.session_metrics["successful_queries"] += 1

        # Update metrics
        self.session_metrics["total_latency"] += latency

        # Write to JSONL log file
        self._write_log_entry(self.current_query)
        
        # Send to LangSmith if enabled (happens automatically via @traceable decorator)
        if LANGSMITH_ENABLED:
            self._log_to_langsmith(self.current_query)

        # Reset current query
        self.current_query = None

    def _write_log_entry(self, entry: Dict[str, Any]):
        """Write a log entry to the JSONL file.

        Args:
            entry: Log entry dictionary
        """
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[MONITOR ERROR] Failed to write log: {e}")

    def _log_to_langsmith(self, query_data: Dict[str, Any]):
        """Send query metadata to LangSmith (optional).
        
        Note: Main tracing happens automatically via @traceable decorator.
        This method is for additional custom metadata if needed.
        
        Args:
            query_data: Complete query information
        """
        if not LANGSMITH_ENABLED:
            return
        
        try:
            # LangSmith automatically tracks via @traceable decorators
            # This is just for custom metadata if needed in future
            pass
        except Exception as e:
            print(f"[MONITOR] LangSmith logging failed (non-critical): {e}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get current session metrics.

        Returns:
            Dictionary of metrics
        """
        metrics = self.session_metrics.copy()

        if metrics["total_queries"] > 0:
            metrics["success_rate"] = (
                metrics["successful_queries"] / metrics["total_queries"] * 100
            )
            metrics["avg_latency"] = (
                metrics["total_latency"] / metrics["total_queries"]
            )
        else:
            metrics["success_rate"] = 0
            metrics["avg_latency"] = 0

        return metrics

    def save_metrics(self):
        """Save current metrics to file."""
        metrics = self.get_metrics()
        metrics["saved_at"] = datetime.now().isoformat()

        try:
            with open(self.metrics_file, 'w', encoding='utf-8') as f:
                json.dump(metrics, f, indent=2, ensure_ascii=False)
            print(f"[MONITOR] Metrics saved to {self.metrics_file}")
        except Exception as e:
            print(f"[MONITOR ERROR] Failed to save metrics: {e}")

    def print_summary(self):
        """Print a summary of session metrics to console."""
        metrics = self.get_metrics()

        print("\n" + "=" * 60)
        print("AGENT MONITORING SUMMARY")
        print("=" * 60)
        print(f"Monitoring Mode:    {'LangSmith + JSONL' if LANGSMITH_ENABLED else 'JSONL only'}")
        print(f"Total Queries:      {metrics['total_queries']}")
        print(f"Successful:         {metrics['successful_queries']}")
        print(f"Failed:             {metrics['failed_queries']}")
        print(f"Success Rate:       {metrics['success_rate']:.1f}%")
        print(f"Avg Latency:        {metrics['avg_latency']:.2f}s")
        print(f"\nSource Usage:")
        for source, count in metrics['source_usage'].items():
            print(f"  {source:10s}: {count}")

        if metrics['errors']:
            print(f"\nRecent Errors ({len(metrics['errors'])}):")
            for err in metrics['errors'][-5:]:  # Show last 5
                print(f"  - [{err['timestamp']}] {err['error'][:80]}")
        
        if LANGSMITH_ENABLED:
            print(f"\n✓ View traces at: https://smith.langchain.com/")
        
        print(f"✓ Local logs: {self.log_file}")
        print("=" * 60 + "\n")


# Global monitor instance
_monitor_instance = None


def get_monitor() -> AgentMonitor:
    """Get or create the global monitor instance.

    Returns:
        AgentMonitor instance
    """
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = AgentMonitor()
    return _monitor_instance


def log_agent_activity(event_type: str, data: Dict[str, Any]):
    """Convenience function to log agent activity.

    Args:
        event_type: Type of event
        data: Event data
    """
    monitor = get_monitor()
    monitor.log_event(event_type, data)


def analyze_logs(log_file: str) -> Dict[str, Any]:
    """Analyze a JSONL log file and generate statistics.

    Args:
        log_file: Path to JSONL log file

    Returns:
        Dictionary with analysis results
    """
    queries = []

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                queries.append(json.loads(line))
    except FileNotFoundError:
        print(f"Log file not found: {log_file}")
        return {}

    if not queries:
        return {}

    # Calculate statistics
    total = len(queries)
    successful = sum(1 for q in queries if q.get("success", False))
    latencies = [q.get("latency_seconds", 0) for q in queries]

    sources = {}
    for q in queries:
        for event in q.get("events", []):
            if event["type"] == "classification":
                source = event["data"].get("source", "unknown")
                sources[source] = sources.get(source, 0) + 1

    analysis = {
        "total_queries": total,
        "successful_queries": successful,
        "success_rate": successful / total * 100 if total > 0 else 0,
        "avg_latency": sum(latencies) / len(latencies) if latencies else 0,
        "min_latency": min(latencies) if latencies else 0,
        "max_latency": max(latencies) if latencies else 0,
        "source_distribution": sources
    }

    return analysis


# Export traceable decorator for use in other modules
# If LangSmith not available, this becomes a no-op decorator
__all__ = ['get_monitor', 'log_agent_activity', 'analyze_logs', 'AgentMonitor', 'traceable', 'LANGSMITH_ENABLED']


if __name__ == "__main__":
    # Example usage and testing
    print("\n" + "="*60)
    print("TESTING MONITORING SYSTEM")
    print("="*60)
    
    monitor = get_monitor()
    
    print(f"\nLangSmith status: {'✓ Enabled' if LANGSMITH_ENABLED else '✗ Disabled (no API key)'}")
    print(f"Logs directory: {monitor.log_dir}")
    print(f"Log file: {monitor.log_file}")

    # Simulate a query
    print("\nSimulating query...")
    query_id = monitor.start_query("Quels modes de paiement acceptez-vous?")

    monitor.log_event("classification", {
        "source": "faq",
        "reasoning": "Question about payment methods"
    })

    monitor.log_event("pdf_query", {
        "results_found": 3,
        "top_score": 0.85
    })

    time.sleep(0.1)  # Simulate processing time

    monitor.end_query(
        response="Nous acceptons carte bancaire, prélèvement automatique...",
        success=True
    )

    # Print summary
    monitor.print_summary()
    monitor.save_metrics()
    
    print("\n✓ Monitoring test complete!")