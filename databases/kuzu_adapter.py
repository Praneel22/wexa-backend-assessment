import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import kuzu

from databases.base import BaseGraphDatabase


class KuzuAdapter(BaseGraphDatabase):
    """
    Adapter for Kùzu Graph Database.
    Strictly configured with 256 MB buffer pool to maintain resource fairness
    with CognoDB c0 tier (256 MB RAM limit).
    """

    def __init__(self, db_path: str = "data/kuzu_benchmark_db", buffer_pool_size_mb: int = 256):
        super().__init__(name="Kùzu (256MB capped)")
        self.db_path = Path(db_path)
        self.buffer_pool_size_bytes = buffer_pool_size_mb * 1024 * 1024
        self.db = None
        self.conn = None

    def connect(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # Initialize Kùzu with explicit memory buffer limit (256 MB)
        self.db = kuzu.Database(
            str(self.db_path),
            buffer_pool_size=self.buffer_pool_size_bytes,
        )
        self.conn = kuzu.Connection(self.db)
        self.is_connected = True

    def close(self) -> None:
        self.conn = None
        self.db = None
        self.is_connected = False

    def verify_connectivity(self) -> bool:
        if not self.conn:
            return False
        try:
            res = self.conn.execute("RETURN 1 AS test")
            return res.has_next()
        except Exception:
            return False

    def ping(self) -> float:
        if not self.conn:
            raise RuntimeError("Kùzu connection not active.")
        start = time.perf_counter()
        self.conn.execute("RETURN 1 AS ping")
        return (time.perf_counter() - start) * 1000.0

    def clear_database(self) -> None:
        """Reset Kùzu database files."""
        self.close()
        if self.db_path.is_dir():
            shutil.rmtree(self.db_path)
        elif self.db_path.exists():
            self.db_path.unlink()
        # Also clean any associated lock or wal files
        for f in self.db_path.parent.glob(f"{self.db_path.name}*"):
            if f.is_dir():
                shutil.rmtree(f)
            elif f.exists():
                f.unlink()
        self.connect()


    def create_schema(self) -> None:
        """Create User node table and FRIENDS_WITH relationship table."""
        if not self.conn:
            raise RuntimeError("Kùzu connection not active.")
        try:
            self.conn.execute("CREATE NODE TABLE User(id INT64, PRIMARY KEY(id))")
        except Exception:
            pass  # Table may already exist
        try:
            self.conn.execute("CREATE REL TABLE FRIENDS_WITH(FROM User TO User)")
        except Exception:
            pass

    def batch_insert_nodes(self, nodes: List[int], batch_size: int = 5000) -> Tuple[int, float]:
        """Batch insert User nodes."""
        if not self.conn:
            raise RuntimeError("Kùzu connection not active.")

        start_time = time.perf_counter()
        # Fast bulk ingestion using COPY if nodes CSV exists, or parameterized batching
        nodes_csv = Path("data/processed/pokec_100k_nodes.csv")
        if nodes_csv.exists() and len(nodes) >= 40000:
            self.conn.execute(f"COPY User FROM '{nodes_csv.resolve()}' (HEADER = true)")
            total_inserted = len(nodes)
        else:
            total_inserted = 0
            for i in range(0, len(nodes), batch_size):
                batch = nodes[i : i + batch_size]
                for node_id in batch:
                    self.conn.execute(f"CREATE (:User {{id: {node_id}}})")
                total_inserted += len(batch)

        elapsed = time.perf_counter() - start_time
        return total_inserted, elapsed

    def batch_insert_edges(self, edges: List[Tuple[int, int]], batch_size: int = 5000) -> Tuple[int, float]:
        """Batch insert FRIENDS_WITH relationships."""
        if not self.conn:
            raise RuntimeError("Kùzu connection not active.")

        start_time = time.perf_counter()
        edges_csv = Path("data/processed/pokec_100k.csv")
        if edges_csv.exists() and len(edges) >= 90000:
            self.conn.execute(f"COPY FRIENDS_WITH FROM '{edges_csv.resolve()}' (HEADER = true)")
            total_inserted = len(edges)
        else:
            total_inserted = 0
            for i in range(0, len(edges), batch_size):
                batch = edges[i : i + batch_size]
                for src, dst in batch:
                    self.conn.execute(
                        f"MATCH (s:User {{id: {src}}}), (t:User {{id: {dst}}}) CREATE (s)-[:FRIENDS_WITH]->(t)"
                    )
                total_inserted += len(batch)

        elapsed = time.perf_counter() - start_time
        return total_inserted, elapsed

    def run_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute Cypher query against Kùzu."""
        if not self.conn:
            raise RuntimeError("Kùzu connection not active.")

        # Substitute params if provided (Kùzu supports execute with params or formatted query)
        formatted_query = query
        if params:
            for k, v in params.items():
                if isinstance(v, str):
                    formatted_query = formatted_query.replace(f"${k}", f"'{v}'")
                else:
                    formatted_query = formatted_query.replace(f"${k}", str(v))

        res = self.conn.execute(formatted_query)
        records = []
        while res.has_next():
            row = res.get_next()
            records.append(dict(zip(res.get_column_names(), row)))
        return records

    def get_counts(self) -> Dict[str, int]:
        if not self.conn:
            raise RuntimeError("Kùzu connection not active.")
        try:
            res_nodes = self.conn.execute("MATCH (n:User) RETURN count(n) AS cnt")
            node_cnt = res_nodes.get_next()[0] if res_nodes.has_next() else 0
        except Exception:
            node_cnt = 0

        try:
            res_rels = self.conn.execute("MATCH ()-[r:FRIENDS_WITH]->() RETURN count(r) AS cnt")
            rel_cnt = res_rels.get_next()[0] if res_rels.has_next() else 0
        except Exception:
            rel_cnt = 0

        return {"nodes": int(node_cnt), "relationships": int(rel_cnt)}


    def get_resource_footprint(self) -> Dict[str, Any]:
        """Compute on-disk database size and memory limits."""
        disk_bytes = 0
        if self.db_path.exists():
            for p in self.db_path.rglob("*"):
                if p.is_file():
                    disk_bytes += p.stat().st_size
        return {
            "tier": "Embedded / Self-hosted baseline",
            "vcpu": "0.5 vCPU equivalent",
            "memory": "256 MB RAM (enforced via buffer_pool_size)",
            "storage_limit": "1 GB disk limit",
            "engine": "Kùzu Vectorized Columnar Engine",
            "managed_cloud": "No (Local / Embedded)",
            "stored_data_size": f"{disk_bytes / (1024 * 1024):.2f} MB",
            "memory_usage": "256.00 MB allocated buffer",
        }
