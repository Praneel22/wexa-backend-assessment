import statistics
from typing import Any, Dict, List


def calculate_latencies(latencies_ms: List[float]) -> Dict[str, float]:
    """Calculate statistical distribution for a list of latency measurements (ms)."""
    if not latencies_ms:
        return {
            "p50": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "mean": 0.0,
            "stddev": 0.0,
            "min": 0.0,
            "max": 0.0,
            "count": 0,
        }

    sorted_lats = sorted(latencies_ms)
    n = len(sorted_lats)

    def percentile(p: float) -> float:
        if n == 1:
            return sorted_lats[0]
        k = (n - 1) * (p / 100.0)
        f = int(k)
        c = min(f + 1, n - 1)
        d = k - f
        return sorted_lats[f] + d * (sorted_lats[c] - sorted_lats[f])

    return {
        "p50": round(percentile(50.0), 3),
        "p90": round(percentile(90.0), 3),
        "p95": round(percentile(95.0), 3),
        "p99": round(percentile(99.0), 3),
        "mean": round(statistics.mean(sorted_lats), 3),
        "stddev": round(statistics.stdev(sorted_lats) if n > 1 else 0.0, 3),
        "min": round(sorted_lats[0], 3),
        "max": round(sorted_lats[-1], 3),
        "count": n,
    }


def format_metric_table_row(name: str, metrics: Dict[str, float], unit: str = "ms") -> str:
    """Format a metric dict into a standard row string."""
    return f"{name:<30} | p50: {metrics['p50']:>7.2f} {unit} | p95: {metrics['p95']:>7.2f} {unit} | mean: {metrics['mean']:>7.2f} {unit}"
