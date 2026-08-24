import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmark.workloads import BenchmarkSuite
from databases import get_database, SUPPORTED_DATABASES
from scripts.load_data import run_data_loader

DEFAULT_RESULTS_DIR = PROJECT_ROOT / "results"


def run_benchmark_for_db(
    db_name: str,
    iterations: int = 100,
    warmup: int = 10,
    concurrency_levels: List[int] = [1, 10, 40],
    load_data_first: bool = False,
    results_dir: Path = DEFAULT_RESULTS_DIR,
) -> Dict[str, Any]:
    """Execute the full benchmark suite for a given database platform."""
    results_dir.mkdir(parents=True, exist_ok=True)
    out_json = results_dir / f"{db_name}_benchmark.json"

    print(f"\n=======================================================")
    print(f" BENCHMARK RUNNER: {db_name.upper()}")
    print(f"=======================================================")
    print(f" Iterations / Read Workload : {iterations}")
    print(f" Warm-up Iterations         : {warmup}")
    print(f" Concurrency Sweeps         : {concurrency_levels}")
    print(f" Load Data First            : {load_data_first}")
    print(f" Output JSON                : {out_json}")
    print(f"-------------------------------------------------------")

    # Ingestion benchmark (if requested)
    loading_metrics = {}
    if load_data_first:
        print("[Step 1/6] Running Data Ingestion Workload...")
        loading_metrics = run_data_loader(
            db_name=db_name,
            batch_size=5000,
            clear_first=True,
        )
    else:
        print("[Step 1/6] Skipping fresh data load (using existing graph state)...")

    db = get_database(db_name)
    db.connect()

    try:
        suite = BenchmarkSuite(db=db)

        # Verify connectivity & sample nodes
        print("[Step 2/6] Sampling active nodes from graph...")
        counts = db.get_counts()
        print(f"           Graph contains {counts.get('nodes', 0):,} nodes, {counts.get('relationships', 0):,} edges.")
        sample_nodes = suite.sample_nodes(count=300)
        print(f"           Sampled {len(sample_nodes)} test start nodes.")

        # 1. Traversals (1-hop, 2-hop, 3-hop)
        print("[Step 3/6] Running Multi-Hop Traversal Workloads...")
        traversal_results = suite.benchmark_traversals(
            sample_nodes=sample_nodes,
            iterations=iterations,
            warmup=warmup,
        )

        # 2. Lookups (Point & Range/Filtered)
        print("[Step 4/6] Running Point & Filtered Lookup Workloads...")
        lookup_results = suite.benchmark_lookups(
            sample_nodes=sample_nodes,
            iterations=iterations,
            warmup=warmup,
        )

        # 3. Aggregations
        print("[Step 5/6] Running Aggregation Workloads...")
        agg_results = suite.benchmark_aggregations(
            sample_nodes=sample_nodes,
            iterations=max(20, iterations // 2),
            warmup=max(3, warmup // 2),
        )

        # 4. Mixed Workload & Concurrency Sweeps
        print("[Step 6/6] Running Mixed Concurrency Sweeps...")
        mixed_results = suite.benchmark_mixed_workload(
            sample_nodes=sample_nodes,
            concurrency_levels=concurrency_levels,
            total_ops_per_client=50,
            read_ratio=0.8,
        )

        footprint = db.get_resource_footprint()

        benchmark_data = {
            "metadata": {
                "database": db.name,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "dataset": "SNAP soc-Pokec Social Network Sample (100k edges)",
                "node_count": counts.get("nodes", 0),
                "edge_count": counts.get("relationships", 0),
                "iterations": iterations,
                "warmup": warmup,
            },
            "data_loading": loading_metrics,
            "traversals": traversal_results,
            "lookups": lookup_results,
            "aggregations": agg_results,
            "mixed_workload": mixed_results,
            "resource_footprint": footprint,
        }

        # Save JSON output
        with out_json.open("w", encoding="utf-8") as f:
            json.dump(benchmark_data, f, indent=2)

        print(f"-------------------------------------------------------")
        print(f"[SUCCESS] Benchmark complete for {db.name}. Saved to {out_json}")
        print(f"=======================================================\n")

        return benchmark_data

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Run Graph Database Cloud Benchmarks.")
    parser.add_argument(
        "--db",
        type=str,
        default="cognodb",
        help="Database to benchmark ('cognodb', 'kuzu', 'all', etc.)",
    )
    parser.add_argument("--iterations", type=int, default=100, help="Number of benchmark iterations per workload")
    parser.add_argument("--warmup", type=int, default=10, help="Number of warm-up iterations")
    parser.add_argument(
        "--concurrency",
        type=str,
        default="1,10,40",
        help="Comma-separated client concurrency levels (e.g. '1,10,40')",
    )
    parser.add_argument("--load-data", action="store_true", help="Load fresh data before running benchmarks")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_RESULTS_DIR, help="Results output directory")
    args = parser.parse_args()

    concurrency_levels = [int(x.strip()) for x in args.concurrency.split(",") if x.strip()]

    target_dbs = []
    if args.db.lower() == "all":
        target_dbs = ["cognodb", "kuzu"]
    else:
        target_dbs = [args.db.lower()]

    for target in target_dbs:
        try:
            run_benchmark_for_db(
                db_name=target,
                iterations=args.iterations,
                warmup=args.warmup,
                concurrency_levels=concurrency_levels,
                load_data_first=args.load_data,
                results_dir=args.output_dir,
            )
        except Exception as e:
            print(f"[BENCHMARK FAILED for {target}]: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
