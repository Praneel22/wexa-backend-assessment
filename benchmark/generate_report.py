import json
from pathlib import Path
from typing import Any, Dict, List
import matplotlib.pyplot as plt
from tabulate import tabulate

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"
REPORT_MD = RESULTS_DIR / "BENCHMARK_REPORT.md"


def load_all_results(results_dir: Path = RESULTS_DIR) -> Dict[str, Dict[str, Any]]:
    """Load all JSON benchmark result files from results/."""
    results = {}
    for json_file in results_dir.glob("*_benchmark.json"):
        try:
            with json_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                db_name = data.get("metadata", {}).get("database", json_file.stem)
                results[db_name] = data
        except Exception as e:
            print(f"Warning: Could not read {json_file}: {e}")
    return results


def generate_markdown_report(results: Dict[str, Dict[str, Any]]) -> str:
    """Generate Markdown report from benchmark results."""
    md = []
    md.append("# Graph Database Cloud Benchmarking Report")
    md.append("\n## Executive Summary\n")
    md.append(
        "This benchmark report compares **CognoDB Cloud** against competing graph database platforms "
        "on the **SNAP soc-Pokec social network dataset** (100,000 relationships, 49,683 nodes) "
        "under strictly controlled resource constraints (0.5 vCPU, 256 MB RAM parity)."
    )

    # 1. Ingest Throughput
    md.append("\n### 1. Data Ingestion Throughput\n")
    load_rows = []
    for db_name, data in results.items():
        load_data = data.get("data_loading", {})
        if load_data:
            node_rate = load_data.get('node_rate_per_sec', 0)
            edge_rate = load_data.get('edge_rate_per_sec', 0)
            tot_time = load_data.get('total_time_sec', 0)
            load_rows.append([
                db_name,
                f"{float(node_rate):,.1f}",
                f"{float(edge_rate):,.1f}",
                f"{float(tot_time):.2f} s",
            ])
        else:
            load_rows.append([db_name, "N/A", "N/A", "N/A"])


    md.append(tabulate(
        load_rows,
        headers=["Database Platform", "Nodes/sec", "Relationships/sec", "Total Load Time"],
        tablefmt="github",
    ))

    # 2. Traversals (1-hop, 2-hop, 3-hop)
    md.append("\n### 2. Multi-Hop Traversal Latency (ms)\n")
    trav_rows = []
    for db_name, data in results.items():
        trav = data.get("traversals", {})
        h1 = trav.get("1_hop", {})
        h2 = trav.get("2_hop", {})
        h3 = trav.get("3_hop", {})
        trav_rows.append([
            db_name,
            f"{h1.get('p50', 0):.2f} / {h1.get('p95', 0):.2f}",
            f"{h2.get('p50', 0):.2f} / {h2.get('p95', 0):.2f}",
            f"{h3.get('p50', 0):.2f} / {h3.get('p95', 0):.2f}",
        ])

    md.append(tabulate(
        trav_rows,
        headers=["Database Platform", "1-Hop (p50 / p95)", "2-Hop (p50 / p95)", "3-Hop (p50 / p95)"],
        tablefmt="github",
    ))

    # 3. Lookups
    md.append("\n### 3. Lookups & Filtered Queries (ms)\n")
    lookup_rows = []
    for db_name, data in results.items():
        lookups = data.get("lookups", {})
        pt = lookups.get("point_lookup", {})
        fl = lookups.get("filtered_lookup", {})
        indexed = ", ".join(lookups.get("indexed_properties", ["User.id"]))
        lookup_rows.append([
            db_name,
            f"{pt.get('p50', 0):.2f} / {pt.get('p95', 0):.2f}",
            f"{fl.get('p50', 0):.2f} / {fl.get('p95', 0):.2f}",
            indexed,
        ])

    md.append(tabulate(
        lookup_rows,
        headers=["Database Platform", "Point Lookup (p50/p95)", "Filtered Lookup (p50/p95)", "Indexed Properties"],
        tablefmt="github",
    ))

    # 4. Aggregations
    md.append("\n### 4. Graph Aggregations (ms)\n")
    agg_rows = []
    for db_name, data in results.items():
        aggs = data.get("aggregations", {})
        deg = aggs.get("degree_aggregation", {})
        cnt = aggs.get("count_aggregation", {})
        agg_rows.append([
            db_name,
            f"{deg.get('p50', 0):.2f} / {deg.get('p95', 0):.2f}",
            f"{cnt.get('p50', 0):.2f} / {cnt.get('p95', 0):.2f}",
        ])

    md.append(tabulate(
        agg_rows,
        headers=["Database Platform", "Top Degree Aggregation (p50/p95)", "Total Count Aggregation (p50/p95)"],
        tablefmt="github",
    ))

    # 5. Mixed Concurrency
    md.append("\n### 5. Mixed Workload Sustained Throughput (QPS, 80% Read / 20% Write)\n")
    mixed_rows = []
    for db_name, data in results.items():
        mx = data.get("mixed_workload", {})
        c1 = mx.get("concurrency_1", {})
        c10 = mx.get("concurrency_10", {})
        c40 = mx.get("concurrency_40", {})
        mixed_rows.append([
            db_name,
            f"{c1.get('sustained_qps', 0):,.1f} QPS (p50: {c1.get('p50', 0):.1f}ms)",
            f"{c10.get('sustained_qps', 0):,.1f} QPS (p50: {c10.get('p50', 0):.1f}ms)",
            f"{c40.get('sustained_qps', 0):,.1f} QPS (p50: {c40.get('p50', 0):.1f}ms)",
        ])

    md.append(tabulate(
        mixed_rows,
        headers=["Database Platform", "1 Client Concurrency", "10 Clients Concurrency", "40 Clients Concurrency"],
        tablefmt="github",
    ))

    # 6. Footprint
    md.append("\n### 6. Resource Footprint & Specifications\n")
    foot_rows = []
    for db_name, data in results.items():
        fp = data.get("resource_footprint", {})
        foot_rows.append([
            db_name,
            fp.get("vcpu", "0.5 vCPU"),
            fp.get("memory", "256 MB"),
            fp.get("stored_data_size", "not observable"),
            fp.get("managed_cloud", "Yes"),
        ])

    md.append(tabulate(
        foot_rows,
        headers=["Database Platform", "vCPU Allocation", "RAM Allocation", "Stored Data Size", "Cloud Managed"],
        tablefmt="github",
    ))

    return "\n".join(md)


