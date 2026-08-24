import pytest
from benchmark.metrics import calculate_latencies
from benchmark.workloads import BenchmarkSuite
from databases.kuzu_adapter import KuzuAdapter


def test_percentile_calculation():
    """Verify statistical percentile calculations."""
    latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    metrics = calculate_latencies(latencies)

    assert metrics["p50"] == pytest.approx(55.0, abs=1.0)
    assert metrics["p95"] == pytest.approx(95.5, abs=1.0)
    assert metrics["p99"] == pytest.approx(99.1, abs=1.0)
    assert metrics["mean"] == 55.0
    assert metrics["min"] == 10.0
    assert metrics["max"] == 100.0
    assert metrics["count"] == 10


def test_benchmark_suite_workloads(tmp_path):
    """Verify end-to-end workload execution on an in-memory/temp Kùzu database."""
    db_dir = tmp_path / "test_bench_kuzu"
    db = KuzuAdapter(db_path=str(db_dir), buffer_pool_size_mb=64)
    db.connect()

    try:
        db.create_schema()
        # Seed test graph
        db.batch_insert_nodes([1, 2, 3, 4, 5])
        db.batch_insert_edges([(1, 2), (2, 3), (3, 4), (4, 5)])

        suite = BenchmarkSuite(db=db, seed=42)
        sample = [1, 2]

        # 1. Traversals
        trav = suite.benchmark_traversals(sample_nodes=sample, iterations=5, warmup=1)
        assert "1_hop" in trav
        assert "2_hop" in trav
        assert "3_hop" in trav
        assert trav["1_hop"]["p50"] >= 0

        # 2. Lookups
        look = suite.benchmark_lookups(sample_nodes=sample, iterations=5, warmup=1)
        assert "point_lookup" in look
        assert "filtered_lookup" in look
        assert look["point_lookup"]["p50"] >= 0

        # 3. Aggregations
        agg = suite.benchmark_aggregations(sample_nodes=sample, iterations=2, warmup=1)
        assert "degree_aggregation" in agg
        assert "count_aggregation" in agg

        # 4. Mixed workload
        mixed = suite.benchmark_mixed_workload(
            sample_nodes=sample,
            concurrency_levels=[1, 2],
            total_ops_per_client=5,
            read_ratio=0.8,
        )
        assert "concurrency_1" in mixed
        assert "concurrency_2" in mixed
        assert mixed["concurrency_1"]["sustained_qps"] >= 0

    finally:
        db.close()
