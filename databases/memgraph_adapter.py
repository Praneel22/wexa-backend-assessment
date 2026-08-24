import os
import time
from typing import Any, Dict, List, Optional, Tuple
from neo4j import GraphDatabase

from databases.base import BaseGraphDatabase


class MemgraphAdapter(BaseGraphDatabase):
    """Adapter for Memgraph In-Memory Graph Database."""

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        super().__init__(name="Memgraph (In-Memory)")
        self.uri = uri or os.getenv("MEMGRAPH_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("MEMGRAPH_USERNAME", "")
        self.password = password or os.getenv("MEMGRAPH_PASSWORD", "")
        self.driver = None

    def connect(self) -> None:
        auth = (self.user, self.password) if self.user and self.password else None
        self.driver = GraphDatabase.driver(
            self.uri,
            auth=auth,
            connection_timeout=15.0,
        )
        self.verify_connectivity()
        self.is_connected = True

    def close(self) -> None:
        if self.driver:
            self.driver.close()
            self.driver = None
        self.is_connected = False

    def verify_connectivity(self) -> bool:
        if not self.driver:
            return False
        try:
            self.driver.verify_connectivity()
            return True
        except Exception:
            return False

    def ping(self) -> float:
        if not self.driver:
            raise RuntimeError("Driver not connected.")
        start = time.perf_counter()
        with self.driver.session() as session:
            session.run("RETURN 1 AS ping").consume()
        return (time.perf_counter() - start) * 1000.0

    def clear_database(self) -> None:
        if not self.driver:
            raise RuntimeError("Driver not connected.")
        with self.driver.session() as session:
            session.run("MATCH ()-[r]->() DELETE r")
            session.run("MATCH (n) DELETE n")

    def create_schema(self) -> None:
        if not self.driver:
            raise RuntimeError("Driver not connected.")
        with self.driver.session() as session:
            session.run("CREATE INDEX ON :User(id)")

    def batch_insert_nodes(self, nodes: List[int], batch_size: int = 5000) -> Tuple[int, float]:
        if not self.driver:
            raise RuntimeError("Driver not connected.")
        query = "UNWIND $batch AS node_id CREATE (:User {id: node_id})"
        start_time = time.perf_counter()
        with self.driver.session() as session:
            for i in range(0, len(nodes), batch_size):
                batch = nodes[i : i + batch_size]
                session.run(query, {"batch": batch}).consume()
        return len(nodes), time.perf_counter() - start_time

    def batch_insert_edges(self, edges: List[Tuple[int, int]], batch_size: int = 5000) -> Tuple[int, float]:
        if not self.driver:
            raise RuntimeError("Driver not connected.")
        query = """
        UNWIND $batch AS row
        MATCH (s:User {id: row[0]}), (t:User {id: row[1]})
        CREATE (s)-[:FRIENDS_WITH]->(t)
        """
        start_time = time.perf_counter()
        with self.driver.session() as session:
            for i in range(0, len(edges), batch_size):
                batch = edges[i : i + batch_size]
                session.run(query, {"batch": batch}).consume()
        return len(edges), time.perf_counter() - start_time

    def run_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not self.driver:
            raise RuntimeError("Driver not connected.")
        with self.driver.session() as session:
            result = session.run(query, params or {})
            return [dict(record) for record in result]

    def get_counts(self) -> Dict[str, int]:
        if not self.driver:
            raise RuntimeError("Driver not connected.")
        with self.driver.session() as session:
            nodes = session.run("MATCH (n:User) RETURN count(n) AS cnt").single()["cnt"]
            rels = session.run("MATCH ()-[r:FRIENDS_WITH]->() RETURN count(r) AS cnt").single()["cnt"]
            return {"nodes": int(nodes), "relationships": int(rels)}

    def get_resource_footprint(self) -> Dict[str, Any]:
        return {
            "tier": "Memgraph Community / Cloud Free",
            "vcpu": "0.5 vCPU",
            "memory": "256 MB RAM",
            "storage_limit": "In-Memory",
            "engine": "Memgraph In-Memory C++ Engine",
            "managed_cloud": "Optional",
            "stored_data_size": "In-Memory",
            "memory_usage": "not observable",
        }
