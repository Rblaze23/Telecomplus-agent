"""Monitoring and logging system for agent performance tracking.

This module provides comprehensive logging of:
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


class AgentMonitor:
    """Monitor and log agent activities for debugging and performance analysis."""

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
            "errors": []
        }

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

        if hasattr(self, 'current_query'):
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
        if not hasattr(self, 'current_query'):
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

        # Write to log file (JSONL format)
        self._write_log_entry(self.current_query)

        # Reset current query
        delattr(self, 'current_query')

    def _write_log_entry(self, entry: Dict[str, Any]):
        """Write a log entry to the JSONL file.

        Args:
            entry: Log entry dictionary
        """
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"Error writing log: {e}")

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
            print(f"Error saving metrics: {e}")

    def print_summary(self):
        """Print a summary of session metrics to console."""
        metrics = self.get_metrics()

        print("\n" + "=" * 60)
        print("AGENT MONITORING SUMMARY")
        print("=" * 60)
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
    """Analyze a log file and generate statistics.

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


if __name__ == "__main__":
    # Example usage and testing
    monitor = get_monitor()

    # Simulate a query
    query_id = monitor.start_query("Quels modes de paiement acceptez-vous?")

    monitor.log_event("classification", {
        "source": "faq",
        "reasoning": "Question about payment methods"
    })

    monitor.log_event("pdf_query", {
        "results_found": 3,
        "top_score": 0.85
    })

    monitor.end_query(
        response="Nous acceptons carte bancaire, prélèvement automatique...",
        success=True
    )

    # Print summary
    monitor.print_summary()
    monitor.save_metrics()
