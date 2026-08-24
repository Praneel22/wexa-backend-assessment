import concurrent.futures
import random
import time
from typing import Any, Callable, Dict, List, Tuple

from benchmark.metrics import calculate_latencies
from databases.base import BaseGraphDatabase


class BenchmarkSuite:
    """Executes standard benchmark workloads across graph database engines."""

    def __init__(self, db: BaseGraphDatabase, seed: int = 42):
        self.db = db
        self.seed = seed
        random.seed(seed)

    def sample_nodes(self, count: int = 200) -> List[int]:
        """Fetch or sample existing node IDs from the database."""
        try:
            res = self.db.run_query("MATCH (u:User) RETURN u.id AS id LIMIT 1000")
            if res:
                all_ids = [r["id"] for r in res]
                sample_size = min(count, len(all_ids))
                return random.sample(all_ids, sample_size)
        except Exception:
            pass
        # Fallback to standard range
        return list(range(1, count + 1))

    def run_workload_iterations(
        self,
        name: str,
        query_fn: Callable[[int], Any],
        sample_pool: List[int],
        iterations: int = 100,
        warmup: int = 10,
    ) -> Dict[str, Any]:
        """Execute a query workload with warm-up runs followed by timed iterations."""
        # 1. Warm-up phase
        for _ in range(warmup):
            node_id = random.choice(sample_pool)
            try:
                query_fn(node_id)
            except Exception:
                pass

        # 2. Timed benchmark phase
        latencies = []
        start_wall = time.perf_counter()
        success_count = 0
        failure_count = 0

        for _ in range(iterations):
            node_id = random.choice(sample_pool)
            t0 = time.perf_counter()
            try:
                query_fn(node_id)
                t_elapsed = (time.perf_counter() - t0) * 1000.0  # ms
                latencies.append(t_elapsed)
                success_count += 1
            except Exception as e:
                failure_count += 1

        total_wall_sec = time.perf_counter() - start_wall
        qps = success_count / total_wall_sec if total_wall_sec > 0 else 0.0

        stats = calculate_latencies(latencies)
        stats["throughput_qps"] = round(qps, 2)
        stats["success_count"] = success_count
        stats["failure_count"] = failure_count
        stats["total_wall_sec"] = round(total_wall_sec, 3)

        return stats

    def benchmark_traversals(
        self,
        sample_nodes: List[int],
        iterations: int = 100,
        warmup: int = 10,
    ) -> Dict[str, Any]:
        """Measure 1-hop, 2-hop, and 3-hop traversal latency distributions."""
        print(f"  -> Running 1-Hop Neighbor Traversal ({iterations} iterations)...")
        hop1_stats = self.run_workload_iterations(
            name="1-Hop Traversal",
            query_fn=lambda nid: self.db.run_query(
                "MATCH (u:User {id: $id})-[:FRIENDS_WITH]->(v:User) RETURN v.id LIMIT 50",
                {"id": nid},
            ),
            sample_pool=sample_nodes,
            iterations=iterations,
            warmup=warmup,
        )

        print(f"  -> Running 2-Hop Neighbor Traversal ({iterations} iterations)...")
        hop2_stats = self.run_workload_iterations(
            name="2-Hop Traversal",
            query_fn=lambda nid: self.db.run_query(
                "MATCH (u:User {id: $id})-[:FRIENDS_WITH]->()-[:FRIENDS_WITH]->(v:User) RETURN count(v) AS cnt",
                {"id": nid},
            ),
            sample_pool=sample_nodes,
            iterations=iterations,
            warmup=warmup,
        )

        print(f"  -> Running 3-Hop Neighbor Traversal ({iterations} iterations)...")
        hop3_stats = self.run_workload_iterations(
            name="3-Hop Traversal",
            query_fn=lambda nid: self.db.run_query(
                "MATCH (u:User {id: $id})-[:FRIENDS_WITH]->()-[:FRIENDS_WITH]->()-[:FRIENDS_WITH]->(v:User) RETURN count(v) AS cnt",
                {"id": nid},
            ),
            sample_pool=sample_nodes,
            iterations=iterations,
            warmup=warmup,
        )

        return {
            "1_hop": hop1_stats,
            "2_hop": hop2_stats,
            "3_hop": hop3_stats,
        }

    def benchmark_lookups(
        self,
        sample_nodes: List[int],
        iterations: int = 100,
        warmup: int = 10,
    ) -> Dict[str, Any]:
        """Measure point lookups and filtered/range lookups on indexed properties."""
        print(f"  -> Running Point Lookup on User.id ({iterations} iterations)...")
        point_stats = self.run_workload_iterations(
            name="Point Lookup",
            query_fn=lambda nid: self.db.run_query(
                "MATCH (u:User {id: $id}) RETURN u.id",
                {"id": nid},
            ),
            sample_pool=sample_nodes,
            iterations=iterations,
            warmup=warmup,
        )

        print(f"  -> Running Filtered/Range Lookup ({iterations} iterations)...")
        range_stats = self.run_workload_iterations(
            name="Filtered Lookup",
            query_fn=lambda nid: self.db.run_query(
                "MATCH (u:User) WHERE u.id >= $min_id AND u.id <= $max_id RETURN count(u) AS cnt",
                {"min_id": nid, "max_id": nid + 50},
            ),
            sample_pool=sample_nodes,
            iterations=iterations,
            warmup=warmup,
        )

        return {
            "point_lookup": point_stats,
            "filtered_lookup": range_stats,
            "indexed_properties": ["User.id (Unique Index)"],
        }

    def benchmark_aggregations(
        self,
        sample_nodes: List[int],
        iterations: int = 50,
        warmup: int = 5,
    ) -> Dict[str, Any]:
        """Measure aggregation queries (degree distribution & count)."""
        print(f"  -> Running Aggregation Workload ({iterations} iterations)...")
        deg_stats = self.run_workload_iterations(
            name="Top Connected Nodes Aggregation",
            query_fn=lambda _: self.db.run_query(
                "MATCH (u:User)-[r:FRIENDS_WITH]->() RETURN u.id, count(r) AS degree ORDER BY degree DESC LIMIT 10"
            ),
            sample_pool=sample_nodes,
            iterations=iterations,
            warmup=warmup,
        )

        count_stats = self.run_workload_iterations(
            name="Global Relationship Count Aggregation",
            query_fn=lambda _: self.db.run_query(
                "MATCH ()-[r:FRIENDS_WITH]->() RETURN count(r) AS total"
            ),
            sample_pool=sample_nodes,
            iterations=iterations,
            warmup=warmup,
        )

        return {
            "degree_aggregation": deg_stats,
            "count_aggregation": count_stats,
        }

    def benchmark_mixed_workload(
        self,
        sample_nodes: List[int],
        concurrency_levels: List[int] = [1, 10, 40],
        total_ops_per_client: int = 50,
        read_ratio: float = 0.8,
    ) -> Dict[str, Any]:
        """
        Measure sustained throughput and latency under concurrent client load.
        Mix: 80% Read (lookups & 1-hop traversals) + 20% Write (temporary nodes/edges).
        """
        results_by_concurrency = {}

        for clients in concurrency_levels:
            print(f"  -> Running Mixed Workload (Concurrency = {clients} clients, 80/20 Read/Write)...")

            def client_worker(client_id: int) -> Tuple[List[float], int, int]:
                local_latencies = []
                success = 0
                failures = 0
                rng = random.Random(self.seed + client_id)

                for i in range(total_ops_per_client):
                    t0 = time.perf_counter()
                    try:
                        if rng.random() < read_ratio:
                            # 80% Read: Point lookup or 1-hop traversal
                            nid = rng.choice(sample_nodes)
                            if rng.random() < 0.5:
                                self.db.run_query("MATCH (u:User {id: $id}) RETURN u.id", {"id": nid})
                            else:
                                self.db.run_query(
                                    "MATCH (u:User {id: $id})-[:FRIENDS_WITH]->(v:User) RETURN v.id LIMIT 10",
                                    {"id": nid},
                                )
                        else:
                            # 20% Write: Create and delete a transient marker node
                            temp_id = 9_000_000 + client_id * 100_000 + i
                            self.db.run_query(
                                "CREATE (m:BenchmarkMarker {id: $id, client: $c})",
                                {"id": temp_id, "c": client_id},
                            )
                            self.db.run_query(
                                "MATCH (m:BenchmarkMarker {id: $id}) DELETE m",
                                {"id": temp_id},
                            )

                        elapsed_ms = (time.perf_counter() - t0) * 1000.0
                        local_latencies.append(elapsed_ms)
                        success += 1
                    except Exception:
                        failures += 1

                return local_latencies, success, failures

            wall_start = time.perf_counter()
            all_latencies = []
            total_success = 0
            total_failures = 0

            with concurrent.futures.ThreadPoolExecutor(max_workers=clients) as executor:
                futures = [executor.submit(client_worker, cid) for cid in range(clients)]
                for f in concurrent.futures.as_completed(futures):
                    lats, s, fl = f.result()
                    all_latencies.extend(lats)
                    total_success += s
                    total_failures += fl

            wall_time = time.perf_counter() - wall_start
            qps = total_success / wall_time if wall_time > 0 else 0.0

            stats = calculate_latencies(all_latencies)
            stats["concurrency"] = clients
            stats["read_write_mix"] = f"{int(read_ratio*100)}% Read / {int((1-read_ratio)*100)}% Write"
            stats["sustained_qps"] = round(qps, 2)
            stats["total_operations"] = total_success + total_failures
            stats["wall_time_sec"] = round(wall_time, 3)

            results_by_concurrency[f"concurrency_{clients}"] = stats

        return results_by_concurrency
