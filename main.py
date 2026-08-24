"""
Main entry point for WEXA AI Graph Database Cloud Benchmarking Suite.

Usage:
    python main.py --help
    python main.py --test-connection
    python main.py --prepare-data
    python main.py --load --db cognodb
    python main.py --benchmark --db cognodb
    python main.py --report
    python main.py --all
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is in python path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.test_cognodb import test_connection
from scripts.prepare_dataset import prepare_dataset
from scripts.load_data import run_data_loader
from benchmark.runner import run_benchmark_for_db
from benchmark.generate_report import main as generate_report_main


def run_full_workflow():
    """Run the complete end-to-end benchmarking workflow."""
    print("\n=======================================================")
    print("  GRAPH DATABASE BENCHMARKING: FULL END-TO-END RUN")
    print("=======================================================\n")

    # Step 1: Verify CognoDB Connectivity
    print("[1/5] Testing CognoDB Cloud Connectivity...")
    connected = test_connection()
    if not connected:
        print("[WARNING] Could not connect to CognoDB Cloud. Check .env settings.")

    # Step 2: Prepare Dataset
    print("\n[2/5] Preparing SNAP Pokec Dataset...")
    prepare_dataset()

    # Step 3: Ingest Data into Kùzu (Local 256MB Baseline)
    print("\n[3/5] Ingesting Data into Kùzu (256MB Capped Baseline)...")
    run_data_loader(db_name="kuzu", batch_size=5000, clear_first=True)

    # Step 4: Run Benchmarks on Kùzu & CognoDB
    print("\n[4/5] Running Benchmark Workloads on Kùzu...")
    run_benchmark_for_db(db_name="kuzu", iterations=50, warmup=5, concurrency_levels=[1, 10, 40])

    if connected:
        print("\n[4b/5] Running Benchmark Workloads on CognoDB Cloud...")
        run_benchmark_for_db(db_name="cognodb", iterations=50, warmup=5, concurrency_levels=[1, 10, 40])

    # Step 5: Generate Report & Charts
    print("\n[5/5] Generating Markdown Report and Visualization Charts...")
    generate_report_main()

    print("\n=======================================================")
    print("  [SUCCESS] All benchmarks complete! Report generated.")
    print("  View: results/BENCHMARK_REPORT.md")
    print("=======================================================\n")


def main():
    parser = argparse.ArgumentParser(
        description="WEXA AI Graph Database Cloud Benchmarking Suite CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --all
  python main.py --test-connection
  python main.py --prepare-data
  python main.py --load --db cognodb
  python main.py --benchmark --db cognodb --iterations 100
  python main.py --report
        """,
    )
    parser.add_argument("--all", action="store_true", help="Run full end-to-end benchmark workflow")
    parser.add_argument("--test-connection", action="store_true", help="Test CognoDB Cloud connection")
    parser.add_argument("--prepare-data", action="store_true", help="Prepare SNAP Pokec 100k dataset")
    parser.add_argument("--load", action="store_true", help="Load dataset into database")
    parser.add_argument("--benchmark", action="store_true", help="Run benchmark suite")
    parser.add_argument("--db", type=str, default="cognodb", help="Database platform ('cognodb', 'kuzu', 'all')")
    parser.add_argument("--iterations", type=int, default=100, help="Number of benchmark iterations")
    parser.add_argument("--warmup", type=int, default=10, help="Number of warm-up iterations")
    parser.add_argument("--concurrency", type=str, default="1,10,40", help="Concurrency sweep levels (e.g. '1,10,40')")
    parser.add_argument("--report", action="store_true", help="Generate summary Markdown report and charts")

    args = parser.parse_args()

    # If no flags passed, run full workflow or print help
    if not any([args.all, args.test_connection, args.prepare_data, args.load, args.benchmark, args.report]):
        run_full_workflow()
        return

    if args.test_connection:
        test_connection()

    if args.prepare_data:
        prepare_dataset()

    if args.load:
        run_data_loader(db_name=args.db)

    if args.benchmark:
        concurrency_levels = [int(x.strip()) for x in args.concurrency.split(",") if x.strip()]
        run_benchmark_for_db(
            db_name=args.db,
            iterations=args.iterations,
            warmup=args.warmup,
            concurrency_levels=concurrency_levels,
        )

    if args.report:
        generate_report_main()


if __name__ == "__main__":
    main()
