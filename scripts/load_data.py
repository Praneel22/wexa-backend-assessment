import argparse
import csv
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from databases import get_database


DEFAULT_EDGES_CSV = Path("data/processed/pokec_100k.csv")
DEFAULT_NODES_CSV = Path("data/processed/pokec_100k_nodes.csv")


def load_edges_from_csv(csv_path: Path) -> List[Tuple[int, int]]:
    """Read edge tuples from processed CSV."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Edges CSV not found at {csv_path}. Run prepare_dataset.py first.")
    edges = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if len(row) >= 2:
                try:
                    edges.append((int(row[0]), int(row[1])))
                except ValueError:
                    continue
    return edges


def load_nodes_from_csv(csv_path: Path, edges: List[Tuple[int, int]]) -> List[int]:
    """Read unique nodes from nodes CSV or derive from edges."""
    if csv_path.exists():
        nodes = []
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if row:
                    try:
                        nodes.append(int(row[0]))
                    except ValueError:
                        continue
        if nodes:
            return sorted(nodes)

    # Fallback: extract unique node IDs from edges
    node_set = set()
    for src, dst in edges:
        node_set.add(src)
        node_set.add(dst)
    return sorted(node_set)


def run_data_loader(
    db_name: str = "cognodb",
    edges_csv: Path = DEFAULT_EDGES_CSV,
    nodes_csv: Path = DEFAULT_NODES_CSV,
    batch_size: int = 5000,
    clear_first: bool = True,
) -> Dict[str, float]:
    """
    Executes the full data loading pipeline:
    1. Connect & verify target database
    2. Optional clear existing graph
    3. Initialize schema / constraints
    4. Batch insert nodes
    5. Batch insert relationships
    6. Verify final node & edge counts
    """
    print(f"==================================================")
    print(f" Graph Database Ingestion: {db_name.upper()}")
    print(f"==================================================")
    print(f" Target Engine : {db_name}")
    print(f" Edges file    : {edges_csv}")
    print(f" Batch size    : {batch_size:,}")
    print(f" Clear first   : {clear_first}")
    print(f"--------------------------------------------------")

    # Load dataset into memory
    print("[1/5] Loading processed dataset from disk...")
    edges = load_edges_from_csv(edges_csv)
    nodes = load_nodes_from_csv(nodes_csv, edges)
    print(f"      Loaded {len(nodes):,} unique nodes and {len(edges):,} edges from CSV.")

    db = get_database(db_name)
    db.connect()

    try:
        # Clear if requested
        if clear_first:
            print("[2/5] Resetting database state (idempotent cleanup)...")
            db.clear_database()

        # Schema & Indexes
        print("[3/5] Applying schema, uniqueness constraints and indexes...")
        db.create_schema()

        # Insert Nodes
        print(f"[4/5] Ingesting {len(nodes):,} nodes in batches of {batch_size:,}...")
        n_inserted, node_time = db.batch_insert_nodes(nodes, batch_size=batch_size)
        node_rate = n_inserted / node_time if node_time > 0 else 0
        print(f"      Inserted {n_inserted:,} nodes in {node_time:.2f}s ({node_rate:,.1f} nodes/sec)")

        # Insert Relationships
        print(f"[5/5] Ingesting {len(edges):,} relationships in batches of {batch_size:,}...")
        e_inserted, edge_time = db.batch_insert_edges(edges, batch_size=batch_size)
        edge_rate = e_inserted / edge_time if edge_time > 0 else 0
        print(f"      Inserted {e_inserted:,} relationships in {edge_time:.2f}s ({edge_rate:,.1f} rels/sec)")

        # Verification
        counts = db.get_counts()
        total_time = node_time + edge_time
        print(f"--------------------------------------------------")
        print(f" Ingestion Summary for {db.name}:")
        print(f"   - Verified Nodes Ingested : {counts.get('nodes', 0):,}")
        print(f"   - Verified Rels Ingested  : {counts.get('relationships', 0):,}")
        print(f"   - Total Wall-Clock Time   : {total_time:.2f} s")
        print(f"   - Node Throughput         : {node_rate:,.1f} nodes/sec")
        print(f"   - Relationship Throughput : {edge_rate:,.1f} rels/sec")
        print(f"--------------------------------------------------")
        print(f"[SUCCESS] Ingestion completed successfully!")
        print(f"==================================================")

        return {
            "database": db.name,
            "nodes_count": counts.get("nodes", 0),
            "rels_count": counts.get("relationships", 0),
            "node_time_sec": node_time,
            "edge_time_sec": edge_time,
            "total_time_sec": total_time,
            "node_rate_per_sec": node_rate,
            "edge_rate_per_sec": edge_rate,
        }
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Ingest SNAP Pokec 100k dataset into graph database.")
    parser.add_argument("--db", type=str, default="cognodb", help="Database to load (cognodb, kuzu, neo4j, memgraph)")
    parser.add_argument("--edges", type=Path, default=DEFAULT_EDGES_CSV, help="Path to processed edges CSV")
    parser.add_argument("--nodes", type=Path, default=DEFAULT_NODES_CSV, help="Path to processed nodes CSV")
    parser.add_argument("--batch-size", type=int, default=5000, help="Batch size for insertion")
    parser.add_argument("--no-clear", action="store_true", help="Do not clear database before loading")
    args = parser.parse_args()

    try:
        run_data_loader(
            db_name=args.db,
            edges_csv=args.edges,
            nodes_csv=args.nodes,
            batch_size=args.batch_size,
            clear_first=not args.no_clear,
        )
    except Exception as e:
        print(f"[LOAD ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