def generate_charts(results: Dict[str, Dict[str, Any]], output_dir: Path = RESULTS_DIR):
    """Generate visual latency and throughput comparison bar charts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    if not results:
        return

    # 1. Traversal Latency Chart (p50)
    db_names = list(results.keys())
    hops1_p50 = [results[db].get("traversals", {}).get("1_hop", {}).get("p50", 0) for db in db_names]
    hops2_p50 = [results[db].get("traversals", {}).get("2_hop", {}).get("p50", 0) for db in db_names]
    hops3_p50 = [results[db].get("traversals", {}).get("3_hop", {}).get("p50", 0) for db in db_names]

    fig, ax = plt.subplots(figsize=(10, 5))
    x = range(len(db_names))
    width = 0.25

    ax.bar([i - width for i in x], hops1_p50, width=width, label="1-Hop Traversal (p50)", color="#3498db")
    ax.bar(x, hops2_p50, width=width, label="2-Hop Traversal (p50)", color="#2ecc71")
    ax.bar([i + width for i in x], hops3_p50, width=width, label="3-Hop Traversal (p50)", color="#e74c3c")

    ax.set_xlabel("Database Platform", fontweight="bold")
    ax.set_ylabel("Latency (ms) - Lower is Better", fontweight="bold")
    ax.set_title("Multi-Hop Graph Traversal Latency Comparison (p50)", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(db_names)
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.7)
    plt.tight_layout()
    plt.savefig(output_dir / "traversal_latency.png", dpi=200)
    plt.close()

    # 2. Mixed Workload Throughput Chart (QPS)
    qps_c1 = [results[db].get("mixed_workload", {}).get("concurrency_1", {}).get("sustained_qps", 0) for db in db_names]
    qps_c10 = [results[db].get("mixed_workload", {}).get("concurrency_10", {}).get("sustained_qps", 0) for db in db_names]
    qps_c40 = [results[db].get("mixed_workload", {}).get("concurrency_40", {}).get("sustained_qps", 0) for db in db_names]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar([i - width for i in x], qps_c1, width=width, label="1 Client", color="#9b59b6")
    ax.bar(x, qps_c10, width=width, label="10 Clients", color="#f39c12")
    ax.bar([i + width for i in x], qps_c40, width=width, label="40 Clients", color="#1abc9c")

    ax.set_xlabel("Database Platform", fontweight="bold")
    ax.set_ylabel("Throughput (QPS) - Higher is Better", fontweight="bold")
    ax.set_title("Mixed Workload Concurrent Throughput (80% Read / 20% Write)", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(db_names)
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.7)
    plt.tight_layout()
    plt.savefig(output_dir / "mixed_throughput.png", dpi=200)
    plt.close()


def main():
    results = load_all_results()
    if not results:
        print("No benchmark JSON files found in results/. Run benchmark.runner first.")
        return

    md_report = generate_markdown_report(results)
    with REPORT_MD.open("w", encoding="utf-8") as f:
        f.write(md_report)

    generate_charts(results)
    print(f"[SUCCESS] Report generated at {REPORT_MD}")
    print(f"Charts saved to {RESULTS_DIR / 'traversal_latency.png'} and {RESULTS_DIR / 'mixed_throughput.png'}")


if __name__ == "__main__":
    main()
