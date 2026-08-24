import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv
import certifi
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable, AuthError

from databases.base import BaseGraphDatabase

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
os.environ.setdefault("SSL_CERT_FILE", certifi.where())


class CognoDBAdapter(BaseGraphDatabase):
    """Adapter for CognoDB Cloud using Bolt protocol with TLS encryption."""

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        super().__init__(name="CognoDB Cloud")
        self.raw_uri = uri or os.getenv("COGNODB_URI")
        self.user = user or os.getenv("COGNODB_USERNAME") or os.getenv("COGNODB_USER") or "cognodb"
        self.password = password or os.getenv("COGNODB_PASSWORD")
        self.driver = None
        self._normalize_uri()

    def _normalize_uri(self) -> None:
        if not self.raw_uri:
            raise ValueError("COGNODB_URI must be provided or set in environment.")
        uri = self.raw_uri.strip()
        # Ensure TLS scheme for remote Cloud instances
        if uri.startswith("bolt://") and "databases.cognodb." in uri:
            uri = "bolt+s://" + uri[len("bolt://"):]
        elif uri.startswith("neo4j://") and "databases.cognodb." in uri:
            uri = "neo4j+s://" + uri[len("neo4j://"):]
        self.uri = uri

    def connect(self) -> None:
        if not self.uri or not self.password:
            raise ValueError("CognoDB URI and Password are required to connect.")

        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password),
            connection_timeout=15.0,
            max_connection_lifetime=300,
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
        """Measure round-trip ping time in milliseconds."""
        if not self.driver:
            raise RuntimeError("Driver not connected.")
        start = time.perf_counter()
        with self.driver.session() as session:
            session.run("RETURN 1 AS ping").consume()
        return (time.perf_counter() - start) * 1000.0

    def clear_database(self) -> None:
        """Remove all nodes and relationships."""
        if not self.driver:
            raise RuntimeError("Driver not connected.")
        with self.driver.session() as session:
            # Batch deletion for safety with memory limits
            session.run("MATCH ()-[r]->() DELETE r")
            session.run("MATCH (n) DELETE n")

    def create_schema(self) -> None:
        """Create uniqueness constraint and indexes for User nodes."""
        if not self.driver:
            raise RuntimeError("Driver not connected.")
        with self.driver.session() as session:
            try:
                session.run("CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE")
            except Exception:
                try:
                    session.run("CREATE CONSTRAINT ON (u:User) ASSERT u.id IS UNIQUE")
                except Exception:
                    session.run("CREATE INDEX user_id_idx IF NOT EXISTS FOR (u:User) ON (u.id)")

    def batch_insert_nodes(self, nodes: List[int], batch_size: int = 5000) -> Tuple[int, float]:
        """
        Batch insert User nodes using UNWIND Cypher query.
        Returns: (nodes_inserted, elapsed_seconds)
        """
        if not self.driver:
            raise RuntimeError("Driver not connected.")

        query = """
        UNWIND $batch AS node_id
        CREATE (:User {id: node_id})
        """
        total_inserted = 0
        start_time = time.perf_counter()

        with self.driver.session() as session:
            for i in range(0, len(nodes), batch_size):
                batch = nodes[i : i + batch_size]
                session.run(query, {"batch": batch}).consume()
                total_inserted += len(batch)

        elapsed = time.perf_counter() - start_time
        return total_inserted, elapsed

    def batch_insert_edges(self, edges: List[Tuple[int, int]], batch_size: int = 5000) -> Tuple[int, float]:
        """
        Batch insert FRIENDS_WITH relationships between existing User nodes.
        Returns: (edges_inserted, elapsed_seconds)
        """
        if not self.driver:
            raise RuntimeError("Driver not connected.")

        query = """
        UNWIND $batch AS row
        MATCH (s:User {id: row[0]}), (t:User {id: row[1]})
        CREATE (s)-[:FRIENDS_WITH]->(t)
        """
        total_inserted = 0
        start_time = time.perf_counter()

        with self.driver.session() as session:
            for i in range(0, len(edges), batch_size):
                batch = edges[i : i + batch_size]
                session.run(query, {"batch": batch}).consume()
                total_inserted += len(batch)

        elapsed = time.perf_counter() - start_time
        return total_inserted, elapsed

    def run_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute Cypher query and return list of record dictionaries."""
        if not self.driver:
            raise RuntimeError("Driver not connected.")
        with self.driver.session() as session:
            result = session.run(query, params or {})
            return [dict(record) for record in result]

    def get_counts(self) -> Dict[str, int]:
        """Return total nodes and relationships."""
        if not self.driver:
            raise RuntimeError("Driver not connected.")
        with self.driver.session() as session:
            nodes = session.run("MATCH (n:User) RETURN count(n) AS cnt").single()["cnt"]
            rels = session.run("MATCH ()-[r:FRIENDS_WITH]->() RETURN count(r) AS cnt").single()["cnt"]
            return {"nodes": int(nodes), "relationships": int(rels)}

    def get_resource_footprint(self) -> Dict[str, Any]:
        """Return specs and observable footprint."""
        return {
            "tier": "Free (c0)",
            "vcpu": "0.5 vCPU (burstable)",
            "memory": "256 MB RAM",
            "storage_limit": "1 GB disk",
            "engine": "CognoDB Native Graph Engine",
            "managed_cloud": "Yes (CognoDB Cloud)",
            "stored_data_size": "not observable (managed tier)",
            "memory_usage": "not observable (managed tier)",
        }
