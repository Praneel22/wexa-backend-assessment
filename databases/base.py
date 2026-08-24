from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class BaseGraphDatabase(ABC):
    """Abstract Base Class for graph database adapters in the benchmarking suite."""

    def __init__(self, name: str, host: Optional[str] = None, port: Optional[int] = None):
        self.name = name
        self.host = host
        self.port = port
        self.is_connected = False

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the database."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close database connection and clean up resources."""
        pass

    @abstractmethod
    def verify_connectivity(self) -> bool:
        """Verify that the database is reachable and accepting queries."""
        pass

    @abstractmethod
    def clear_database(self) -> None:
        """Idempotently remove all benchmark nodes and relationships."""
        pass

    @abstractmethod
    def create_schema(self) -> None:
        """Create constraints, indexes, and tables required for optimal performance."""
        pass

    @abstractmethod
    def batch_insert_nodes(self, nodes: List[int], batch_size: int = 5000) -> Tuple[int, float]:
        """
        Batch insert nodes into the database.
        Returns: (nodes_inserted, elapsed_seconds)
        """
        pass

    @abstractmethod
    def batch_insert_edges(self, edges: List[Tuple[int, int]], batch_size: int = 5000) -> Tuple[int, float]:
        """
        Batch insert edges into the database.
        Returns: (edges_inserted, elapsed_seconds)
        """
        pass

    @abstractmethod
    def run_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        """Execute a read or write Cypher/graph query and return records."""
        pass

    @abstractmethod
    def get_counts(self) -> Dict[str, int]:
        """Return current counts: {'nodes': int, 'relationships': int}."""
        pass

    @abstractmethod
    def get_resource_footprint(self) -> Dict[str, Any]:
        """
        Return observable resource footprint (disk, memory, instance specs).
        If platform does not expose internal metrics, return 'not observable'.
        """
        pass

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
