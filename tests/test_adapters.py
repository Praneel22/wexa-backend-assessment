import os
import pytest
from databases.base import BaseGraphDatabase
from databases.factory import get_database, SUPPORTED_DATABASES
from databases.cognodb import CognoDBAdapter
from databases.kuzu_adapter import KuzuAdapter


def test_supported_databases_factory():
    """Verify factory instantiation for supported engines."""
    for name in SUPPORTED_DATABASES:
        db = get_database(name)
        assert isinstance(db, BaseGraphDatabase)
        assert db.name is not None

    with pytest.raises(ValueError, match="Unsupported database"):
        get_database("invalid_engine_name")


def test_cognodb_uri_normalization():
    """Verify that CognoDBAdapter correctly normalizes bolt:// to bolt+s:// for TLS."""
    adapter = CognoDBAdapter(uri="bolt://db-test.bravo.databases.cognodb.com", password="dummy")
    assert adapter.uri.startswith("bolt+s://")

    adapter_neo4j = CognoDBAdapter(uri="neo4j://db-test.bravo.databases.cognodb.com", password="dummy")
    assert adapter_neo4j.uri.startswith("neo4j+s://")


def test_kuzu_crud_lifecycle(tmp_path):
    """Verify Kùzu adapter lifecycle (connect, schema, batch insert, query, clear)."""
    db_dir = tmp_path / "test_kuzu"
    kuzu_db = KuzuAdapter(db_path=str(db_dir), buffer_pool_size_mb=64)
    kuzu_db.connect()

    try:
        assert kuzu_db.verify_connectivity() is True
        assert kuzu_db.ping() > 0

        # Create schema
        kuzu_db.create_schema()

        # Insert nodes
        n_ins, n_time = kuzu_db.batch_insert_nodes([1, 2, 3])
        assert n_ins == 3

        # Insert edges
        e_ins, e_time = kuzu_db.batch_insert_edges([(1, 2), (2, 3)])
        assert e_ins == 2

        # Query
        res = kuzu_db.run_query("MATCH (u:User {id: 1})-[:FRIENDS_WITH]->(v:User) RETURN v.id AS id")
        assert len(res) == 1
        assert res[0]["id"] == 2

        # Counts
        counts = kuzu_db.get_counts()
        assert counts["nodes"] == 3
        assert counts["relationships"] == 2

        # Clear
        kuzu_db.clear_database()
        counts_after = kuzu_db.get_counts()
        assert counts_after["nodes"] == 0
        assert counts_after["relationships"] == 0
    finally:
        kuzu_db.close()
