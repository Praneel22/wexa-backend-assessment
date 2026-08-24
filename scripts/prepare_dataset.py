import argparse
import csv
from pathlib import Path

DEFAULT_RAW_FILE = Path("data/raw/soc-pokec-relationships.txt")
DEFAULT_PROCESSED_DIR = Path("data/processed")
DEFAULT_MAX_EDGES = 100_000


def prepare_dataset(
    raw_file_path: Path = DEFAULT_RAW_FILE,
    output_dir: Path = DEFAULT_PROCESSED_DIR,
    max_edges: int = DEFAULT_MAX_EDGES,
):
    """
    Parses the raw SNAP Pokec relationship file and extracts a clean,
    deduplicated sample of edges and unique nodes.
    
    Generates:
    - pokec_100k.csv (and pokec_100k_edges.csv): columns [source_id, target_id]
    - pokec_100k_nodes.csv: columns [id]
    - pokec_100k.txt: tab-separated raw format
    """
    if not raw_file_path.exists():
        raise FileNotFoundError(f"Raw dataset file not found at: {raw_file_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    edges_csv_file = output_dir / "pokec_100k.csv"
    edges_alias_file = output_dir / "pokec_100k_edges.csv"
    nodes_csv_file = output_dir / "pokec_100k_nodes.csv"
    edges_txt_file = output_dir / "pokec_100k.txt"

    print(f"==================================================")
    print(f" Dataset Preparation: SNAP Pokec Social Network")
    print(f"==================================================")
    print(f" Source file   : {raw_file_path}")
    print(f" Target sample : {max_edges:,} edges")
    print(f" Output dir    : {output_dir}")
    print(f"--------------------------------------------------")

    seen_edges = set()
    nodes = set()
    edge_list = []
    malformed_lines = 0

    with raw_file_path.open("r", encoding="utf-8") as src:
        for line_num, line in enumerate(src, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            if len(parts) != 2:
                malformed_lines += 1
                continue

            try:
                src_id = int(parts[0])
                dst_id = int(parts[1])
            except ValueError:
                malformed_lines += 1
                continue

            edge = (src_id, dst_id)
            if edge in seen_edges:
                continue

            seen_edges.add(edge)
            nodes.add(src_id)
            nodes.add(dst_id)
            edge_list.append(edge)

            if len(edge_list) >= max_edges:
                break

    # 1. Write edges CSV
    with edges_csv_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["source_id", "target_id"])
        for src_id, dst_id in edge_list:
            writer.writerow([src_id, dst_id])

    # Also save as pokec_100k_edges.csv for explicit clarity
    with edges_alias_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["source_id", "target_id"])
        for src_id, dst_id in edge_list:
            writer.writerow([src_id, dst_id])

    # 2. Write edges TXT (tab-separated)
    with edges_txt_file.open("w", encoding="utf-8") as f:
        for src_id, dst_id in edge_list:
            f.write(f"{src_id}\t{dst_id}\n")

    # 3. Write sorted nodes CSV
    sorted_nodes = sorted(nodes)
    with nodes_csv_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id"])
        for node_id in sorted_nodes:
            writer.writerow([node_id])

    print(f" Extracted Edges     : {len(edge_list):,}")
    print(f" Unique Nodes       : {len(sorted_nodes):,}")
    print(f" Malformed Skipped  : {malformed_lines:,}")
    print(f" Generated Files    :")
    print(f"   - {edges_csv_file} ({edges_csv_file.stat().st_size / 1024:.1f} KB)")
    print(f"   - {nodes_csv_file} ({nodes_csv_file.stat().st_size / 1024:.1f} KB)")
    print(f"   - {edges_txt_file} ({edges_txt_file.stat().st_size / 1024:.1f} KB)")
    print(f"--------------------------------------------------")
    print(f"[SUCCESS] Dataset preparation complete.")
    print(f"==================================================")

    return {
        "edge_count": len(edge_list),
        "node_count": len(sorted_nodes),
        "edges_file": edges_csv_file,
        "nodes_file": nodes_csv_file,
    }


def main():
    parser = argparse.ArgumentParser(description="Prepare SNAP Pokec 100k benchmark dataset.")
    parser.add_argument("--raw-file", type=Path, default=DEFAULT_RAW_FILE, help="Path to raw relationships file")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_PROCESSED_DIR, help="Directory to save processed CSVs")
    parser.add_argument("--max-edges", type=int, default=DEFAULT_MAX_EDGES, help="Maximum number of unique edges")
    args = parser.parse_args()

    prepare_dataset(
        raw_file_path=args.raw_file,
        output_dir=args.output_dir,
        max_edges=args.max_edges,
    )


if __name__ == "__main__":
    main()