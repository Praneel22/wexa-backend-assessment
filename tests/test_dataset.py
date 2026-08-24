import csv
from pathlib import Path
import pytest

from scripts.prepare_dataset import prepare_dataset

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_FILE = DATA_DIR / "raw" / "soc-pokec-relationships.txt"
PROCESSED_DIR = DATA_DIR / "processed"
EDGES_CSV = PROCESSED_DIR / "pokec_100k.csv"
NODES_CSV = PROCESSED_DIR / "pokec_100k_nodes.csv"


def test_prepare_dataset_generation():
    """Verify that dataset preparation creates the expected edge and node files."""
    if not RAW_FILE.exists():
        pytest.skip(f"Raw data file not present at {RAW_FILE}")

    res = prepare_dataset(raw_file_path=RAW_FILE, output_dir=PROCESSED_DIR, max_edges=10_000)
    assert res["edge_count"] == 10_000
    assert res["node_count"] > 0
    assert EDGES_CSV.exists()
    assert NODES_CSV.exists()


def test_processed_edges_integrity():
    """Verify format, headers, and types in processed CSV."""
    if not EDGES_CSV.exists():
        pytest.skip("Processed CSV does not exist yet")

    with EDGES_CSV.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        assert header == ["source_id", "target_id"]

        row_count = 0
        for row in reader:
            assert len(row) == 2
            src = int(row[0])
            dst = int(row[1])
            assert src > 0
            assert dst > 0
            row_count += 1
            if row_count >= 1000:
                break
        assert row_count >= 1000
