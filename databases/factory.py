from typing import Any, Dict, Optional
from databases.base import BaseGraphDatabase
from databases.cognodb import CognoDBAdapter
from databases.kuzu_adapter import KuzuAdapter
from databases.neo4j_adapter import Neo4jAdapter
from databases.memgraph_adapter import MemgraphAdapter
from databases.falkordb_adapter import FalkorDBAdapter

SUPPORTED_DATABASES = {
    "cognodb": CognoDBAdapter,
    "kuzu": KuzuAdapter,
    "neo4j": Neo4jAdapter,
    "memgraph": MemgraphAdapter,
    "falkordb": FalkorDBAdapter,
}


def get_database(name: str, **kwargs) -> BaseGraphDatabase:
    """
    Factory function to instantiate graph database adapter by name.
    
    Supported names:
    - 'cognodb': CognoDB Cloud (Bolt over TLS)
    - 'kuzu': Kùzu Columnar Graph Database (256MB capped)
    - 'neo4j': Neo4j (AuraDB / Community)
    - 'memgraph': Memgraph (In-Memory)
    - 'falkordb': FalkorDB (GraphBLAS Sparse Matrix)
    """
    key = name.lower().strip()
    if key not in SUPPORTED_DATABASES:
        supported = ", ".join(SUPPORTED_DATABASES.keys())
        raise ValueError(f"Unsupported database '{name}'. Choose from: {supported}")

    adapter_cls = SUPPORTED_DATABASES[key]
    return adapter_cls(**kwargs)
